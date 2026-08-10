"""The repulsive-curves optimizer — Python/numpy/scipy port of the Sobolev
gradient-flow step in racetrack-js/src/energyCurve.js (+ index.js Driver).

Uses direct O(n^2) tangent-point energy/gradient (numba, tpe_kernels.py) instead
of the JS Barnes-Hut approximation, the Sobolev-Slobodeckij Gram matrix as a
preconditioner, and barycenter + length constraints via a saddle-point solve.
Obstacles (bounding circle + boundary boxes) are summed directly. The energy is
made self-consistent with its gradient (l_i l_j weighting throughout).
"""

import math
import numpy as np
from scipy.linalg import lu_factor, lu_solve

from .blob import generate_blob_seed
from .kernels import (edge_geometry, vertex_geometry, tpe_energy, tpe_gradient,
                      gram_matrix, obstacle_energy as _obs_energy,
                      obstacle_gradient as _obs_gradient)
from .shapes import sample_roundrect, sample_circle_ring, closed_polyline_masses

ALPHA = 3.0
BETA = 6.0
LS_STEP_THRESHOLD = 1e-15
BACKPROJ_THRESHOLD = 1e-4
SIGMA = 0.01


def _build_obstacles(radius, boxes, obstacle_weight=2.0):
    """Concatenate all obstacle point masses. Returns (C (M,2), we (M,), p_exp).
    `we` folds the per-obstacle weight into the point mass; energy and force both
    use it (mass-weighted, so gradient == d(energy)/dP, unlike the JS quirk)."""
    p_exp = BETA - ALPHA  # 3
    Cs = []
    We = []
    # Bounding circle: radius*4, trunc(outer)*3 points, weight 1.
    outer = radius * 4.0
    npts = int(outer) * 3
    ring = sample_circle_ring(0.0, 0.0, outer, npts)
    m = closed_polyline_masses(ring)
    Cs.append(np.asarray(ring)); We.append(1.0 * m)
    # Boxes: weight = obstacle_weight (2.0).
    for b in boxes:
        pts = sample_roundrect(b['x'], b['y'], b['w'], b['h'], b['r'], step=1.5)
        m = closed_polyline_masses(pts)
        Cs.append(np.asarray(pts)); We.append(obstacle_weight * m)
    C = np.vstack(Cs)
    we = np.concatenate(We)
    return C, we, p_exp


class EnergyCurve:
    def __init__(self, seed, radius=10.0, num_points=100, boxes=None,
                 target_length_scale=6.0, obstacle_weight=2.0):
        self.P = generate_blob_seed(seed, radius, num_points).astype(float)
        self.n = self.P.shape[0]
        self.boxes = boxes or []

        self.C, self.we, self.p_exp = _build_obstacles(radius, self.boxes, obstacle_weight)
        self.obstacles_enabled = True

        Te, Le = edge_geometry(self.P)
        self.initial_avg_length = Le.mean()
        self.target_length = target_length_scale * Le.sum()

        # Constraints: barycenter (2) + length (n edges). Targets track the growing
        # length; barycenter target is the fixed initial centroid.
        self.bary_target = self._barycenter().copy()
        self.length_target = Le.copy()
        self.length_scale_step = self.initial_avg_length * 0.01
        self.scaling_length = True

        self.last_step_size = 0.0
        self.num_stuck = 0
        self.subdivide_count = 0
        self.subdivide_limit = 2
        self.steps = 0
        self.done = False

    # ---- geometry ----
    def _geom(self):
        Te, Le = edge_geometry(self.P)
        Ti, li = vertex_geometry(Te, Le)
        return Te, Le, Ti, li

    def total_length(self):
        _, Le = edge_geometry(self.P)
        return Le.sum()

    def _barycenter(self):
        Te, Le = edge_geometry(self.P)
        _, li = vertex_geometry(Te, Le)
        m = li.sum()
        return (self.P * li[:, None]).sum(axis=0) / m

    # ---- obstacles (direct sum, numba) ----
    def obstacle_energy(self, P):
        if not self.obstacles_enabled:
            return 0.0
        return float(_obs_energy(np.ascontiguousarray(P), self.C, self.we, self.p_exp))

    def obstacle_gradient(self, P):
        if not self.obstacles_enabled:
            return np.zeros_like(P)
        return _obs_gradient(np.ascontiguousarray(P), self.C, self.we, self.p_exp)

    # ---- total energy / gradient ----
    def current_energy(self, P):
        Te, Le = edge_geometry(P)
        Ti, li = vertex_geometry(Te, Le)
        E = tpe_energy(P, Ti, li, ALPHA, BETA)
        E += self.obstacle_energy(P)
        return E

    def _gradient(self):
        Te, Le, Ti, li = self._geom()
        G = tpe_gradient(self.P, Te, Ti, li, ALPHA, BETA)
        G += self.obstacle_gradient(self.P)
        return G, Te, Le, Ti, li

    # ---- saddle system ----
    def _build_saddle(self, Te, Le, li):
        n = self.n
        m = 2 + n
        N = 2 * n + m
        M = np.zeros((N, N))
        A = gram_matrix(self.P, Te, Le, ALPHA, BETA)
        M[0:2 * n:2, 0:2 * n:2] = A
        M[1:2 * n:2, 1:2 * n:2] = A

        total_len = Le.sum()
        base = 2 * n
        # Barycenter rows (0,1)
        w = li / total_len
        for i in range(n):
            M[base + 0, 2 * i] = w[i];     M[2 * i, base + 0] = w[i]
            M[base + 1, 2 * i + 1] = w[i]; M[2 * i + 1, base + 1] = w[i]
        # Length rows (2 .. 2+n-1)
        nxt = np.roll(np.arange(n), -1)
        d = self.P - self.P[nxt]                      # prev - next
        L = np.hypot(d[:, 0], d[:, 1])
        g = d / L[:, None]
        for e in range(n):
            row = base + 2 + e
            j2 = nxt[e]
            M[row, 2 * e] = g[e, 0];       M[2 * e, row] = g[e, 0]
            M[row, 2 * e + 1] = g[e, 1];   M[2 * e + 1, row] = g[e, 1]
            M[row, 2 * j2] = -g[e, 0];     M[2 * j2, row] = -g[e, 0]
            M[row, 2 * j2 + 1] = -g[e, 1]; M[2 * j2 + 1, row] = -g[e, 1]
        return M

    def _project(self, luf, grad):
        n = self.n
        N = luf[0].shape[0]
        b = np.zeros(N)
        b[0:2 * n:2] = grad[:, 0]
        b[1:2 * n:2] = grad[:, 1]
        x = lu_solve(luf, b)
        proj = np.empty_like(grad)
        proj[:, 0] = x[0:2 * n:2]
        proj[:, 1] = x[1:2 * n:2]
        return proj

    def _constraint_violations(self):
        # b[2n:] = targets - current  (negative violations)
        Te, Le = edge_geometry(self.P)
        bary = self._barycenter()
        vb = self.bary_target - bary
        vl = self.length_target - Le
        return np.concatenate([vb, vl])

    def _backproject_constraints(self, luf):
        n = self.n
        N = luf[0].shape[0]
        viol = self._constraint_violations()
        b = np.zeros(N)
        b[2 * n:] = viol
        x = lu_solve(luf, b)
        self.P[:, 0] += x[0:2 * n:2]
        self.P[:, 1] += x[1:2 * n:2]
        return float(np.max(np.abs(self._constraint_violations())))

    # ---- line search ----
    def _line_search(self, grad, grad_dot, P0):
        grad_norm = float(np.sqrt((grad ** 2).sum()))
        if grad_norm > 1:
            init_guess = 1.0 / grad_norm
        else:
            init_guess = 1.0 / math.sqrt(grad_norm) if grad_norm > 0 else 0.0
        if self.last_step_size > max(LS_STEP_THRESHOLD, 1e-5):
            init_guess = min(self.last_step_size * 1.5, init_guess * 4)
        delta = init_guess
        initial_energy = self.current_energy(P0)
        if grad_norm < 1e-10:
            return 0.0
        while delta > LS_STEP_THRESHOLD:
            self.P = P0 - grad * delta
            new_energy = self.current_energy(self.P)
            decrease = initial_energy - new_energy
            target = SIGMA * delta * grad_norm * grad_dot
            if decrease < target:
                delta /= 2
            else:
                self.P = P0 - grad * delta
                break
        if delta <= LS_STEP_THRESHOLD:
            self.P = P0.copy()
            return 0.0
        return delta

    def _backproject(self, grad, init_guess, luf, P0):
        delta = init_guess
        attempts = 0
        while attempts < 10:  # usingLength keeps the loop alive until attempts hit 10
            attempts += 1
            self.P = P0 - grad * delta
            for _ in range(3):
                maxv = self._backproject_constraints(luf)
                if maxv < BACKPROJ_THRESHOLD:
                    return delta
            delta *= 0.5
        self.P = P0.copy()
        self._backproject_constraints(luf)
        return delta

    # ---- length scaling ----
    def _move_length_towards_target(self):
        curr = self.total_length()
        diff = self.target_length - curr
        n = self.n
        step = self.length_scale_step if diff > 0 else -self.length_scale_step
        if abs(diff) < self.length_scale_step * n:
            step = diff / n
        self.length_target += step

    def _target_length_reached(self):
        return abs(self.total_length() - self.target_length) <= self.length_scale_step

    # ---- one Sobolev step ----
    def _sobolev_step(self):
        if self.scaling_length:
            self._move_length_towards_target()
        if self.scaling_length and self._target_length_reached():
            self.scaling_length = False
            self.obstacles_enabled = False  # deacObsAfterScaling

        grad, Te, Le, Ti, li = self._gradient()
        M = self._build_saddle(Te, Le, li)
        luf = lu_factor(M)

        l2 = grad.copy()
        proj = self._project(luf, grad)
        sobo_dot = float((l2 * proj).sum())
        proj_norm = float(np.sqrt((proj ** 2).sum()))
        if not np.isfinite(sobo_dot) or proj_norm == 0:
            return False

        energy1 = self.current_energy(self.P)
        dot_acc = sobo_dot / (proj_norm * proj_norm)

        P0 = self.P.copy()
        step_size = self._line_search(proj, dot_acc, P0)

        if step_size < LS_STEP_THRESHOLD:
            proj = np.zeros_like(proj)  # usingConstraint(Length) is always true here
        step_size = self._backproject(proj, step_size, luf, P0)

        energy2 = self.current_energy(self.P)
        self.last_step_size = step_size
        return step_size > LS_STEP_THRESHOLD and abs(energy2 - energy1) > 0

    # ---- subdivide (matches EnergyCurve.subdivide) ----
    def _subdivide(self):
        n = self.n
        nxt = np.roll(self.P, -1, axis=0)
        mids = 0.5 * (self.P + nxt)
        new = np.empty((2 * n, 2))
        new[0::2] = self.P
        new[1::2] = mids
        self.P = new
        self.n = new.shape[0]
        # initConstraints: reset targets to current, resume scaling.
        Te, Le = edge_geometry(self.P)
        self.bary_target = self._barycenter().copy()
        self.length_target = Le.copy()
        self.length_scale_step = Le.mean() * 0.01
        self.scaling_length = True

    # ---- Driver.step ----
    def step(self):
        if self.done:
            return
        good = self._sobolev_step()
        self.steps += 1
        if not good:
            self.num_stuck += 1
            if self.num_stuck >= 3 and self._target_length_reached():
                self.done = True
                return
        else:
            self.num_stuck = 0
        avg = self.total_length() / self.n
        if avg > 2 * self.initial_avg_length and self.subdivide_count < self.subdivide_limit:
            self.subdivide_count += 1
            self._subdivide()

    # ---- helpers for the driver loop ----
    def _box_hits_any_vertex(self, b):
        # Vectorized roundrect interior test over all vertices.
        ax = np.abs(self.P[:, 0] - b['x'])
        ay = np.abs(self.P[:, 1] - b['y'])
        hw = b['w'] / 2.0; hh = b['h'] / 2.0
        r = min(b['r'], hw, hh)
        dx = np.maximum(ax - (hw - r), 0.0)
        dy = np.maximum(ay - (hh - r), 0.0)
        inside = (ax <= hw) & (ay <= hh) & (dx * dx + dy * dy <= r * r)
        return bool(inside.any())

    def watched_boxes(self):
        # Boxes the seed curve isn't already sitting on (matches main.js watchedShapes).
        return [b for b in self.boxes if not self._box_hits_any_vertex(b)]

    def intruded(self, watched):
        return any(self._box_hits_any_vertex(b) for b in watched)

    @property
    def polyline(self):
        return self.P.copy()

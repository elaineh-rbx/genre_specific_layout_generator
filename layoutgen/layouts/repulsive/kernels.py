"""Numba-compiled kernels for the tangent-point energy, its gradient, and the
Sobolev-Slobodeckij Gram matrix — direct O(n^2) ports of tpe.js / soboSlobo.js
for a closed curve (numEdges == numVerts == n; edge e joins vert e and e+1).

We use the mathematically-consistent energy E = sum_{i!=j} l_i l_j Kf(i,j) for
BOTH energy and gradient (the JS `tpePair` uses l_i^2 for the energy, which is a
port quirk that makes energy inconsistent with its own gradient). Using l_i l_j
throughout gives a proper descent method with the exact same gradient formula
the JS uses, and produces equivalent tracks.

Vertex tangent T_i = normalize(edgeTangent[i-1] + edgeTangent[i]); vertex dual
length l_i = (len[i-1] + len[i]) / 2.
"""

import math
import numpy as np
from numba import njit


# ---------------------------------------------------------------- derived geometry
@njit(cache=True)
def edge_geometry(P):
    n = P.shape[0]
    Te = np.empty((n, 2))
    Le = np.empty(n)
    for e in range(n):
        a = e
        b = (e + 1) % n
        dx = P[b, 0] - P[a, 0]
        dy = P[b, 1] - P[a, 1]
        L = math.sqrt(dx * dx + dy * dy)
        Le[e] = L
        Te[e, 0] = dx / L
        Te[e, 1] = dy / L
    return Te, Le


@njit(cache=True)
def vertex_geometry(Te, Le):
    n = Te.shape[0]
    Ti = np.empty((n, 2))
    li = np.empty(n)
    for i in range(n):
        p = (i - 1) % n
        sx = Te[p, 0] + Te[i, 0]
        sy = Te[p, 1] + Te[i, 1]
        s = math.sqrt(sx * sx + sy * sy)
        Ti[i, 0] = sx / s
        Ti[i, 1] = sy / s
        li[i] = 0.5 * (Le[p] + Le[i])
    return Ti, li


# ---------------------------------------------------------------- small helpers
@njit(cache=True)
def _edge_tan_jac(P, a, b, wrt):
    # d(unit tangent of edge a->b)/dP_wrt, returned as (cxx, cxy, cyx, cyy)
    # where col_x = (cxx, cxy), col_y = (cyx, cyy).
    if wrt != a and wrt != b:
        return 0.0, 0.0, 0.0, 0.0
    tx = P[b, 0] - P[a, 0]
    ty = P[b, 1] - P[a, 1]
    vn = math.sqrt(tx * tx + ty * ty)
    nx = tx / vn
    ny = ty / vn
    inv = 1.0 / (vn * vn)
    cxx = (vn - tx * nx) * inv
    cxy = (0.0 - ty * nx) * inv
    cyx = (0.0 - tx * ny) * inv
    cyy = (vn - ty * ny) * inv
    if wrt == a:
        return -cxx, -cxy, -cyx, -cyy
    return cxx, cxy, cyx, cyy


@njit(cache=True)
def _vtan_jac(P, Te, n, i, wrt):
    # dT_i/dP_wrt (2x2). Nonzero only for wrt in {i-1, i, i+1}.
    ip = (i - 1) % n
    inx = (i + 1) % n
    if wrt != ip and wrt != i and wrt != inx:
        return 0.0, 0.0, 0.0, 0.0
    sTx = Te[ip, 0] + Te[i, 0]
    sTy = Te[ip, 1] + Te[i, 1]
    normSum = math.sqrt(sTx * sTx + sTy * sTy)
    tix = sTx / normSum
    tiy = sTy / normSum
    # derivSumTs = d/dP_wrt (Te[prevEdge] + Te[nextEdge])
    p0, p1, p2, p3 = _edge_tan_jac(P, ip, i, wrt)   # prevEdge: verts ip -> i
    q0, q1, q2, q3 = _edge_tan_jac(P, i, inx, wrt)   # nextEdge: verts i  -> inx
    sxx = p0 + q0; sxy = p1 + q1; syx = p2 + q2; syy = p3 + q3
    # derivNorm = derivSumTs.leftMultiply(Ti)
    dNx = tix * sxx + tiy * sxy
    dNy = tix * syx + tiy * syy
    inv = 1.0 / (normSum * normSum)
    cxx = (sxx * normSum - sTx * dNx) * inv
    cxy = (sxy * normSum - sTy * dNx) * inv
    cyx = (syx * normSum - sTx * dNy) * inv
    cyy = (syy * normSum - sTy * dNy) * inv
    return cxx, cxy, cyx, cyy


@njit(cache=True)
def _grad_tan_proj(P, Te, Ti, n, i, j, wrt):
    # d(sT_i)/dP_wrt where s = disp . T_i, disp = P_i - P_j. (2x2)
    dispx = P[i, 0] - P[j, 0]
    dispy = P[i, 1] - P[j, 1]
    tix = Ti[i, 0]
    tiy = Ti[i, 1]
    dT = dispx * tix + dispy * tiy
    if wrt == i:
        iax = tix; iay = tiy
    elif wrt == j:
        iax = -tix; iay = -tiy
    else:
        iax = 0.0; iay = 0.0
    dtxx, dtxy, dtyx, dtyy = _vtan_jac(P, Te, n, i, wrt)
    ibx = dispx * dtxx + dispy * dtxy
    iby = dispx * dtyx + dispy * dtyy
    dix = iax + ibx
    diy = iay + iby
    cxx = tix * dix + dtxx * dT
    cxy = tiy * dix + dtxy * dT
    cyx = tix * diy + dtyx * dT
    cyy = tiy * diy + dtyy * dT
    return cxx, cxy, cyx, cyy


@njit(cache=True)
def _grad_normproj_alpha(P, Te, Ti, n, i, j, wrt, alpha):
    dispx = P[i, 0] - P[j, 0]
    dispy = P[i, 1] - P[j, 1]
    tix = Ti[i, 0]
    tiy = Ti[i, 1]
    dT = dispx * tix + dispy * tiy
    projx = dispx - dT * tix
    projy = dispy - dT * tiy
    proj_len = math.sqrt(projx * projx + projy * projy)
    if proj_len < 1e-10:
        return 0.0, 0.0
    alpha_deriv = alpha * math.pow(proj_len, alpha - 1.0)
    pnx = projx / proj_len
    pny = projy / proj_len
    if wrt == i:
        ddxx = 1.0; ddxy = 0.0; ddyx = 0.0; ddyy = 1.0
    elif wrt == j:
        ddxx = -1.0; ddxy = 0.0; ddyx = 0.0; ddyy = -1.0
    else:
        ddxx = 0.0; ddxy = 0.0; ddyx = 0.0; ddyy = 0.0
    gxx, gxy, gyx, gyy = _grad_tan_proj(P, Te, Ti, n, i, j, wrt)
    nxx = ddxx - gxx; nxy = ddxy - gxy; nyx = ddyx - gyx; nyy = ddyy - gyy
    resx = alpha_deriv * (pnx * nxx + pny * nxy)
    resy = alpha_deriv * (pnx * nyx + pny * nyy)
    return resx, resy


@njit(cache=True)
def _kf(P, Ti, i, j, alpha, beta):
    dispx = P[i, 0] - P[j, 0]
    dispy = P[i, 1] - P[j, 1]
    D = math.sqrt(dispx * dispx + dispy * dispy)
    dT = dispx * Ti[i, 0] + dispy * Ti[i, 1]
    projx = dispx - dT * Ti[i, 0]
    projy = dispy - dT * Ti[i, 1]
    N = math.sqrt(projx * projx + projy * projy)
    return math.pow(N, alpha) / math.pow(D, beta)


@njit(cache=True)
def _grad_kf(P, Te, Ti, n, i, j, wrt, alpha, beta):
    dispx = P[i, 0] - P[j, 0]
    dispy = P[i, 1] - P[j, 1]
    D = math.sqrt(dispx * dispx + dispy * dispy)
    dT = dispx * Ti[i, 0] + dispy * Ti[i, 1]
    projx = dispx - dT * Ti[i, 0]
    projy = dispy - dT * Ti[i, 1]
    N = math.sqrt(projx * projx + projy * projy)
    numer = math.pow(N, alpha)
    denom = math.pow(D, beta)
    dnx, dny = _grad_normproj_alpha(P, Te, Ti, n, i, j, wrt, alpha)
    bpow = beta * math.pow(D, beta - 1.0)
    if wrt == i:
        ddx = (dispx / D) * bpow
        ddy = (dispy / D) * bpow
    elif wrt == j:
        ddx = -(dispx / D) * bpow
        ddy = -(dispy / D) * bpow
    else:
        ddx = 0.0
        ddy = 0.0
    inv = 1.0 / (denom * denom)
    gx = (dnx * denom - ddx * numer) * inv
    gy = (dny * denom - ddy * numer) * inv
    return gx, gy


@njit(cache=True)
def _length_wrt(P, n, v, wrt):
    vp = (v - 1) % n
    vn = (v + 1) % n
    if wrt == v:
        ax = P[vp, 0] - P[v, 0]; ay = P[vp, 1] - P[v, 1]
        la = math.sqrt(ax * ax + ay * ay)
        bx = P[vn, 0] - P[v, 0]; by = P[vn, 1] - P[v, 1]
        lb = math.sqrt(bx * bx + by * by)
        return -0.5 * (ax / la + bx / lb), -0.5 * (ay / la + by / lb)
    elif wrt == vp:
        ax = P[vp, 0] - P[v, 0]; ay = P[vp, 1] - P[v, 1]
        la = math.sqrt(ax * ax + ay * ay)
        return 0.5 * ax / la, 0.5 * ay / la
    elif wrt == vn:
        bx = P[vn, 0] - P[v, 0]; by = P[vn, 1] - P[v, 1]
        lb = math.sqrt(bx * bx + by * by)
        return 0.5 * bx / lb, 0.5 * by / lb
    return 0.0, 0.0


@njit(cache=True)
def _tpe_grad_vv(P, Te, Ti, li, n, i, j, wrt, alpha, beta):
    gkx, gky = _grad_kf(P, Te, Ti, n, i, j, wrt, alpha, beta)
    Kf = _kf(P, Ti, i, j, alpha, beta)
    lxx, lxy = _length_wrt(P, n, i, wrt)   # grad l_i
    lyx, lyy = _length_wrt(P, n, j, wrt)   # grad l_j
    lx = li[i]
    ly = li[j]
    px = lxx * ly + lyx * lx
    py = lxy * ly + lyy * lx
    return gkx * (lx * ly) + px * Kf, gky * (lx * ly) + py * Kf


# ---------------------------------------------------------------- energy & gradient
@njit(cache=True)
def tpe_energy(P, Ti, li, alpha, beta):
    n = P.shape[0]
    E = 0.0
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            E += li[i] * li[j] * _kf(P, Ti, i, j, alpha, beta)
    return E


@njit(cache=True)
def tpe_gradient(P, Te, Ti, li, alpha, beta):
    n = P.shape[0]
    G = np.zeros((n, 2))
    cand = np.empty(6, dtype=np.int64)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            cand[0] = (i - 1) % n
            cand[1] = i
            cand[2] = (i + 1) % n
            cand[3] = (j - 1) % n
            cand[4] = j
            cand[5] = (j + 1) % n
            for c in range(6):
                wrt = cand[c]
                dup = False
                for d in range(c):
                    if cand[d] == wrt:
                        dup = True
                        break
                if dup:
                    continue
                gx, gy = _tpe_grad_vv(P, Te, Ti, li, n, i, j, wrt, alpha, beta)
                G[wrt, 0] += gx
                G[wrt, 1] += gy
    return G


# ---------------------------------------------------------------- obstacles (direct)
@njit(cache=True)
def obstacle_energy(P, C, we, p_exp):
    n = P.shape[0]
    M = C.shape[0]
    E = 0.0
    for i in range(n):
        px = P[i, 0]; py = P[i, 1]
        for k in range(M):
            dx = C[k, 0] - px; dy = C[k, 1] - py
            d = math.sqrt(dx * dx + dy * dy)
            E += we[k] / math.pow(d, p_exp)
    return E


@njit(cache=True)
def obstacle_gradient(P, C, we, p_exp):
    n = P.shape[0]
    M = C.shape[0]
    G = np.zeros((n, 2))
    pe2 = p_exp + 2.0
    for i in range(n):
        px = P[i, 0]; py = P[i, 1]
        gx = 0.0; gy = 0.0
        for k in range(M):
            dx = C[k, 0] - px; dy = C[k, 1] - py
            d = math.sqrt(dx * dx + dy * dy)
            coef = we[k] * p_exp / math.pow(d, pe2)
            gx += coef * dx; gy += coef * dy
        G[i, 0] = gx; G[i, 1] = gy
    return G


# ---------------------------------------------------------------- Sobolev Gram matrix
@njit(cache=True)
def gram_matrix(P, Te, Le, alpha, beta):
    # Returns the n x n top-left Sobolev-Slobodeckij block (SoboSlobo.sobolevGramMatrix).
    n = P.shape[0]
    A = np.zeros((n, n))
    s_pow = (beta - 1.0) / alpha
    hi_exp = 2.0 * (s_pow - 1.0) + 1.0     # high-order distance exponent
    low_b = 4.0 + hi_exp                    # low-order kernel exponent
    a_low = 2.0
    ends = np.empty(4, dtype=np.int64)
    for s in range(n):
        sp = s
        sn = (s + 1) % n
        for t in range(n):
            if t == s or t == (s - 1) % n or t == (s + 1) % n:
                continue
            tp = t
            tn = (t + 1) % n
            ends[0] = sp; ends[1] = sn; ends[2] = tp; ends[3] = tn
            len_s = Le[s]
            len_t = Le[t]
            msx = 0.5 * (P[sp, 0] + P[sn, 0]); msy = 0.5 * (P[sp, 1] + P[sn, 1])
            mtx = 0.5 * (P[tp, 0] + P[tn, 0]); mty = 0.5 * (P[tp, 1] + P[tn, 1])
            dx = msx - mtx; dy = msy - mty
            dist = math.sqrt(dx * dx + dy * dy)
            # high-order term
            dist_term = 1.0 / math.pow(dist, hi_exp)
            # low-order kernel (symmetric tangent-point)
            tsx = Te[s, 0]; tsy = Te[s, 1]
            ttx = Te[t, 0]; tty = Te[t, 1]
            dds = dx * tsx + dy * tsy
            ddt = dx * ttx + dy * tty
            npx_s = dx - dds * tsx; npy_s = dy - dds * tsy
            npx_t = dx - ddt * ttx; npy_t = dy - ddt * tty
            nxs = math.sqrt(npx_s * npx_s + npy_s * npy_s)
            nxt = math.sqrt(npx_t * npx_t + npy_t * npy_t)
            kf_low = 0.5 * (math.pow(nxs, a_low) + math.pow(nxt, a_low)) / math.pow(dist, low_b)

            for ui in range(4):
                u = ends[ui]
                # hatGradientOnEdge(s,u), (t,u)
                uhs_x = 0.0; uhs_y = 0.0
                if u == sp:
                    dxx = P[sp, 0] - P[sn, 0]; dyy = P[sp, 1] - P[sn, 1]
                    uhs_x = dxx / (len_s * len_s); uhs_y = dyy / (len_s * len_s)
                elif u == sn:
                    dxx = P[sn, 0] - P[sp, 0]; dyy = P[sn, 1] - P[sp, 1]
                    uhs_x = dxx / (len_s * len_s); uhs_y = dyy / (len_s * len_s)
                uht_x = 0.0; uht_y = 0.0
                if u == tp:
                    dxx = P[tp, 0] - P[tn, 0]; dyy = P[tp, 1] - P[tn, 1]
                    uht_x = dxx / (len_t * len_t); uht_y = dyy / (len_t * len_t)
                elif u == tn:
                    dxx = P[tn, 0] - P[tp, 0]; dyy = P[tn, 1] - P[tp, 1]
                    uht_x = dxx / (len_t * len_t); uht_y = dyy / (len_t * len_t)
                udx = uhs_x - uht_x; udy = uhs_y - uht_y
                u_low = (0.5 if (u == sp or u == sn) else 0.0) - (0.5 if (u == tp or u == tn) else 0.0)
                for vi in range(4):
                    v = ends[vi]
                    vhs_x = 0.0; vhs_y = 0.0
                    if v == sp:
                        dxx = P[sp, 0] - P[sn, 0]; dyy = P[sp, 1] - P[sn, 1]
                        vhs_x = dxx / (len_s * len_s); vhs_y = dyy / (len_s * len_s)
                    elif v == sn:
                        dxx = P[sn, 0] - P[sp, 0]; dyy = P[sn, 1] - P[sp, 1]
                        vhs_x = dxx / (len_s * len_s); vhs_y = dyy / (len_s * len_s)
                    vht_x = 0.0; vht_y = 0.0
                    if v == tp:
                        dxx = P[tp, 0] - P[tn, 0]; dyy = P[tp, 1] - P[tn, 1]
                        vht_x = dxx / (len_t * len_t); vht_y = dyy / (len_t * len_t)
                    elif v == tn:
                        dxx = P[tn, 0] - P[tp, 0]; dyy = P[tn, 1] - P[tp, 1]
                        vht_x = dxx / (len_t * len_t); vht_y = dyy / (len_t * len_t)
                    vdx = vhs_x - vht_x; vdy = vhs_y - vht_y
                    v_low = (0.5 if (v == sp or v == sn) else 0.0) - (0.5 if (v == tp or v == tn) else 0.0)

                    numer_hi = udx * vdx + udy * vdy
                    A[u, v] += numer_hi * dist_term * len_s * len_t
                    A[u, v] += (u_low * v_low) * kf_low * len_s * len_t
    return A

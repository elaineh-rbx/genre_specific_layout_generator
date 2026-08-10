"""Bit-exact port of racetrack-js/src/rng.js — the mulberry32 PRNG.

Matching the JS generator means a given seed produces the same blob seed curve
and the same boundary boxes as the web app's automatic mode.
"""

_U32 = 0xFFFFFFFF


def _imul(a, b):
    # JS Math.imul: 32-bit signed integer multiply.
    r = (a * b) & _U32
    return r - 0x100000000 if r & 0x80000000 else r


class Rng:
    def __init__(self, seed=0):
        s = seed & _U32
        self.state = s if s != 0 else 0x9E3779B9

    def next(self):
        # Mirror the JS bit ops: `|0` keeps 32-bit signed, `>>>` is unsigned shift.
        self.state = (self.state + 0x6D2B79F5) & _U32
        st = self.state
        t = _imul(st ^ (st >> 15), 1 | st) & _U32
        t = ((t + _imul(t ^ (t >> 7), 61 | t)) & _U32) ^ t
        t &= _U32
        return ((t ^ (t >> 14)) & _U32) / 4294967296.0

    # UnityEngine.Random.value : [0, 1]
    @property
    def value(self):
        return self.next()

    # UnityEngine.Random.Range(min, max) float overload.
    def range(self, lo, hi):
        return lo + self.next() * (hi - lo)


def seed_u32(x):
    """Reduce an int to the uint32 the JS `x >>> 0` would produce."""
    return x & _U32

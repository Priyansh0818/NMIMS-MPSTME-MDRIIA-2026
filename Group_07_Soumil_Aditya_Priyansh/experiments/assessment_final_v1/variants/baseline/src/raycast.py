"""Version-tolerant batched ray casting (mj_multiRay signature changed between MuJoCo releases)."""
import numpy as np, mujoco

GROUP0 = np.array([1, 0, 0, 0, 0, 0], dtype=np.uint8)   # furniture + clutter live in geom group 0; robot meshes in 2/3


def cast(m, d, origin, dirs, cutoff=6.0, exclude_body=-1, geomgroup=GROUP0):
    """dirs: (N,3) unit vectors.  Returns (geom_id[N], dist[N]) with geom_id=-1 / dist=-1 for misses."""
    n = len(dirs)
    gid = np.full(n, -1, dtype=np.int32); dist = np.full(n, -1.0)
    vec = np.ascontiguousarray(dirs, dtype=np.float64).reshape(-1)
    pnt = np.asarray(origin, dtype=np.float64)
    try:
        mujoco.mj_multiRay(m, d, pnt, vec, geomgroup, 1, exclude_body, gid, dist, None, n, cutoff)
    except TypeError:
        mujoco.mj_multiRay(m, d, pnt, vec, geomgroup, 1, exclude_body, gid, dist, n, cutoff)
    # mj_multiRay can miss the (bounded) floor plane for steep rays far from the origin: add the analytic z=0 hit.
    miss = (gid < 0) & (dirs[:, 2] < -1e-3) & (origin[2] > 0)
    if miss.any():
        t = origin[2] / -dirs[miss, 2]
        gid[miss] = np.where(t <= cutoff, 0, -1); dist[miss] = np.where(t <= cutoff, t, -1.0)
    return gid, dist


def ray1(m, d, origin, direction, cutoff=6.0, geomgroup=GROUP0):
    gid = np.zeros(1, dtype=np.int32)
    dist = mujoco.mj_ray(m, d, np.asarray(origin, float), np.asarray(direction, float), geomgroup, 1, -1, gid)
    return (int(gid[0]), float(dist)) if 0 <= dist <= cutoff else (-1, -1.0)


def ray1_excl(m, d, origin, direction, exclude_body, cutoff=6.0, geomgroup=GROUP0):
    gid = np.zeros(1, dtype=np.int32)
    dist = mujoco.mj_ray(m, d, np.asarray(origin, float), np.asarray(direction, float), geomgroup, 1, exclude_body, gid)
    return (int(gid[0]), float(dist)) if 0 <= dist <= cutoff else (-1, -1.0)

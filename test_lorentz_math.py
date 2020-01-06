import torch
import random
import numpy as np
import pytest
from geoopt.manifolds import lorentz

def seed():
    seed = 13
    torch.manual_seed(seed)
    random.seed(seed)
    np.random.seed(seed)
    return seed


def dtype():
    return torch.float32


def k(seed, dtype):
    # test broadcasted and non broadcasted versions
    if seed == 30:
        k = torch.tensor(0.0).to(dtype)
    elif seed == 35:
        k = torch.zeros(100, 1, dtype=dtype)
    elif seed > 35:
        k = torch.rand(100, 1, dtype=dtype)
    else:
        k = torch.tensor(random.random()).to(dtype)
    return torch.Tensor([1.])


def a(seed, k):
    if seed in {30, 35}:
        a = torch.randn(100, 10, dtype=k.dtype)
    elif seed > 35:
        # do not check numerically unstable regions
        # I've manually observed small differences there
        a = torch.empty(100, 10, dtype=k.dtype).normal_(-1, 1)
        a /= a.norm(dim=-1, keepdim=True) * 1.3
        a *= (torch.rand_like(k) * k) ** 0.5
    else:
        a = torch.empty(100, 10, dtype=k.dtype).normal_(-1, 1)
        a /= a.norm(dim=-1, keepdim=True) * 1.3
        a *= random.uniform(0, k) ** 0.5
    return lorentz.math.project(a, k=k)


def b(seed, k):
    if seed in {30, 35}:
        b = torch.randn(100, 10, dtype=k.dtype)
    elif seed > 35:
        b = torch.empty(100, 10, dtype=k.dtype).normal_(-1, 1)
        b /= b.norm(dim=-1, keepdim=True) * 1.3
        b *= (torch.rand_like(k) * k) ** 0.5
    else:
        b = torch.empty(100, 10, dtype=k.dtype).normal_(-1, 1)
        b /= b.norm(dim=-1, keepdim=True) * 1.3
        b *= random.uniform(0, k) ** 0.5
    return lorentz.math.project(b, k=k)


def test_expmap_logmap(a, b, k):
    # this test appears to be numerical unstable once a and b may appear on the opposite sides
    bh = lorentz.math.expmap(x=a, u=lorentz.math.logmap(a, b, k=k), k=k)
    tolerance = {torch.float32: dict(rtol=1e-5, atol=1e-6), torch.float64: dict()}
    print(k.dtype)
    np.testing.assert_allclose(bh, b, **tolerance[k.dtype])


def test_parallel_transport_a_b(a, b, k):
    v_0 = torch.rand_like(a)
    u_0 = torch.rand_like(a)

    v_0 = lorentz.math.project_u(a, v_0) # project on tangent plane
    u_0 = lorentz.math.project_u(a, u_0) # project on tangent plane

    v_1 = lorentz.math.parallel_transport(a, b, v_0, k=k)
    u_1 = lorentz.math.parallel_transport(a, b, u_0, k=k)

    vu_1 = lorentz.math.inner(v_1, u_1, keepdim=True)
    vu_0 = lorentz.math.inner(v_0, u_0, keepdim=True)

    np.testing.assert_allclose(vu_0, vu_1, atol=1e-6, rtol=1e-6)


def test_geodesic_segement_unit_property(a, b, k):
    extra_dims = len(a.shape)
    segments = 12
    t = torch.linspace(0, 1, segments + 1, dtype=k.dtype).view(
        (segments + 1,) + (1,) * extra_dims
    )

    b = lorentz.math.project_u(a, b)

    gamma_ab_t = lorentz.math.geodesic_unit(t, a, b, k=k)
    gamma_ab_t0 = gamma_ab_t[:1]
    gamma_ab_t1 = gamma_ab_t
    dist_ab_t0mt1 = lorentz.math.dist(gamma_ab_t0, gamma_ab_t1, k=k, keepdim=True)
    true_distance_travelled = t.expand_as(dist_ab_t0mt1)

    # we have exactly 12 line segments

    tolerance = {
        torch.float32: dict(atol=1e-6, rtol=1e-5),
        torch.float64: dict(atol=1e-10),
    }
    np.testing.assert_allclose(
        dist_ab_t0mt1, true_distance_travelled, **tolerance[k.dtype]
    )

if __name__ == "__main__":
    seed = seed()
    dtype = dtype()
    k = k(seed, dtype)
    a = a(seed, k)
    b = b(seed, k)

    #test_parallel_transport_a_b(a, b, k)
    test_expmap_logmap(a, b, k)
    #test_geodesic_segement_unit_property(a, b, k)
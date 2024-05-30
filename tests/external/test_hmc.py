import pytest

from climate_health.external.models.jax_models.hmc import sample
from climate_health.external.models.jax_models.utii import state_or_param, PydanticTree


@state_or_param
class NestedParams(PydanticTree):
    c: float = 0.0
    d: float = 0.0


@state_or_param
class DummyParam(PydanticTree):
    a: float = 0.0
    b: float = 0.0
    e: NestedParams = NestedParams()


@pytest.fixture
def init_params():
    return DummyParam(a=1.0, b=2.0, e=NestedParams(c=3.0, d=4.0))


def dummy_logprob_func(params):
    return params.a ** 2 - (params.b - 2) ** 3 + (params.e.c * params.e.d - 20) ** 2


def test_sample(init_params, random_key):
    sample(dummy_logprob_func, random_key, init_params, num_samples=100, num_warmup=100)
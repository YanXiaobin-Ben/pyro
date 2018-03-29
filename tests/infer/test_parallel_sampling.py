from __future__ import absolute_import, division, print_function

import logging

import pytest
import torch
from torch.distributions import constraints

import pyro
import pyro.distributions as dist
import pyro.optim
from pyro.infer.search import Search, ParallelSearch
from tests.common import assert_equal

logger = logging.getLogger(__name__)


@pytest.mark.parametrize("num_data", [2, 3, 4, 5])
def test_parallel_equals_sequential_naive(num_data):
    pyro.clear_param_store()
    data = torch.ones(num_data)
    init_probs = torch.tensor([0.5, 0.5])

    def model(data):
        transition_probs = pyro.param("transition_probs",
                                      torch.tensor([[0.9, 0.1], [0.1, 0.9]]),
                                      constraint=constraints.simplex)
        locs = pyro.param("obs_locs", torch.tensor([-1, 1]))
        scale = pyro.param("obs_scale", torch.tensor(1.0),
                           constraint=constraints.positive)

        x = None
        for i, y in enumerate(data):
            probs = init_probs if x is None else transition_probs[x]
            x = pyro.sample("x_{}".format(i), dist.Categorical(probs))
            pyro.sample("y_{}".format(i), dist.Normal(locs[x], scale), obs=y)

    # XXX max_iarange_nesting = 0 ?
    sequential_posterior = Search(model)
    parallel_posterior = ParallelSearch(model)

    parallel_trace = [(tr, log_w) for tr, log_w in parallel_posterior._traces(data)]
    seq_traces = [(tr, log_w) for tr, log_w in sequential_posterior._traces(data)]

    assert_equal(parallel_trace[0][1].size(), torch.Size([2]*num_data))

    assert_equal(parallel_trace[0][1].view(-1),
                 torch.stack([p[1] for p in seq_traces]))

    assert_equal(parallel_trace[0][1].sum().item(),
                 sum(map(lambda p: p[1], seq_traces)).sum().item())

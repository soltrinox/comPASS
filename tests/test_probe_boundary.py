"""Process-boundary smoke: route/graph imports must not pull probe.runner."""

from __future__ import annotations

import importlib
import sys


def test_route_decide_does_not_import_probe_runner():
    # Ensure a clean check of the module import graph after load
    for name in list(sys.modules):
        if name.startswith("compass.probe"):
            del sys.modules[name]
    importlib.import_module("compass.route.decide")
    assert "compass.probe.runner" not in sys.modules


def test_graph_does_not_import_probe_runner():
    for name in list(sys.modules):
        if name.startswith("compass.probe"):
            del sys.modules[name]
    importlib.import_module("compass.graph")
    assert "compass.probe.runner" not in sys.modules


#!/usr/bin/env python3
"""Compatibility shim for `team/tools/teamlib/` (the team-tier validator and compiler).

The code moved into the package (schema / io / compile / validate). This module keeps
`import _teamlib as lib` working for build.py, teamctl.py, deid.py, the tests and CI: it
re-exports every name of the four modules, private ones included, and forwards attribute
assignment (`lib.render_summary = fake`, used by tests) to every module that holds that name,
so a patch reaches the code that calls it. New code should import `teamlib` directly.
"""
from __future__ import annotations

import sys as _sys
import types as _types
from pathlib import Path as _Path

_HERE = str(_Path(__file__).resolve().parent)
if _HERE not in _sys.path:                   # loaded by file path: make the package importable
    _sys.path.insert(0, _HERE)

import importlib as _importlib  # noqa: E402

_pkg = _importlib.import_module("teamlib")
# By module path: the package re-exports the function `validate`, which shadows the submodule name.
_MODULES = tuple(_importlib.import_module(f"teamlib.{m}") for m in ("schema", "io", "compile", "validate"))
for _mod in _MODULES:
    for _name, _value in vars(_mod).items():
        if not (_name.startswith("__") and _name.endswith("__")):
            globals()[_name] = _value
del _mod, _name, _value


class _Shim(_types.ModuleType):
    def __setattr__(self, name: str, value) -> None:
        for mod in (*_MODULES, _pkg):
            if name in vars(mod):
                setattr(mod, name, value)
        super().__setattr__(name, value)


_sys.modules[__name__].__class__ = _Shim

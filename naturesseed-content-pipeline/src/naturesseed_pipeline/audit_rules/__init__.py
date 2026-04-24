"""Registry + directory discovery for decay rules."""

import importlib
import inspect
import pkgutil

from naturesseed_pipeline.audit_rules.base import DecayRule


def discover_rules() -> list[DecayRule]:
    """Instantiate every DecayRule-conforming class found in this package."""
    pkg = importlib.import_module("naturesseed_pipeline.audit_rules")
    rules: list[DecayRule] = []
    for info in pkgutil.iter_modules(pkg.__path__):
        if info.name in ("base", "__init__"):
            continue
        module = importlib.import_module(f"naturesseed_pipeline.audit_rules.{info.name}")
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if obj is DecayRule:
                continue
            if not hasattr(obj, "check") or not hasattr(obj, "name"):
                continue
            if obj.__module__ != module.__name__:
                continue  # skip imports
            try:
                rules.append(obj())
            except TypeError:
                pass
    return rules

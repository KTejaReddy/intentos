"""Code generation package: IR -> artifacts for every supported target."""

from .base import Generator, Registry
from .registry import global_registry, register_all

__all__ = ["Generator", "Registry", "global_registry", "register_all"]

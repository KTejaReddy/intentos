"""IntentLang Compiler — the deterministic core of IntentOS.

Pipeline: source -> Lexer -> Tokens -> Parser -> AST -> Semantic Analyzer -> IR
          -> Optimizer -> IR' -> Code Generators -> Artifacts.

Design invariants
-----------------
* Deterministic: identical source + options produce byte-identical artifacts.
* Zero third-party dependencies (stdlib only) so it runs anywhere, including
  inside the FastAPI backend process.
* AI never touches this package: anything here is pure, testable code.
"""

from .compiler import Compiler, CompileOptions, CompileResult
from .diagnostics import Diagnostics, Diagnostic, Severity
from .incremental import IncrementalEngine

__version__ = "1.0.0"
VERSION = __version__

__all__ = [
    "Compiler",
    "CompileOptions",
    "CompileResult",
    "Diagnostics",
    "Diagnostic",
    "Severity",
    "IncrementalEngine",
    "__version__",
]

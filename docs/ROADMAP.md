# IntentOS Roadmap (v2)

This document outlines the planned features and architectural upgrades for IntentOS version 2.0.

## Q1 2027: Complex Logic & Branching
- **If/Else Directives:** Add support for conditional branching within `When` clauses.
- **Loops & Iteration:** Enable list iteration (`For Each`) inside actions to batch process records.
- **Custom Computed Fields:** Allow models to define computed properties powered by mathematical formulas.

## Q2 2027: Safe Infrastructure Evolutions
- **Alembic/Prisma Migration Engine:** Generate deterministic `.sql` migration files based on AST diffing between sequential compilation runs to prevent data loss.
- **Redis Token Blacklisting:** Upgrade the `backend_fastapi.py` and `backend_spring.py` generators to inject Redis for true JWT revocation.

## Q3 2027: Native Mobile Targets
- **Flutter Code Generator:** Compile IntentLang directly to a full-stack Dart/Flutter mobile application.
- **SwiftUI Code Generator:** Native iOS target generation with CoreData mapping.

## Q4 2027: Language Server Protocol (LSP)
- **VS Code Extension:** Extract the `parser.py` and `semantic.py` core into an LSP server to enable native syntax highlighting, hover documentation, and auto-completion directly inside standard IDEs.
- **Strict AST Typing:** Re-architect `parser.py` AST nodes from dynamic objects to strict Python Dataclasses for enhanced type safety and structural validation.

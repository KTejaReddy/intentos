"""Keyword registry for IntentLang.

Keywords are statement / action / structure words. Property keys (e.g.
``Type``, ``Route``, ``Method``) are ordinary identifiers matched by the
parser in context — this keeps the language extensible: a plugin can define
new property keys without touching the lexer.

The set is deliberately small and versioned. Additions are backward
compatible because the parser matches on token text, not token identity.
"""

# Words that introduce a statement or a block structure.
STATEMENT_KEYWORDS = frozenset(
    {
        "create", "add", "field", "with", "when", "on", "use", "deploy",
        "import", "request", "response", "query",
    }
)

# Words that introduce an action inside an event block.
ACTION_KEYWORDS = frozenset(
    {
        "navigate", "open", "call", "show", "set", "submit", "reload",
        "close", "if", "else",
    }
)

# Reserved words inside Query blocks.
QUERY_KEYWORDS = frozenset(
    {"select", "from", "where", "join", "order", "by", "limit", "and", "or"}
)

# Literal keywords.
LITERAL_KEYWORDS = frozenset({"true", "false", "null"})

# Kinds allowed after ``Create``.
CREATE_KINDS = frozenset(
    {
        "application", "page", "database", "model", "api", "role", "job",
        "collection",
    }
)

# Widget kinds allowed after ``Add``.
WIDGET_KINDS = frozenset(
    {
        "input", "button", "text", "select", "table", "navbar", "card",
        "image", "form", "checkbox", "textarea", "link", "chart", "badge",
    }
)

KEYWORDS = (
    STATEMENT_KEYWORDS | ACTION_KEYWORDS | QUERY_KEYWORDS | LITERAL_KEYWORDS
)

# Field / entity types recognised by the semantic analyzer.
ENTITY_TYPES = frozenset(
    {
        "string", "text", "int", "integer", "float", "boolean", "bool",
        "date", "datetime", "email", "password", "id", "money", "url",
        "phone", "enum", "json",
    }
)

# Backend / frontend / database targets understood by code generators.
FRONTENDS = frozenset({"react", "next", "nextjs", "flutter"})
BACKENDS = frozenset({"fastapi", "express", "node", "spring", "springboot"})
DATABASES = frozenset({"sqlite", "postgres", "postgresql", "mysql"})

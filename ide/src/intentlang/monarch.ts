import * as monaco from "monaco-editor";

export const INTENTLANG_ID = "intentlang";

const STATEMENTS = [
  "create", "add", "field", "with", "when", "on", "use", "deploy", "import",
  "request", "response", "query", "select", "from", "where", "join", "order",
  "by", "limit",
];
const ACTIONS = [
  "navigate", "open", "call", "show", "set", "submit", "reload", "close",
  "api", "to", "toast",
];
const KINDS = [
  "application", "page", "database", "model", "api", "role", "job",
  "collection", "input", "button", "text", "select", "table", "navbar",
  "card", "image", "form", "checkbox", "textarea", "link", "chart", "badge",
];
const PROPS = [
  "type", "required", "unique", "primary", "default", "reference", "route",
  "method", "auth", "engine", "table", "title", "theme", "label", "text",
  "variant", "placeholder", "options", "src", "href", "layout", "status",
  "body", "list", "of", "language", "frontend", "backend", "database",
  "permissions", "description", "port",
];
const TYPES = [
  "string", "text", "int", "integer", "float", "boolean", "bool", "date",
  "datetime", "email", "password", "id", "money", "url", "phone", "enum",
  "json",
];
const LITERALS = ["true", "false", "null"];

export function defineIntentLang() {
  if (monaco.languages.getLanguages().some((l) => l.id === INTENTLANG_ID)) {
    return;
  }
  monaco.languages.register({ id: INTENTLANG_ID, extensions: [".intentlang", ".il"] });

  monaco.languages.setMonarchTokensProvider(INTENTLANG_ID, {
    defaultToken: "",
    tokenPostfix: ".il",
    keywords: [...STATEMENTS, ...ACTIONS, ...KINDS, ...LITERALS],
    typeKeywords: TYPES,
    propertyKeys: PROPS,
    tokenizer: {
      root: [
        [/\/\/.*$/, "comment"],
        [/\/\*/, "comment", "@comment"],
        [/[a-zA-Z_][a-zA-Z0-9_]*/, {
          cases: {
            "@keywords": "keyword",
            "@typeKeywords": "type",
            "@propertyKeys": "type.identifier",
            "@default": "identifier",
          },
        }],
        [/"([^"\\]|\\.)*$/, "string.invalid"],
        [/'([^'\\]|\\.)*$/, "string.invalid"],
        [/"/, "string", "@string_double"],
        [/'/, "string", "@string_single"],
        [/\/[a-zA-Z0-9_\-./{}:?&=*]+/, "number.hex"],
        [/\d+(\.\d+)?([eE][+-]?\d+)?/, "number"],
        [/[=<>!]+/, "operator"],
        [/[\[\],]/, "delimiter"],
        [/[{}]/, "delimiter.bracket"],
        [/[ \t\r\n]+/, "white"],
      ],
      comment: [
        [/[^/*]+/, "comment"],
        [/\*\//, "comment", "@pop"],
        [/[/*]/, "comment"],
      ],
      string_double: [
        [/[^\\"]+/, "string"],
        [/\\./, "string.escape"],
        [/"/, "string", "@pop"],
      ],
      string_single: [
        [/[^\\']+/, "string"],
        [/\\./, "string.escape"],
        [/'/, "string", "@pop"],
      ],
    },
  });

  monaco.editor.defineTheme("intentos-dark", {
    base: "vs-dark",
    inherit: true,
    rules: [
      { token: "keyword", foreground: "a5b4fc", fontStyle: "bold" },
      { token: "type", foreground: "6ee7b7" },
      { token: "type.identifier", foreground: "e6eaf3" },
      { token: "string", foreground: "fcd34d" },
      { token: "number", foreground: "f9a8d4" },
      { token: "number.hex", foreground: "67e8f9" },
      { token: "comment", foreground: "565f73", fontStyle: "italic" },
      { token: "operator", foreground: "94a3b8" },
    ],
    colors: {
      "editor.background": "#0b0f1a",
      "editor.foreground": "#e6eaf3",
      "editorLineNumber.foreground": "#3b4356",
      "editorCursor.foreground": "#a5b4fc",
      "editor.selectionBackground": "#33415566",
      "editor.lineHighlightBackground": "#ffffff08",
      "editorIndentGuide.background1": "#ffffff0d",
      "editorWidget.background": "#131a2b",
      "editorWidget.border": "#ffffff14",
    },
  });
}

export const COMPLETION_WORDS = [
  ...STATEMENTS.map((w) => w[0].toUpperCase() + w.slice(1)),
  ...KINDS.map((w) => w[0].toUpperCase() + w.slice(1)),
  ...PROPS.map((w) => w[0].toUpperCase() + w.slice(1)),
  "Create", "With", "Field", "Add", "When", "On", "Call Api", "Navigate To",
  "Show Toast", "Deploy Docker", "Use Pwa", "Use Seo", "Import",
];

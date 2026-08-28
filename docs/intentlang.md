# IntentLang Language Reference

IntentLang is the deterministic intermediate language of IntentOS. It is:

- **Human readable** — reads like structured English.
- **Deterministic** — the same program always compiles to the same artifacts.
- **Compiler friendly** — indentation-based blocks, a small fixed keyword set,
  and a strictly ordered grammar make it trivial to lex and parse.
- **Versionable** — the IR carries a schema version; artifacts are reproducible.
- **Extensible** — unknown property values degrade gracefully, and the plugin
  system adds generator behavior without touching the core language.

The language is case-insensitive for keywords; identifiers preserve their
spelling.

---

## 1. Lexical structure

| Element      | Example                     | Notes |
|--------------|-----------------------------|-------|
| Comment      | `// this is a comment`      | `//` to end of line |
| Application  | `Student Portal`            | multi-word names allowed |
| String       | `"Hello world"`             | double-quoted |
| Number       | `42`, `3.14`                | integer or decimal |
| Boolean      | `true`, `false`             | lowercase |
| List         | `[view, create, update]`    | comma-separated idents |
| Route        | `/api/students`             | bare `/` and `{param}` supported |
| Field type   | `string`, `email`, `money`  | see table below |
| Ident        | `Name`, `ListStudents`      | letters, digits, underscores |

Indentation defines blocks: the first indented line opens a block at that
column; every deeper level nests; returning to a shallower column closes
blocks. **No braces, no semicolons.**

### Field types

`id`, `string`, `text`, `email`, `phone`, `password`, `money`, `int`, `float`,
`bool`, `date`, `datetime`, `time`, `enum`, `json`, `image`, `file`, `url`.

---

## 2. Statements

### 2.1 `Create Application <Name>`

Declares the application. Properties in its `With` block:

```
Create Application Student Portal
  With
    Title "Student Portal"
    Description "Manage courses, grades and teachers"
    Theme indigo            // color token: indigo, violet, emerald, rose, amber, slate
    Database sqlite         // sqlite | postgres | mysql
```

### 2.2 `Create Role <Name>`

Declares a user role.

```
Create Role Student
  With
    Permissions [view, create, update]
```

### 2.3 `Create Model <Name>`

Declares a database entity. `With Table <table>` names the table; `Field`
children declare columns. First `Field` with `Type id` becomes the primary key.

```
Create Model Student
  With
    Table students
  Field Id
    Type id
  Field Name
    Type string
    Required true
  Field Email
    Type email
    Unique true
  Field Grade
    Type enum
```

### 2.4 `Create Api <Name>`

Declares a REST endpoint. The `With` block carries metadata; `Request`,
`Query`, and `Response` blocks define contracts.

```
Create Api ListStudents
  With
    Method GET
    Route /api/students
    Auth user               // public | user | <role-name>
    Title "List students"
  Query
    Select
    From students
  Response
    Status 200
    Body List Student
```

```
Create Api CreateStudent
  With
    Method POST
    Route /api/students
    Auth user
  Request
    Field Name
      Type string
    Field Email
      Type email
  Response
    Status 201
    Body Student
```

Optional capability sections:

```
  With
    ...
    Rate Limit 100
    Cached true
    Paginated true
```

### 2.5 `Create Page <Name>`

Declares a screen. `With` sets metadata; widget children build the UI.

```
Create Page Home
  With
    Route /
    Title "Home"
    Layout app               // app | auth | blank
  Add NavBar Nav
    With
      Brand "Student Portal"
  Add Text HomeTitle
    With
      Text "Home"
      Variant heading
  Add Table StudentsTable
    With
      Api ListStudents
```

#### Widgets

| Widget     | Key properties |
|------------|----------------|
| `Add Text <id>`       | `Text`, `Variant` (heading / subheading / body / caption) |
| `Add Button "<label>"`| `Variant` (primary / secondary / ghost / danger) |
| `Add Input <id>`      | `Label`, `Type` (text / password / email / number), `Required`, `Placeholder` |
| `Add NavBar <id>`     | `Brand` |
| `Add Table <id>`      | `Api <api>`, `Columns [Name, Email]` |
| `Add Chart <id>`      | `Type` (bar / line / pie), `Api <api>`, `X`, `Y` |
| `Add Card <id>`       | `Title`, `Text` |

#### Events

Widgets can attach handlers with `When <event>` blocks. Supported events:

| Event              | Example |
|--------------------|---------|
| `When Clicked`     | buttons, cards |
| `When Changed`     | inputs, selects |

Actions inside event blocks:

```
  Add Button "Sign In"
    When Clicked
      Call Api Login
        With
          Body {
            Username = Username
            Password = Password
          }
        On Success
          Navigate To Home
        On Failure
          Show Toast "Invalid credentials"

  Add Input Email
    When Changed
      Set Page State email
```

`Call Api <name>` may carry `With Body { … }` (field mappings from widget ids),
then `On Success` / `On Failure` handler blocks with actions:

- `Navigate To <page>`
- `Show Toast "<message>"`
- `Set Page State <key>`
- `Open Modal <id>`
- `Close Modal <id>`
- `Log "<message>"`

---

## 3. Rules

### 3.1 `When <event>`

Declares an app-level rule. Canonical example:

```
When Login succeeds
  Open Home
```

Events: `<Api> succeeds`, `<Api> fails`, `App starts`.

---

## 4. Deployment

```
Deploy Docker
  With
    Port 8000

Deploy Kubernetes
  With
    Replicas 3
```

Targets: `Docker`, `Kubernetes`.

---

## 5. Comments and blank lines

Blank lines are ignored between statements. `//` comments are stripped at
lexing time, so they can appear anywhere.

---

## 6. Compilation guarantees

- The **semantic analyzer** reports unknown model/page/api references, route
  collisions (method-aware: `GET /students` and `POST /students` coexist),
  duplicate declarations, invalid auth roles, and unresolved widget ids.
- The **optimizer** eliminates models, pages, and APIs that are unreferenced
  by any live entity (while preserving everything reachable from rules).
- The **IR** is versioned and JSON-serializable; `CompileOptions` can disable
  optimization for debugging.
- Output artifacts are deterministic — the same input yields byte-identical
  outputs across runs and machines.

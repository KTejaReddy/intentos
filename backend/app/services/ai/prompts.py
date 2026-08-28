"""System prompts enforcing the IntentOS policy: AI writes IntentLang, never
production source code. All LLM output is parsed back into IntentLang source
or structured JSON."""

from __future__ import annotations

import json
import re

INTENTLANG_GUIDE = """IntentLang is the deterministic intermediate language of IntentOS.
It is NOT code. It declares an application: pages, widgets, data models,
APIs, roles, rules and deployment targets. The compiler turns it into the
real application.

Grammar essentials:
  Create Application <Name>
    With
      Title "..."
      Theme <indigo|blue|emerald|rose|amber|slate|violet>
      Database sqlite|postgres|mysql

  Create Page <Name>
    With
      Route /path
    Add Input <Name>
      With
        Label "..."
        Type <text|password|email>
        Required true
    Add Button "<Label>"
      When Clicked
        Call Api <ApiName>
          On Success
            Navigate To <PageName>
          On Failure
            Show Toast "..."
    Add NavBar <Name>
    Add Text <Name>
      With
        Text "..."
        Variant heading
    Add Table <Name>
      With
        Api <ListApi>
    Add Form <FormName>
      With
        Api <SaveApi>
      Add Input <FieldName>
      Add Button "Save"
        When Clicked
          Submit <FormName>

  Create Model <Name>
    With
      Table <plural>
    Field <Name>
      Type <string|text|int|float|boolean|date|datetime|email|password|money|url|enum>
      Required true
      Unique true
      Reference OtherModel.id

  Create Api <Name>
    With
      Method GET|POST|PUT|DELETE
      Route /api/...
      Auth public|user|admin|<RoleName>
    Request
      Field <Name>
        Type <type>
    Query
      Select
      From <table>
      Where <field> = <param>
      Order By <field>
    Response
      Status 200
      Body <Model>          (or: Body List Model)

  Create Role <Name>
    With
      Permissions [a, b, c]

  Use <Plugin>             (pwa, seo)
  Deploy Docker
  When <event>
    <action>

Rules for you:
- Output ONLY IntentLang between the markers. No code, no JSON, no prose
  outside markers. Comments with // are allowed.
- Names are PascalCase or plain words. Routes start with /.
- Every page the user needs gets a Create Page. Every data concept gets a
  Create Model + CRUD Create Api entries. Wire buttons to APIs with
  Call Api / On Success / On Failure and Navigate To.
- Include login/logout when the app has users.
- Keep it deterministic: no free-form expressions.
"""

PLANNER_SYSTEM = (
    "You are the AI Planner of IntentOS. You convert a natural-language "
    "software idea into an IntentLang program.\n\n"
    + INTENTLANG_GUIDE
)

INTENT_SYSTEM = """You extract structured product intent from a user's idea.
Reply with ONLY a JSON object of the form:
{"app_name": "...", "summary": "...", "domain": "...", "users": ["..."],
 "features": ["..."], "entities": ["..."]}
No markdown fences."""

REQUIREMENTS_SYSTEM = """You are a product analyst. Given a software idea,
list missing requirements and return ONLY JSON:
{"missing": ["..."], "questions": [{"id": "q1", "question": "...",
 "options": ["..."], "reason": "..."}]}
No markdown fences."""

RESEARCH_SYSTEM = """You research competitors for a software idea. Reply with
ONLY JSON: {"competitors": [{"name": "...", "summary": "..."}]} — no markdown
fences. If you genuinely do not know, return {"competitors": []}."""


def extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        return {}


def extract_intentlang(text: str) -> str:
    """Extract the IntentLang source from a model reply.

    Accepts optional markers and tolerates prose around the program.
    """
    m = re.search(r"```(?:intentlang)?\s*(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    # Fall back to everything that looks like IntentLang statements.
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("Create ", "When ", "Use ", "Deploy ",
                                "Import ")) or stripped.startswith(("  ", "\t")):
            lines.append(line)
    return "\n".join(lines).strip()

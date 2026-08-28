"""Deterministic heuristic planner.

Turns a natural-language idea into structured intent and a full IntentLang
program without any language model. Used as the offline provider and as a
fallback when the LLM output is unusable.

Rule-based and fully deterministic: the same idea always produces the same
IntentLang. This honors the IntentOS policy — the output is IntentLang, never
production code.
"""

from __future__ import annotations

import re
from typing import Optional


# ---------------------------------------------------------------- domains ---
DOMAINS = [
    {
        "keys": ["food", "restaurant", "delivery", "food delivery", "eat", "meal", "kitchen"],
        "name": "food delivery",
        "app_suffix": "Delivery",
        "entities": [
            ("Restaurant", "restaurants", ["Name", "Cuisine", "City", "Rating"]),
            ("MenuItem", "menu_items", ["Name", "Description", "Price", "Restaurant"]),
            ("Order", "orders", ["CustomerName", "Items", "Total", "Status"]),
            ("DeliveryPartner", "delivery_partners", ["Name", "Phone", "Status"]),
        ],
        "pages": {
            "Home": "/",
            "Menu": "/menu",
            "Cart": "/cart",
            "Checkout": "/checkout",
            "Orders": "/orders",
            "Login": "/login",
            "Admin Dashboard": "/admin",
        },
    },
    {
        "keys": ["ecommerce", "e-commerce", "shop", "store", "commerce", "product", "marketplace", "sell"],
        "name": "e-commerce",
        "app_suffix": "Store",
        "entities": [
            ("Product", "products", ["Name", "Description", "Price", "Category", "Stock"]),
            ("Category", "categories", ["Name"]),
            ("Order", "orders", ["CustomerName", "Total", "Status"]),
            ("Cart", "carts", ["CustomerName", "Items"]),
        ],
        "pages": {"Home": "/", "Products": "/products", "Cart": "/cart",
                  "Checkout": "/checkout", "Login": "/login", "Admin Dashboard": "/admin"},
    },
    {
        "keys": ["education", "school", "student", "learning", "course", "college", "university", "academy"],
        "name": "education",
        "app_suffix": "Portal",
        "entities": [
            ("Student", "students", ["Name", "Email", "Grade"]),
            ("Course", "courses", ["Name", "Teacher", "Credits"]),
            ("Enrollment", "enrollments", ["Student", "Course", "Status"]),
            ("Teacher", "teachers", ["Name", "Email", "Subject"]),
        ],
        "pages": {"Home": "/", "Courses": "/courses", "Grades": "/grades",
                  "Profile": "/profile", "Login": "/login", "Admin Dashboard": "/admin"},
    },
    {
        "keys": ["booking", "reserve", "appointment", "reservation", "schedule", "rent"],
        "name": "booking",
        "app_suffix": "Booking",
        "entities": [
            ("Service", "services", ["Name", "Description", "Price", "Duration"]),
            ("Booking", "bookings", ["CustomerName", "Service", "Date", "Status"]),
            ("Customer", "customers", ["Name", "Email", "Phone"]),
        ],
        "pages": {"Home": "/", "Services": "/services", "Booking": "/booking",
                  "My Bookings": "/my-bookings", "Login": "/login", "Admin Dashboard": "/admin"},
    },
    {
        "keys": ["social", "community", "feed", "follow", "chat", "messaging"],
        "name": "social",
        "app_suffix": "Social",
        "entities": [
            ("User", "users", ["Name", "Email", "Bio"]),
            ("Post", "posts", ["Author", "Content", "Likes"]),
            ("Comment", "comments", ["Post", "Author", "Content"]),
            ("Message", "messages", ["Sender", "Recipient", "Content"]),
        ],
        "pages": {"Feed": "/", "Profile": "/profile", "Messages": "/messages",
                  "Login": "/login", "Explore": "/explore"},
    },
    {
        "keys": ["crm", "customer", "sales", "pipeline", "lead", "business"],
        "name": "crm",
        "app_suffix": "CRM",
        "entities": [
            ("Contact", "contacts", ["Name", "Email", "Phone", "Company"]),
            ("Lead", "leads", ["Name", "Source", "Status", "Value"]),
            ("Deal", "deals", ["Name", "Value", "Stage", "Owner"]),
            ("Task", "tasks", ["Title", "DueDate", "Assignee", "Status"]),
        ],
        "pages": {"Dashboard": "/", "Contacts": "/contacts", "Leads": "/leads",
                  "Deals": "/deals", "Tasks": "/tasks", "Login": "/login"},
    },
    {
        "keys": ["health", "clinic", "hospital", "doctor", "patient", "fitness", "gym"],
        "name": "health",
        "app_suffix": "Health",
        "entities": [
            ("Patient", "patients", ["Name", "Email", "Phone", "History"]),
            ("Doctor", "doctors", ["Name", "Specialty", "Email"]),
            ("Appointment", "appointments", ["Patient", "Doctor", "Date", "Status"]),
            ("Record", "records", ["Patient", "Notes", "Date"]),
        ],
        "pages": {"Home": "/", "Doctors": "/doctors", "Appointments": "/appointments",
                  "Records": "/records", "Login": "/login", "Admin Dashboard": "/admin"},
    },
    {
        "keys": ["finance", "bank", "pay", "invoice", "expense", "accounting", "budget", "wallet"],
        "name": "finance",
        "app_suffix": "Finance",
        "entities": [
            ("Account", "accounts", ["Name", "Type", "Balance"]),
            ("Transaction", "transactions", ["Account", "Amount", "Category", "Date"]),
            ("Invoice", "invoices", ["Client", "Amount", "Status", "DueDate"]),
        ],
        "pages": {"Dashboard": "/", "Accounts": "/accounts", "Transactions": "/transactions",
                  "Invoices": "/invoices", "Login": "/login"},
    },
    {
        "keys": ["task", "todo", "project", "kanban", "issue", "tracker", "team"],
        "name": "productivity",
        "app_suffix": "Workspace",
        "entities": [
            ("Project", "projects", ["Name", "Description", "Status"]),
            ("Task", "tasks", ["Title", "Project", "Assignee", "Status", "DueDate"]),
            ("Team", "teams", ["Name", "Members"]),
        ],
        "pages": {"Dashboard": "/", "Projects": "/projects", "Tasks": "/tasks",
                  "Teams": "/teams", "Login": "/login"},
    },
    {
        "keys": ["news", "blog", "content", "article", "magazine", "publish"],
        "name": "content",
        "app_suffix": "Media",
        "entities": [
            ("Article", "articles", ["Title", "Author", "Content", "PublishedAt"]),
            ("Author", "authors", ["Name", "Email", "Bio"]),
            ("Category", "categories", ["Name"]),
        ],
        "pages": {"Home": "/", "Articles": "/articles", "Article Detail": "/article",
                  "Authors": "/authors", "Login": "/login", "Admin Dashboard": "/admin"},
    },
]

GENERIC_ENTITIES = [
    ("Item", "items", ["Name", "Description"]),
    ("User", "users", ["Name", "Email"]),
    ("Order", "orders", ["CustomerName", "Total", "Status"]),
]

GENERIC_PAGES = {"Home": "/", "Items": "/items", "Login": "/login", "Admin Dashboard": "/admin"}

INTENT_KEYWORDS = {
    "login": ["login", "sign in", "auth", "account"],
    "payment": ["pay", "payment", "checkout", "upi", "card"],
    "notifications": ["notify", "notification", "alert"],
    "search": ["search", "discover", "explore"],
    "reviews": ["review", "rating", "rate"],
    "tracking": ["track", "status", "live"],
    "admin": ["admin", "dashboard", "manage"],
    "chat": ["chat", "message", "support"],
}


def _clean(idea: str) -> str:
    return re.sub(r"\s+", " ", idea.strip())


def detect_domain(idea: str) -> Optional[dict]:
    low = idea.lower()
    for domain in DOMAINS:
        if any(k in low for k in domain["keys"]):
            return domain
    return None


def extract_location(idea: str) -> str:
    m = re.search(r"(?:for|in|targeting)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)", idea)
    if m:
        return m.group(1).strip()
    return ""


def detect_features(idea: str) -> list[str]:
    low = idea.lower()
    features = []
    for feature, keys in INTENT_KEYWORDS.items():
        if any(k in low for k in keys):
            features.append(feature)
    return features


def app_name(idea: str, domain: dict | None, location: str) -> str:
    # Drop a trailing audience/location phrase: "for kids", "in Delhi", "for teens".
    core = re.sub(
        r"(?:for|in|with)\s+[A-Za-z][A-Za-z]+(?:\s+[A-Za-z][A-Za-z]+)*$", "", idea.strip()
    )
    core = re.sub(
        r"^(?:(?:create|make|build|develop|launch|start|design)\s+)?(?:an?|the)\s+",
        "", core.strip(), flags=re.I,
    )
    core = re.sub(
        r"\s+(app|application|platform|startup|website|software|service|portal|system|tool|site)s?\s*$",
        "", core, flags=re.I,
    )
    words = [w for w in core.split() if w.lower() not in ("for", "to", "with")]
    candidate = " ".join(words[:3]).title().strip()
    if len(candidate) < 3:
        suffix = domain["app_suffix"] if domain else "App"
        candidate = f"{location or 'My'}{suffix}" if location else suffix
    return candidate


def analyze_intent(idea: str) -> dict:
    idea = _clean(idea)
    domain = detect_domain(idea)
    location = extract_location(idea)
    features = detect_features(idea)
    users = ["admin"]
    if domain:
        if domain["name"] in ("food delivery", "e-commerce", "booking"):
            users = ["customer", "admin"]
        elif domain["name"] in ("education",):
            users = ["student", "teacher", "admin"]
        elif domain["name"] == "health":
            users = ["patient", "doctor", "admin"]
        else:
            users = ["user", "admin"]
    entities = [e[0] for e in (domain["entities"] if domain else GENERIC_ENTITIES)]
    return {
        "idea": idea,
        "app_name": app_name(idea, domain, location),
        "summary": f"{domain['name'] if domain else 'custom'} application for {location or 'general users'}",
        "domain": domain["name"] if domain else "general",
        "users": users,
        "features": features or ["core_crud"],
        "entities": entities,
        "source": "heuristic",
    }


def missing_requirements(idea: str) -> list[dict]:
    intent = analyze_intent(idea)
    out = []
    low = idea.lower()
    checks = [
        ("auth", "Authentication / roles", bool(intent.get("users")) or any(k in low for k in ["login", "user", "account"])),
        ("payments", "Online payments", any(k in low for k in ["pay", "checkout", "cart", "order"])),
        ("notifications", "Push notifications", any(k in low for k in ["notify", "alert", "track"])),
        ("location", "Map / location services", any(k in low for k in ["deliver", "location", "city", "nearby"])),
        ("multi_lang", "Multi-language UI", any(k in low for k in ["india", "hyderabad", "mumbai", "bengaluru", "delhi"])),
        ("offline", "Offline mode", "social" in intent.get("domain", "")),
    ]
    for fid, label, should_ask in checks:
        if should_ask:
            out.append({
                "id": fid,
                "question": f"Should the app include {label.lower()}?",
                "options": ["Yes", "No"],
                "reason": f"suggested because the idea mentions concepts related to {fid}",
            })
    return out


# ---------------------------------------------------------------- IntentLang ---
def generate_intentlang(idea: str) -> str:
    idea = _clean(idea)
    intent = analyze_intent(idea)
    domain = detect_domain(idea)
    location = extract_location(idea)
    entities = (domain["entities"] if domain else GENERIC_ENTITIES)
    pages = (domain["pages"] if domain else GENERIC_PAGES)
    users = intent["users"]

    L: list[str] = [
        "// ============================================================",
        f"// {intent['app_name']} — generated by the IntentOS heuristic planner",
        f"// idea: {idea}",
        "// ============================================================",
        "",
        f"Create Application {intent['app_name']}",
        "  With",
        f'    Title "{intent["app_name"]}"',
        "    Theme indigo",
        f'    Description "{intent["summary"]}"',
        "    Database sqlite",
        "",
    ]

    # Roles — skip the implicit built-ins (public, user, admin) that the
    # compiler injects; only explicit business roles are declared.
    role_map = {"admin": "Admin", "user": "User", "customer": "Customer",
                "student": "Student", "teacher": "Teacher", "patient": "Patient",
                "doctor": "Doctor"}
    IMPLICIT_ROLES = {"public", "user", "admin"}
    for u in users:
        if u.lower() in IMPLICIT_ROLES:
            continue
        name = role_map.get(u, u.title())
        L.append(f"Create Role {name}")
        L.append("  With")
        L.append("    Permissions [view, create, update]")
        L.append("")

    home_page = next((n for n, r in pages.items() if r == "/"), None) or "Home"

    # Login page when there are users beyond guests
    needs_login = "login" in [p.lower() for p in pages]
    if needs_login:
        L.extend([
            "Create Page Login",
            "  With",
            "    Route /login",
            "    Layout auth",
            "  Add Input Username",
            "    With",
            '      Label "Username"',
            "      Required true",
            "  Add Input Password",
            "    With",
            '      Label "Password"',
            "      Type password",
            "      Required true",
            '  Add Button "Sign In"',
            "    When Clicked",
            "      Call Api Login",
            "        On Success",
            f"          Navigate To {home_page}",
            "        On Failure",
            '          Show Toast "Invalid credentials"',
            "",
        ])

    # Domain pages
    page_names = list(pages.items())
    for idx, (name, route) in enumerate(page_names):
        if name == "Login":
            continue
        L.append(f"Create Page {name}")
        L.append("  With")
        L.append(f"    Route {route}")
        L.append(f'    Title "{name}"')
        if idx == 0 or route == "/":
            L.append("  Add NavBar Nav")
        L.append(f'  Add Text {name.replace(" ", "")}Title')
        L.append("    With")
        L.append(f'      Text "{name}"')
        L.append("      Variant heading")
        L.append(f"  Add Table {name.replace(' ', '')}Table")
        L.append("    With")
        L.append(f"      Api List{_plural(_entity_for_page(name, entities, idx))}")
        if idx == 0:
            L.append("  Add Button \"Logout\"")
            L.append("    When Clicked")
            L.append("      Call Api Logout")
            L.append("        On Success")
            L.append("          Navigate To Login")
        L.append("")

    # Models
    for (ename, table, fields) in entities:
        L.append(f"Create Model {ename}")
        L.append("  With")
        L.append(f"    Table {table}")
        L.append("  Field Id")
        L.append("    Type id")
        for fname, ftype in _field_types(fields):
            L.append(f"  Field {fname}")
            L.append(f"    Type {ftype}")
            if fname == "Email":
                L.append("    Unique true")
        L.append("")

    # CRUD APIs
    for (ename, table, fields) in entities:
        L.append(f"Create Api List{_plural(ename)}")
        L.append("  With")
        L.append("    Method GET")
        L.append(f"    Route /api/{table}")
        L.append("    Auth user")
        L.append("  Query")
        L.append("    Select")
        L.append(f"    From {table}")
        L.append("  Response")
        L.append("    Status 200")
        L.append(f"    Body List {ename}")
        L.append("")
        L.append(f"Create Api Create{ename}")
        L.append("  With")
        L.append("    Method POST")
        L.append(f"    Route /api/{table}")
        L.append("    Auth user")
        L.append("  Request")
        for fname, _ft in _field_types(fields):
            L.append(f"    Field {fname}")
        L.append("  Response")
        L.append("    Status 201")
        L.append(f"    Body {ename}")
        L.append("")

    # Auth APIs
    L.extend([
        "Create Api Login",
        "  With",
        "    Method POST",
        "    Route /api/login",
        "    Auth public",
        "  Request",
        "    Field Username",
        "      Type string",
        "    Field Password",
        "      Type password",
        "  Response",
        "    Status 200",
        "    Body token",
        "",
        "Create Api Logout",
        "  With",
        "    Method POST",
        "    Route /api/logout",
        "    Auth public",
        "  Response",
        "    Status 200",
        "",
    ])

    # Rules
    L.append("When Login succeeds")
    L.append(f"  Open {home_page}")
    L.append("")

    L.append("Deploy Docker")
    L.append("  With")
    L.append("    Port 8000")
    L.append("")
    return "\n".join(L)


def _plural(name: str) -> str:
    if name.lower().endswith("y") and len(name) > 1 and name[-2].lower() not in "aeiou":
        return name[:-1] + "ies"
    if name.lower().endswith("s"):
        return name + "es"
    return name + "s"


def _entity_for_page(page_name: str, entities: list, idx: int) -> str:
    """Pick the entity a page's table should list: match the page name to an
    entity (singularized), else cycle deterministically through the entities."""
    singular = page_name[:-1] if page_name.lower().endswith("s") else page_name
    for (ename, _table, _fields) in entities:
        if ename.lower() == singular.lower():
            return ename
    return entities[idx % len(entities)][0]


def _field_types(fields: list) -> list[tuple]:
    mapping = {
        "Name": "string", "Description": "text", "Price": "money",
        "Email": "email", "Phone": "phone", "Status": "enum",
        "Date": "date", "DueDate": "date", "Total": "money",
        "Amount": "money", "Balance": "money", "Value": "money",
        "Likes": "int", "Stock": "int", "Credits": "int",
        "Rating": "float", "Content": "text", "Bio": "text",
        "History": "text", "Notes": "text", "City": "string",
        "Cuisine": "string", "Category": "string", "Type": "enum",
        "Author": "string", "CustomerName": "string", "Items": "text",
        "Source": "string", "Stage": "enum", "Assignee": "string",
        "Owner": "string", "Title": "string", "Subject": "string",
        "Specialty": "string", "Members": "text", "Client": "string",
        "Company": "string", "Teacher": "string", "Student": "string",
        "Course": "string", "Restaurant": "string", "Service": "string",
        "Patient": "string", "Doctor": "string", "Account": "string",
        "PublishedAt": "datetime", "Duration": "int",
        "Recipient": "string", "Sender": "string", "Post": "string",
        "CreatedAt": "datetime",
    }
    return [(f, mapping.get(f, "string")) for f in fields]

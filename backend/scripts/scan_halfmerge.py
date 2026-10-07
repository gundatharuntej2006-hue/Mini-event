"""
Find half-merged references: code that calls something which does not exist.

Two of these were already hit at runtime and both answered 500 on production:
  * round_service read timing.rule_penalty_seconds, a column the model never
    declared -> GET/PUT /api/rounds/1/records
  * round_service called code_hunt_service.record_fragment, which on this
    build is only record_fragment_1..4 -> PUT /api/rounds/3/codes/fragment

They share a cause: a branch merged a service but not the model or helper it
depends on. Python does not catch that until the line runs, and the line only
runs when an organiser clicks the thing. This walks the AST instead.

Run it:
    cd backend
    <venv>/Scripts/python scripts/scan_halfmerge.py
"""

import ast
import importlib
import os
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("SECRET_KEY", "scan_only_secret_key_at_least_32_characters_ok")
os.environ.setdefault("DATABASE_URL",
                      f"sqlite:///{(Path(tempfile.gettempdir()) / 'eventhq_scan.db').as_posix()}")

APP = BACKEND / "app"
problems = []


def module_name(path: Path) -> str:
    return ".".join(path.relative_to(BACKEND).with_suffix("").parts)


# ---- pass 1: module-level attribute calls (service.helper(...)) ------------
for py in sorted(APP.rglob("*.py")):
    try:
        tree = ast.parse(py.read_text(encoding="utf-8"))
    except SyntaxError:
        continue

    # alias -> dotted module, for `from app.services import x` and `import app.x as y`
    aliases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app"):
            for a in node.names:
                aliases[a.asname or a.name] = f"{node.module}.{a.name}"
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.name.startswith("app"):
                    aliases[a.asname or a.name.split(".")[0]] = a.name

    for node in ast.walk(tree):
        if not (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)):
            continue
        target = aliases.get(node.value.id)
        if not target:
            continue
        try:
            mod = importlib.import_module(target)
        except Exception:  # noqa: BLE001  - not a module (a class, or import side effects)
            continue
        if not hasattr(mod, node.attr):
            problems.append(
                f"{module_name(py)}:{node.lineno}  {node.value.id}.{node.attr} "
                f"does not exist in {target}"
            )

# ---- pass 2: ORM column references on our own models ----------------------
# Catches the rule_penalty_seconds case: service reads an attribute the model
# never mapped, so it only fails when that row is touched.
try:
    from app.db.base import Base  # noqa: E402

    import app.models  # noqa: F401,E402

    for py in sorted(APP.rglob("*.py")):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        local = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and "models" in node.module:
                for a in node.names:
                    local[a.asname or a.name] = a.name
        if not local:
            continue
        mapped = {}
        for cls in Base.registry._class_registry.values():  # noqa: SLF001
            name = getattr(cls, "__name__", None)
            if name and hasattr(cls, "__table__"):
                mapped[name] = set(c.key for c in cls.__table__.columns) | set(
                    getattr(cls, "__mapper__").relationships.keys()
                )
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)):
                continue
            cls_name = local.get(node.value.id)
            if cls_name and cls_name in mapped and node.attr not in mapped[cls_name]:
                if node.attr.startswith("_") or node.attr in dir(object):
                    continue
                if hasattr(Base.registry._class_registry.get(cls_name, object), node.attr):  # noqa: SLF001
                    continue
                problems.append(
                    f"{module_name(py)}:{node.lineno}  {cls_name}.{node.attr} is not a mapped column"
                )
except Exception as e:  # noqa: BLE001
    print(f"  (model pass skipped: {e})")

print()
if problems:
    print(f"{len(problems)} half-merged reference(s):\n")
    for p in sorted(set(problems)):
        print("  " + p)
else:
    print("No half-merged references found.")
sys.exit(1 if problems else 0)

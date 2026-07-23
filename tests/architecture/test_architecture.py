import ast
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "identity_service"

FORBIDDEN_EVERYWHERE = {"vehicle_sales_service"}
FORBIDDEN_IN_DOMAIN = {
    "fastapi",
    "starlette",
    "pydantic",
    "pydantic_settings",
    "pymongo",
    "bson",
    "motor",
    "redis",
    "httpx",
    "jwt",
    "cryptography",
    "argon2",
    "uvicorn",
    "prometheus_client",
    "identity_service.application",
    "identity_service.infrastructure",
    "identity_service.entrypoints",
    "os",
}
FORBIDDEN_IN_APPLICATION = {
    "fastapi",
    "starlette",
    "pydantic",
    "pydantic_settings",
    "pymongo",
    "bson",
    "motor",
    "redis",
    "httpx",
    "jwt",
    "cryptography",
    "argon2",
    "uvicorn",
    "prometheus_client",
    "identity_service.infrastructure",
    "identity_service.entrypoints",
}
FORBIDDEN_IN_ROUTERS = {"pymongo", "bson", "motor"}


def python_files(relative: str) -> list[Path]:
    root = SRC_ROOT / relative if relative else SRC_ROOT
    return sorted(root.rglob("*.py"))


def imports_of(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def violations(files: list[Path], forbidden: set[str]) -> list[str]:
    found: list[str] = []
    for path in files:
        for module in imports_of(path):
            for banned in forbidden:
                if module == banned or module.startswith(f"{banned}."):
                    found.append(f"{path.relative_to(SRC_ROOT)} imports {module}")
    return found


def test_domain_does_not_depend_on_frameworks_or_outer_layers() -> None:
    assert violations(python_files("domain"), FORBIDDEN_IN_DOMAIN) == []


def test_application_does_not_depend_on_frameworks_or_adapters() -> None:
    assert violations(python_files("application"), FORBIDDEN_IN_APPLICATION) == []


def test_routers_do_not_touch_mongodb() -> None:
    assert violations(python_files("entrypoints/http/routers"), FORBIDDEN_IN_ROUTERS) == []


def test_service_never_imports_the_other_service() -> None:
    assert violations(python_files(""), FORBIDDEN_EVERYWHERE) == []


def test_domain_entities_and_value_objects_are_not_pydantic_models() -> None:
    offending: list[str] = []
    for relative in ("entities", "value_objects"):
        for path in python_files(f"domain/{relative}"):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                base_names = {
                    base.id if isinstance(base, ast.Name) else getattr(base, "attr", "")
                    for base in node.bases
                }
                if "BaseModel" in base_names:
                    offending.append(f"{path.name}::{node.name}")
    assert offending == []


def test_use_cases_do_not_import_http_schemas() -> None:
    forbidden = {"identity_service.entrypoints"}
    assert violations(python_files("application/use_cases"), forbidden) == []

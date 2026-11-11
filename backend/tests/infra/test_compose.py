from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]


def _services(name: str) -> dict[str, Any]:
    data = yaml.safe_load((ROOT / name).read_text(encoding="utf-8"))
    services: dict[str, Any] = data["services"]
    return services


def test_published_ports_are_local_and_configurable() -> None:
    expected = {
        "frontend": "127.0.0.1:${FRONTEND_PORT:-5173}:5173",
        "backend": "127.0.0.1:${BACKEND_PORT:-8000}:8000",
        "qdrant": "127.0.0.1:${QDRANT_PORT:-6333}:6333",
    }
    services = _services("docker-compose.yml")
    published = {name: svc["ports"] for name, svc in services.items() if "ports" in svc}
    assert published == {name: [port] for name, port in expected.items()}


def test_cors_origin_and_api_url_follow_the_ports() -> None:
    services = _services("docker-compose.yml")
    backend_env = services["backend"]["environment"]
    assert backend_env["CORS_ORIGIN"] == "${CORS_ORIGIN:-http://localhost:${FRONTEND_PORT:-5173}}"
    build_args = services["frontend"]["build"]["args"]
    assert build_args["VITE_API_URL"] == "http://localhost:${BACKEND_PORT:-8000}"
    dev_env = _services("docker-compose.dev.yml")["frontend"]["environment"]
    assert dev_env["VITE_API_URL"] == "http://localhost:${BACKEND_PORT:-8000}"


def test_no_fixed_container_name() -> None:
    # Un nom fixe entrerait en conflit avec les conteneurs d'autres projets (« qdrant »...).
    for name in ("docker-compose.yml", "docker-compose.dev.yml"):
        for svc in _services(name).values():
            assert "container_name" not in svc


def test_env_example_documents_the_ports() -> None:
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    for var in ("FRONTEND_PORT=5173", "BACKEND_PORT=8000", "QDRANT_PORT=6333"):
        assert f"# {var}" in text


def test_env_example_documents_cors_origin() -> None:
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "# CORS_ORIGIN=http://localhost:5173" in text


def test_compose_passes_qdrant_dashboard_url() -> None:
    backend_env = _services("docker-compose.yml")["backend"]["environment"]
    assert (
        backend_env["QDRANT_DASHBOARD_URL"]
        == "${QDRANT_DASHBOARD_URL:-http://localhost:${QDRANT_PORT:-6333}/dashboard}"
    )

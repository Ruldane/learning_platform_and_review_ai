import re
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


def _deny_regex(command: list[str]) -> str:
    """Motif de `--chromium-deny-list` ; compose remplace `$$` par `$` (interpolation)."""
    (value,) = [arg.split("=", 1)[1] for arg in command if arg.startswith("--chromium-deny-list=")]
    # Gotenberg découpe la valeur sur les virgules (plusieurs motifs) : aucune virgule permise.
    assert "," not in value
    return value.replace("$$", "$")


_DENIED = [
    "http://backend:8000/api/v1/memory/items",
    "http://frontend:5173/",
    "http://qdrant:6333/",
    "http://ollama:11434/api/tags",
    "http://searxng:8080/search?q=x",
    "http://gotenberg:3000/forms/chromium/convert/url",
    "http://localhost/",
    "http://localhost:8000",
    "http://localhost./",
    "http://app.localhost/",
    "http://host.docker.internal:11434/",
    "http://printer.local/",
    "http://169.254.169.254/latest",
    "http://10.0.0.1/",
    "http://127.0.0.1:8000/",
    "http://127.1/",
    "http://0.0.0.0/",
    "http://0177.0.0.1/",
    "http://0x7f.0.0.1/",
    "http://2130706433/",
    "http://172.16.0.1/",
    "http://172.31.255.255/",
    "http://192.168.1.1/",
    "http://100.64.0.1/",
    "http://198.18.0.1/",
    "http://[::1]/",
    "http://[fd00::1]/",
    "http://[fe80::1]/",
    "http://[::ffff:127.0.0.1]/",
    "ws://backend:8000/ws",
    "file:///etc/passwd",
    "https://user@10.0.0.1/",
]

_ALLOWED = [
    "https://example.org/page",
    "https://www.wikipedia.org/wiki/Python",
    "https://10fastfingers.com/",
    "https://172.217.0.1/",
    "https://local.example.org/",
    "https://backend.example.org/",
    "https://github.com/org/repo?tab=readme",
    "https://8.8.8.8/",
]


def test_gotenberg_denies_internal_hosts() -> None:
    deny = _deny_regex(_services("docker-compose.yml")["gotenberg"]["command"])
    for url in _DENIED:
        assert re.search(deny, url), url
    for url in _ALLOWED:
        assert not re.search(deny, url), url


def test_gotenberg_also_checks_resolved_addresses() -> None:
    command = _services("docker-compose.yml")["gotenberg"]["command"]
    assert command[0] == "gotenberg"
    assert "--chromium-deny-private-ips=true" in command
    assert "--api-disable-download-from=true" in command

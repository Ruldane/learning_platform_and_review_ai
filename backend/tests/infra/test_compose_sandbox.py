"""Le service `sandbox` de Compose (10.A1) : chaque valeur d'isolation est figée par le plan
(phase 10, « Bac à sable »). Un changement ici est un changement de sécurité."""

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]


def _compose() -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    return data


def _sandbox() -> dict[str, Any]:
    sandbox: dict[str, Any] = _compose()["services"]["sandbox"]
    return sandbox


def test_sandbox_has_no_network_no_port_no_secret() -> None:
    svc = _sandbox()
    assert svc["network_mode"] == "none"
    for forbidden in ("ports", "env_file", "environment", "networks", "extra_hosts", "devices"):
        assert forbidden not in svc, forbidden
    assert svc["volumes"] == ["sandbox_spool:/spool"]  # aucun dossier de l'hôte, aucun socket
    assert "privileged" not in svc and "pid" not in svc and "ipc" not in svc


def test_sandbox_runs_as_root_without_capabilities_except_four() -> None:
    svc = _sandbox()
    assert svc["user"] == "0:12345"
    assert svc["cap_drop"] == ["ALL"]
    assert svc["cap_add"] == ["CHOWN", "SETUID", "SETGID", "KILL"]
    assert svc["security_opt"] == ["no-new-privileges:true"]
    assert not any("seccomp" in str(o) or "apparmor" in str(o) for o in svc["security_opt"])


def test_sandbox_filesystem_and_limits() -> None:
    svc = _sandbox()
    assert svc["read_only"] is True
    # Les valeurs du plan, plus `nr_inodes` (sans lui, une boucle de `open()` tue le conteneur).
    assert svc["tmpfs"] == [
        "/work:size=64m,noexec,nosuid,nodev,nr_inodes=4096",
        "/tmp:size=16m,noexec,nosuid,nodev,nr_inodes=2048",
        "/dev/shm:size=64m,noexec,nosuid,nodev,nr_inodes=2048",
    ]
    assert (svc["mem_limit"], svc["memswap_limit"]) == ("512m", "512m")
    assert (svc["cpus"], svc["pids_limit"]) == (1.0, 128)


def test_sandbox_healthcheck_reads_the_heartbeat_age() -> None:
    check = _sandbox()["healthcheck"]["test"]
    assert "/spool/heartbeat" in check[-1] and "< 5" in check[-1]


def test_backend_shares_the_spool_by_group_and_waits_for_the_sandbox() -> None:
    backend = _compose()["services"]["backend"]
    assert "sandbox_spool:/spool" in backend["volumes"]
    assert backend["group_add"] == ["12345"]
    assert backend["depends_on"]["sandbox"] == {"condition": "service_healthy"}
    assert "sandbox_spool" in _compose()["volumes"]


def test_dockerfile_copies_every_runner_module() -> None:
    dockerfile = (ROOT / "sandbox" / "Dockerfile").read_text(encoding="utf-8")
    (copy,) = [line for line in dockerfile.splitlines() if line.startswith("COPY ")]
    for module in (ROOT / "sandbox").glob("*.py"):
        assert module.name in copy, module.name
    assert "pytest==" in dockerfile and "python:3.12" in dockerfile

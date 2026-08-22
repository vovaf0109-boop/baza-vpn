import ast
import os
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_VERSIONS = PROJECT_ROOT / "alembic" / "versions"


def _revision_values(path: Path) -> tuple[str, str | None]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    revision: str | None = None
    down_revision: str | None = None
    for node in tree.body:
        if not isinstance(node, ast.AnnAssign):
            continue
        if not isinstance(node.target, ast.Name):
            continue
        if node.target.id not in {"revision", "down_revision"}:
            continue
        value = ast.literal_eval(node.value)
        if node.target.id == "revision":
            revision = value
        else:
            down_revision = value

    assert revision is not None, f"revision is missing in {path}"
    return revision, down_revision


def test_alembic_revision_ids_fit_default_version_table() -> None:
    for path in ALEMBIC_VERSIONS.glob("*.py"):
        revision, down_revision = _revision_values(path)
        assert len(revision) <= 32, f"{path.name} revision is too long"
        if down_revision is not None:
            assert len(down_revision) <= 32, f"{path.name} down_revision is too long"


def test_alembic_chain_is_linear_and_uses_short_status_revision() -> None:
    revisions = {
        revision: down_revision
        for revision, down_revision in (
            _revision_values(path) for path in ALEMBIC_VERSIONS.glob("*.py")
        )
    }

    old_too_long_revision = "0003_" + "add_status_check_constraints"
    assert old_too_long_revision not in revisions
    assert revisions == {
        "0001_initial": None,
        "0002_add_user_updated_at": "0001_initial",
        "0003_status_checks": "0002_add_user_updated_at",
    }


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _docker_available() -> bool:
    result = subprocess.run(
        ["docker", "version"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


@pytest.mark.integration
def test_full_migration_chain_applies_to_postgresql16() -> None:
    if not _docker_available():
        pytest.skip("Docker is not available")

    container = f"baza-pg-migration-{uuid.uuid4().hex[:12]}"
    port = _free_port()
    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            container,
            "-e",
            "POSTGRES_USER=baza",
            "-e",
            "POSTGRES_PASSWORD=postgres",
            "-e",
            "POSTGRES_DB=baza",
            "-p",
            f"127.0.0.1:{port}:5432",
            "postgres:16-alpine",
        ],
        cwd=PROJECT_ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            ready = subprocess.run(
                ["docker", "exec", container, "pg_isready", "-U", "baza", "-d", "baza"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if ready.returncode == 0:
                break
            time.sleep(1)
        else:
            pytest.fail("PostgreSQL 16 container did not become ready")

        env = os.environ.copy()
        env.update(
            {
                "APP_ENV": "test",
                "BOT_TOKEN": "",
                "DATABASE_URL": f"postgresql+asyncpg://baza:postgres@127.0.0.1:{port}/baza",
                "REDIS_URL": "",
                "SECRET_KEY": "test-secret-key",
                "SUPPORT_USERNAME": "baza_support",
                "SUBSCRIPTION_BASE_URL": "https://sub.example.com",
            }
        )
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=PROJECT_ROOT,
            env=env,
            check=True,
            timeout=60,
        )

        version = subprocess.run(
            [
                "docker",
                "exec",
                container,
                "psql",
                "-U",
                "baza",
                "-d",
                "baza",
                "-tAc",
                "SELECT version_num FROM alembic_version",
            ],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout.strip()
        assert version == "0003_status_checks"

        constraint = subprocess.run(
            [
                "docker",
                "exec",
                container,
                "psql",
                "-U",
                "baza",
                "-d",
                "baza",
                "-tAc",
                "SELECT conname FROM pg_constraint WHERE conname = 'ck_users_status'",
            ],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout.strip()
        assert constraint == "ck_users_status"
    finally:
        subprocess.run(
            ["docker", "rm", "-f", container],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

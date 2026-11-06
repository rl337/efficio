"""Exercise check dispatch without requiring Docker or CAD dependencies."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def make_checkout(tmp_path: Path) -> Path:
    shutil.copy(ROOT / "run_checks.sh", tmp_path / "run_checks.sh")
    (tmp_path / "efficio").mkdir()
    return tmp_path


def fake_runner(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "with open(os.environ['CALL_LOG'], 'a') as log:\n"
        "    log.write(json.dumps(sys.argv[1:]) + '\\n')\n"
        "if '-c' in sys.argv:\n"
        "    sys.exit(1)  # optional plugins are absent\n"
        "sys.exit(1 if os.environ.get('FAIL_TOOL') in sys.argv[1:] else 0)\n"
    )
    path.chmod(0o755)


def run_checks(
    root: Path, mode: str, fail: str = ""
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.update(
        EFFICIO_CHECK_ENV=mode,
        CALL_LOG=str(root / "calls.jsonl"),
        FAIL_TOOL=fail,
        PATH=f"{root / 'bin'}:{env['PATH']}",
    )
    # Deliberately call from outside the project to test path resolution.
    return subprocess.run(
        ["bash", str(root / "run_checks.sh")],
        cwd=root.parent,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("mode", ["venv", "auto"])
def test_checks_use_project_venv(tmp_path: Path, mode: str) -> None:
    root = make_checkout(tmp_path)
    fake_runner(root / ".venv/bin/python")
    result = run_checks(root, mode)
    assert result.returncode == 0, result.stdout + result.stderr
    calls = [
        json.loads(line) for line in (root / "calls.jsonl").read_text().splitlines()
    ]
    assert [call[1] for call in calls if call[0] == "-m"] == [
        "mypy",
        "black",
        "isort",
        "pytest",
    ]
    assert "coverage not measured" in result.stdout
    assert (root / "test-results").is_dir()


def test_checks_keep_docker_poetry_path(tmp_path: Path) -> None:
    root = make_checkout(tmp_path)
    fake_runner(root / "bin/poetry")
    fake_runner(root / ".venv/bin/python")
    result = run_checks(root, "docker")
    assert result.returncode == 0, result.stdout + result.stderr
    calls = [
        json.loads(line) for line in (root / "calls.jsonl").read_text().splitlines()
    ]
    assert calls[0] == ["run", "mypy", "."]
    assert all(call[0] == "run" for call in calls)


def test_checks_stop_on_failure(tmp_path: Path) -> None:
    root = make_checkout(tmp_path)
    fake_runner(root / ".venv/bin/python")
    result = run_checks(root, "venv", fail="mypy")
    assert result.returncode == 1
    assert "MyPy type checking failed" in result.stdout
    assert "Running Black" not in result.stdout


@pytest.mark.parametrize("mode", ["venv", "unsupported"])
def test_checks_reject_missing_or_invalid_environment(
    tmp_path: Path, mode: str
) -> None:
    root = make_checkout(tmp_path)
    result = run_checks(root, mode)
    assert result.returncode == 1
    assert "Running MyPy" not in result.stdout

#!/usr/bin/env bash
# Install the checked-in lock without installing tools into the host Python.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
python_bin="${PYTHON:-python3.12}"
"$python_bin" -c 'import sys; assert sys.version_info[:2] == (3, 12), "Use Python 3.12 (matching Docker)"'
if [ ! -x .venv/bin/python ]; then
    "$python_bin" -m venv .venv
fi
.venv/bin/python -c 'import sys; assert sys.version_info[:2] == (3, 12), "Existing .venv must use Python 3.12"'

# Poetry has its own temporary environment so its dependencies cannot alter the
# project's lock. Pin the version that generated the current poetry.lock.
tool_dir="$(mktemp -d)"
trap 'rm -rf "$tool_dir"' EXIT
"$python_bin" -m venv "$tool_dir/poetry"
"$tool_dir/poetry/bin/python" -m pip install --disable-pip-version-check 'poetry==2.0.1'
export POETRY_CACHE_DIR="${POETRY_CACHE_DIR:-$tool_dir/cache}"
export POETRY_CONFIG_DIR="${POETRY_CONFIG_DIR:-$tool_dir/config}"
export VIRTUAL_ENV="$PWD/.venv"
export PATH="$VIRTUAL_ENV/bin:$PATH"
"$tool_dir/poetry/bin/poetry" check --lock
"$tool_dir/poetry/bin/poetry" install --with dev --no-interaction

# Exercise both CAD and Cairo-backed export dependencies, not just pip imports.
.venv/bin/python - <<'PY'
import cadquery as cq
from reportlab.graphics import renderPM
from reportlab.graphics.shapes import Drawing, Rect

assert cq.Workplane("XY").box(1, 1, 1).val().isValid()
drawing = Drawing(10, 10)
drawing.add(Rect(0, 0, 10, 10))
assert renderPM.drawToString(drawing, fmt="PNG").startswith(b"\x89PNG")
print("CAD and PNG smoke checks passed.")
PY
printf '\nReady: EFFICIO_CHECK_ENV=venv ./run_checks.sh\n'

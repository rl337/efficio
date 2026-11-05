"""Turn a pytest JUnit report into Markdown for the GitHub job summary.

Usage: python3 junit_summary.py test-results/junit.xml >> "$GITHUB_STEP_SUMMARY"

Standard library only, so it runs on the bare Actions runner.
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List


def summarise(path: Path) -> str:
    if not path.exists():
        return (
            "## Tests\n\n"
            "No test report was produced: the checks stopped before pytest "
            "(see the mypy / black / isort output in the log).\n"
        )
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    total = failures = errors = skipped = 0
    seconds = 0.0
    failed: List[str] = []
    for suite in suites:
        total += int(suite.get("tests", 0))
        failures += int(suite.get("failures", 0))
        errors += int(suite.get("errors", 0))
        skipped += int(suite.get("skipped", 0))
        seconds += float(suite.get("time", 0.0))
        for case in suite.iter("testcase"):
            problem = case.find("failure")
            if problem is None:
                problem = case.find("error")
            if problem is not None:
                name = f"{case.get('classname', '')}::{case.get('name', '')}"
                message = (problem.get("message") or "").splitlines()
                failed.append(f"- `{name}`: {message[0] if message else ''}")
    passed = total - failures - errors - skipped
    status = "✅ passed" if not (failures or errors) else "❌ failed"
    lines = [
        f"## Tests {status}",
        "",
        "| Passed | Failed | Errors | Skipped | Total | Time |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
        f"| {passed} | {failures} | {errors} | {skipped} | {total} | {seconds:.0f} s |",
    ]
    if failed:
        lines += ["", "### Failures", *failed]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.stdout.write(summarise(Path(sys.argv[1] if len(sys.argv) > 1 else "")))

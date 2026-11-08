# Project Instruction

## Development environment

Use an isolated development environment: either the existing Docker image or
Python 3.12 in the repository-local `.venv`. Docker remains the CI environment;
the virtual environment is a supported alternative for internal agent work on
VMs without Docker. Do not install project packages into the host/global Python.

- Docker: `docker build -t efficio .`, then
  `docker run --rm -v "$(pwd):/app" efficio /app/run_checks.sh`.
- Virtual environment: `./scripts/setup_venv.sh`, then
  `EFFICIO_CHECK_ENV=venv ./run_checks.sh`. Use `.venv/bin/python` for other
  development commands, or activate `.venv/bin/activate` first.
- Both paths install from `poetry.lock`. Do not regenerate the lock just to set up
  an environment. See README.md for native libraries and troubleshooting.
- Shell/Git inspection and environment bootstrap can run on the host. Tests,
  validation, CAD scripts and dependency installs must use one of the isolated
  environments above. Bootstrap may install Poetry in a temporary tool venv.
- A venv isolates Python packages, not OS libraries. Report missing native
  dependencies or unavailable package downloads instead of claiming validation
  passed. Do not silently change dependencies to work around a setup failure.

## Object Definitions

All efficio objects must follow the `parameterized-objects` skill (`.claude/skills/parameterized-objects/SKILL.md`):
- define objects by their parameters, in a submodule categorized by what they are;
- fix values only where a standard defines them (e.g. an M3 bolt fixes thread and head but not length);
- create fully concrete parts (e.g. an M3 x 10 bolt) only at the use site that needs them.

## Testing and Coverage

When adding or removing code it is essential that every functional edit to the codebase have corresponding tests. These tests, when possible should use the testing frameworks of the platform, for example in python it should be pytest.  

## Validation Script

There should be a run_checks.sh that runs all automated tests, static checks, style linting, test coverage or automation that run in the github actions.  If the repository contains multiple languages or platforms ALL of their checks must be run from this validation script.

## Validation of PRs
There should be at least 1 github action designed to validate Pull Requests which run a relevant subset of 
checks found in run_checks.sh.  Ideally it will be all but there may be checks that cannot run headlessly or in a github actions context.  

# Task Instruction
All work and changes to the repository should be part of a task.  A task has a distinct starting point and measurable end goal.  If you feel like you are not presently in a task, ask for more detailed instructions or clarity on any underdeveloped parts of the problem.  Once the problem is well understood and appropriately broken down it will be tracked in a Github Issue.

When Starting a distinct task that has a clear starting point and end goal, create an Issue in the github issue tracker via the github MCP (configured via Cursor MCPs) and start a branch named after a 5 digit issue's ID left padded with 0s and suffixed with a snake case identifier transformation of the issue title.  You should check into this branch often and check github action statuses on your checkins fixing any problems that arise with them.  When the task is complete, create a PR against main for me to review and merge.

Issue tracking should take the place of status markdowns in the repository.

# Automatic Task Instructions
Once a task is started and a Github Issue is created the following steps in the task should be performed
## Starting Steps
1. Create branch as described in Task Instruction
2. Evaluate existing checks in run_checks.sh and augment them as well as checks in github actions, updating them when they are out of date or superceded by other methodology.
3. If checks introduced in step 2 of starting steps fail, those failures become part of the scope of this task.
## Closing Steps
1. Verify changes are logically complete and consistent with the overall style of the project
2. Run all checks defined in the run_checks.sh
3. Clean up any artifacts that might have been created during development of the task.  Add relevant entries to .gitignore. Fix problems found with step 2.  If there were problems fixed, return to step 1.  
4. Check in all relevant changes and new files into the branch.  Push changes to to remote.
5. **Create a pull request against main that references the GitHub issue using "Closes #<issue_number>" in the PR title or description.**
6. Wait for verification github action to complete.  If the action fails, analyze failure treating that failure like a local test failure and return to step 3.
7. When previous closing steps are complete, update the GitHub issue with what was accomplished.


## Material-aware finished walls

For new or revised load-bearing housings and tooling, declare material, process,
service assumptions and a minimum finished-wall budget. Use a project-specific
`WallPolicy` where applicable; validate named critical features after holes,
recesses and bevels. Record exemptions and unmeasured regions. Keep shrinkage and
machining allowances separate from finished-wall limits, and leave unsupported
material/process profiles unqualified. A geometry pass is not structural or
manufacturing certification. See `docs/wall-policy.md` for the initial pump case.

# Club Chairman

A football owner-chairman simulation built with Python and Pygame.

## Current status

Development setup only. The repository contains coding-agent instructions, pinned graphics dependencies, an environment diagnostic and automated Linux/Windows checks. There is no playable game yet. Foundation remains incomplete.

## Setup

Use Python 3.12 and run these commands from the repository root:

```sh
python -m venv .venv
```

On Windows:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe tools\check_environment.py
```

On Linux or macOS:

```sh
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python tools/check_environment.py
```

For a server without a display, add `--headless` to the check command. The diagnostic creates a temporary SQLite database, checks write/read integrity, renders text and processes an event, then exits. It does not implement or test game saves. Audio and physical input are not checked.

Windows users with Python 3.12 and the Python launcher installed can also run `setup_windows.cmd`. This convenience script creates the environment, installs dependencies and runs the diagnostic. It is not a game launcher.

## Working on the project

Read [AGENTS.md](AGENTS.md) and [the development checkpoint](docs/DEVELOPMENT_CHECKPOINT.md) before making changes. Consult the current living GDD for relevant design requirements; it is not included in this repository yet. Do not infer gameplay rules from this README or create a competing design document.

The technical baseline uses Python 3.12 and Pygame 2.6.1. SQLite, JSON, logging and unittest are available in the Python standard library. No supporting UI framework or packaging tool has been selected yet. Windows is the intended initial game platform; Linux CI is an engineering check, not a commitment to release on Linux.

Development checks run on pull requests and on pushes to main. They verify installation, dependency consistency, graphics initialization, event handling and basic database operations. Passing them does not constitute a playable milestone or packaged Windows validation.

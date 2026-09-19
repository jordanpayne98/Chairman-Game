# Club Chairman — Executive Update (0.2)

A playable early Python/Pygame football chairman simulation. Take charge of Northbridge Athletic through a complete 14-match season in an eight-club fictional league.

## Play on Windows

Download **ClubChairman-Windows-preview** from the successful GitHub Actions run linked in the implementation pull request. Extract the entire ZIP into a folder, then open **ClubChairman.exe**. Keep the `_internal` folder beside the executable. Python installation is not required for the packaged build.

1. Choose New career and appoint a manager in Staff.
2. Filter and sort free agents in Recruitment. Save a shortlist, add private notes and pin up to four candidates to compare. Scout them before committing; reports use uncertain ranges.
3. Review Finances > Forecast for the next 28 days, or Plan for the combined impact of pinned free agents. Plans change neither time nor funds; signings need individual confirmation. Review the wage limit and ticket price here too.
4. Continue one day or advance to the next fixture. Required chairman decisions interrupt time.
5. Watch text matches at 1x/2x/4x or skip. Your manager selects the team. Encourage them or request more attacking football; they can refuse.
6. Complete all fourteen fixtures and review the final table, prize money and cash ledger. Open completed fixtures in League to revisit commentary, possession and lineups.

Save manually at any time, including mid-match. Autosaves follow management actions and full time. Load / recover career lists manual slots, three rotating autosaves and backups; a loaded career starts a separate save timeline so existing files are preserved. Windows saves live under `%LOCALAPPDATA%\ClubChairman\saves`. The application writes saves outside the game installation folder.

The update reads **existing 0.1 / schema 1 saves** and upgrades them in memory. Original files remain unchanged on load; new saves use schema 2. The older executable cannot read these new saves. Shortlists, pins, notes and read markers travel with the career; interface preferences are stored separately.

Tab and Shift+Tab move focus; Enter activates the focused control. Ctrl+S saves, Ctrl+F searches players, Alt+Left/Right moves through navigation history, Space pauses live matches and F1 opens Help. Escape cancels an overlay or goes back. In the note editor, Enter does not submit while typing; Tab reaches Save note and Discard. Back/Forward and profile Previous/Next preserve filters, sorting and pagination. The sidebar collapses and the window scales with letterboxing.

## New in 0.2

- Executive dashboard with cash projection, wage headroom, recent form and unread updates.
- Role/name/shortlist filtering; stable sorting by name, age, wage or scouted range midpoint. Unknown ratings remain unknown and sort last.
- Saved shortlist, private notes, four-player comparison and reversible list/pin changes. Signed players stay pinned and are excluded from prospective signing costs.
- A 28-day cash forecast and a pinned-signings scenario with immediate fees, future wages, budget impact and combined affordability checks. Gate receipts hold today's supporter mood and ticket price; the shaded ±15% attendance sensitivity is not a probability interval. Forecasts exclude prizes and unapproved future spending and show unpaid accruals separately.
- Archived match reports, lineups, possession and key-event filtering.
- Unread Inbox counts separate from required decisions; session Activity history; keyboard shortcuts; stale and duplicate confirmation guards.
- Configured scouting prices, delivery times and career calendar dates shown consistently.

## What works

- New seeded career, eight clubs, 156 players and a home/away fixture list.
- Three manager candidates; manager-controlled lineup selection and tactical risk.
- Paid scouting with delayed uncertain reports; cash- and wage-validated free-agent signings.
- Wage budgets, home ticket demand, owner equity injections, payroll, sponsorship, ledger and league prizes.
- Chairman spending decisions and a manager response to bench messages.
- Connected match simulation, commentary, statistics, league standings and season completion.
- Versioned atomic SQLite saves, integrity checks, backups and recoverable timelines.

## Preview boundaries

This is an early playable version, not the finished AA game. It supports one existing club and one season. Career creation/acquisition choices, full 37-attribute profiles, potential/development, full contract negotiations, staff replacement, broader delegation, academies, injuries, cards, substitutions, cups, promotion/relegation, later seasons, multi-club ownership, stadium projects, outside investments and succession are not implemented yet. Match simulation is a simplified possession/chance model, not the complete GDD match engine. There is no sound or authored club artwork yet. This update implements part of the approved QoL scope: named multiple shortlists, saved named financial scenarios, side-panel profiles, adjustable columns, global search, shortcut remapping and enlarged text are still pending.

All amounts, player distributions and the preview league are provisional implementation fixtures for playtesting. They do not replace the approved full-game design. The current living GDD revision 0.3 remains authoritative and is not duplicated in this repository. See [AGENTS.md](AGENTS.md) and [the development checkpoint](docs/DEVELOPMENT_CHECKPOINT.md).

## Run from source

Use Python 3.12:

```sh
python -m venv .venv
```

On Windows:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m club_chairman
```

On Linux:

```sh
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m club_chairman
```

Checks:

```sh
python -m unittest discover -s tests -v
python -m club_chairman --self-test
python -m club_chairman --smoke
```

Run these using the virtual environment's Python. The smoke display uses SDL's dummy driver; it does not prove physical input, audio, accessibility or performance on every PC. GitHub Actions runs Linux and Windows tests, builds with PyInstaller, then runs both career and display checks against the Windows executable. Build artifacts expire after 30 days and can be regenerated from source.

Licensing dependencies are documented in [THIRD_PARTY.md](docs/THIRD_PARTY.md).

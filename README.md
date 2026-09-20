# Club Chairman — Contracts Update (0.4)

A playable early Python/Pygame football chairman simulation. Take charge of Northbridge Athletic through continuing 14-match seasons in an eight-club fictional development league. This is a playable development version; the approved full AA game is still being built.

## Play on Windows

Download **ClubChairman-Windows-preview** from the successful GitHub Actions run linked in the implementation pull request. Extract the entire ZIP into a folder, then open **ClubChairman.exe**. Keep the `_internal` folder beside the executable. Python installation is not required for the packaged build.

1. Choose New career and appoint a manager in Staff.
2. Filter and sort free agents in Recruitment. Save a shortlist, add private notes and pin up to four candidates to compare. Scout them before committing; reports use uncertain ranges.
3. Review Finances > Forecast for the next 28 days, or Plan for the combined impact of pinned free agents. Plans change neither time nor funds; signings need individual confirmation. Review the wage limit and ticket price here too.
4. Continue one day or advance to the next fixture. Required chairman decisions interrupt time.
5. Watch text matches at 1x/2x/4x or skip. Your manager selects the team. Encourage them or request more attacking football; they can refuse.
6. Review player and manager contract expiries, then use Career > Prepare next season after closing the final match. Wages and deadlines continue through the two-week preseason. Previous tables and matches remain in Career history.

Save manually at any time, including mid-match. Autosaves follow management actions and full time. Load / recover career lists manual slots, three rotating autosaves and backups; a loaded career starts a separate save timeline so existing files are preserved. Windows saves live under `%LOCALAPPDATA%\ClubChairman\saves`. The application writes saves outside the game installation folder.

The update reads **existing 0.1 and 0.2 / schema 1 and 2 saves** and upgrades them in memory. Original files remain unchanged on load; new saves use schema 3. Older executables cannot read these new saves. Existing contracts retain their original expiry dates; renew before advancing beyond them. New careers start with longer contracts to introduce the continuing-season loop. Shortlists, pins, notes and read markers travel with the career; interface preferences are stored separately.

Tab and Shift+Tab move focus; Enter activates the focused control. Ctrl+S saves, Ctrl+F searches players, Alt+Left/Right moves through navigation history, Space pauses live matches and F1 opens Help. Escape cancels an overlay or goes back. In the note editor, Enter does not submit while typing; Tab reaches Save note and Discard. Back/Forward and profile Previous/Next preserve filters, sorting and pagination. The sidebar collapses and the window scales with letterboxing.

## New in 0.4

- One senior-player signing workflow: enquiry, agent terms, conditional acceptance, medical and final registration. The instant-signing bypass is removed; existing signed contracts are unchanged.
- Contract progress strip, editable Terms, Cash review and paginated Conversation tabs. Counteroffer changes, deadlines, competing reservations and renewal exposure are visible before approval.
- Combined recruitment plans use the latest agent terms and count a selected offer's reservation only once. Plans explicitly assume completion today; they do not automatically reserve or sign anything.
- Next fixture stops for new medical results and imminent offer deadlines. An existing urgent review requires an explicit confirmation before fast-forward. The overview links to the earliest urgent contract.
- Reopening a closed discussion retains its transcript and outcome in Contracts > History. Older saves have no invented past history; records accumulate from this update onward.
- Late medicals that cannot finish before registration closes are rejected without reserving capacity. Completion rechecks manager availability, cash and wages.

Saves remain schema 3, with optional retained offer history. Existing schema 1–3 careers load without altering the source file or existing employment. This completes a focused recruitment workflow, not the entire GDD contract catalogue or AA release.

## Included from 0.3

- Continuing compact seasons with unique fixture identities, separate prize settlements, preseason and retained tables/match reports.
- Contracts desk: editable saved proposals, agent counteroffers, expiry/cooldown, cash/payroll reservations, medical review and final atomic registration. Renewals of existing employment have an immediate medical review. Proposed deals alone do not stop employment expiring.
- Manager renewal and replacement with explicit notice/severance and incoming salary/signing costs.
- Annual academy trials, persistent youth identities, individual admissions and wages, promotion from age 16 and periodic coaching/development estimates.
- Training, academy and stand proposals; fixed-price construction; temporary seat closures; operational capacity and weekly running-cost changes.
- Original crests, stable illustrated portraits and stadium diagram, goal emphasis, construction animation and optional short sound cues. Settings includes reduced motion and sound controls.
- Contextual hover explanations and keyboard F2 help; financial assumptions available through Why this forecast?; cached presentation snapshots for the expanded screens.
- Correct forecast settlement during a paused final away match and a verified migration from an actual 0.2 mid-match save.

Full transfers, loans, clauses and delegation remain on the release checklist. Senior-player free-agent signings and renewals now share the reviewed contract workflow.

## Included from 0.2

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

This is an early playable version, not the finished AA game. The eight-club compact calendar remains development content. Full 14-nation world content, career creation/acquisitions, owner succession, multi-club groups, full attributes/potential, all staff roles/delegation, club transfers/loans/clauses, full football rules, promotion/cups, commercial systems, AI finances, detailed assets and the remaining accessibility/QoL requirements are still pending. The new career systems are connected playable implementations of a subset of their approved scope.

See [release readiness](docs/RELEASE_READINESS.md) for the complete retained scope and [the asset register](docs/ASSET_REGISTER.md) for artwork/audio provenance. No full AA release gate is claimed complete.

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

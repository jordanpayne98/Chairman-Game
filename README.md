# Club Chairman — Transfer and Commercial Update (0.5)

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

The update reads **existing 0.1–0.4 / schema 1–3 saves** and upgrades them in memory. Original files remain unchanged on load; new saves use schema 4. Older executables cannot read these new saves. Existing contracts retain their original expiry dates; renew before advancing beyond them. New careers start with longer contracts to introduce the continuing-season loop. Shortlists, pins, notes and read markers travel with the career; interface preferences are stored separately.

Tab and Shift+Tab move focus; Enter activates the focused control. Ctrl+S saves, Ctrl+F searches players, Alt+Left/Right moves through navigation history, Space pauses live matches and F1 opens Help. Escape cancels an overlay or goes back. In the note editor, Enter does not submit while typing; Tab reaches Save note and Discard. Back/Forward and profile Previous/Next preserve filters, sorting and pagination. The sidebar collapses and the window scales with letterboxing.

## New in 0.5

- Recruitment includes contracted players, with retained market filters, scouting, notes, shortlists and authorised comparisons. True abilities remain hidden.
- Transfers desk: negotiate a selling-club fee, immediate percentage and deferred date, then complete personal terms and medical through Contracts. Club and player consent must both be valid; cash, registration and future obligations commit together.
- Player sales: select a receiving club, obtain a persisted quote, complete consent/medical checks and confirm registration. Both clubs record the same cash transfer; insufficient counterparty funds or inadequate remaining squad cover blocks completion.
- Incoming and outgoing senior loans: borrower wage shares from 50–100%, consent, medical and final review, preserved original employment, automatic return and window-limited recall. Early recall refunds the unserved fee proportion, shown before approval. Current UI uses a 56-day quote; shorter employment shortens it. The command model supports 14–84 days.
- Dated transfer obligations survive season changes and are paid exactly once. Transfers > Payments lists them. Loans > Review recall shows refunds and returning wage responsibility.
- Commercial: training, digital and stadium rights; editable income/duration proposals, counteroffers, exclusivity validation, weekly settlements, expiry and naming-rights supporter effects. Active naming rights appear on the ground screen. The legacy core sponsorship remains separate.
- Forecasts include signed sponsorship schedules, deferred transfer payments and loan wage returns. Proposed acquisitions remain explicitly hypothetical; draft and competing reservations are separated.
- Counterparty club cash ledgers, daily wage accrual, provisional weekly operating income and retained unpaid accrual support these transactions. This is a limited counterparty model, not completed AI financial management.

Existing careers migrate to schema 4 in memory, without rewriting the source save or changing existing employment/match RNG. New files cannot be opened by old executables. No lost historical club financial records are invented: counterparty accounts begin at upgrade with explicit provisional opening balances.

## Included from 0.4

- One senior-player signing workflow: enquiry, agent terms, conditional acceptance, medical and final registration. The instant-signing bypass is removed; existing signed contracts are unchanged.
- Contract progress strip, editable Terms, Cash review and paginated Conversation tabs. Counteroffer changes, deadlines, competing reservations and renewal exposure are visible before approval.
- Combined recruitment plans use the latest agent terms and count a selected offer's reservation only once. Plans explicitly assume completion today; they do not automatically reserve or sign anything.
- Next fixture stops for new medical results and imminent offer deadlines. An existing urgent review requires an explicit confirmation before fast-forward. The overview links to the earliest urgent contract.
- Reopening a closed discussion retains its transcript and outcome in Contracts > History. Older saves have no invented past history; records accumulate from this update onward.
- Late medicals that cannot finish before registration closes are rejected without reserving capacity. Completion rechecks manager availability, cash and wages.

The 0.4 release used schema 3 with retained offer history; 0.5 carries those records into schema 4 without altering source saves or existing employment. This completes a focused recruitment workflow, not the entire GDD contract catalogue or AA release.

## Included from 0.3

- Continuing compact seasons with unique fixture identities, separate prize settlements, preseason and retained tables/match reports.
- Contracts desk: editable saved proposals, agent counteroffers, expiry/cooldown, cash/payroll reservations, medical review and final atomic registration. Renewals of existing employment have an immediate medical review. Proposed deals alone do not stop employment expiring.
- Manager renewal and replacement with explicit notice/severance and incoming salary/signing costs.
- Annual academy trials, persistent youth identities, individual admissions and wages, promotion from age 16 and periodic coaching/development estimates.
- Training, academy and stand proposals; fixed-price construction; temporary seat closures; operational capacity and weekly running-cost changes.
- Original crests, stable illustrated portraits and stadium diagram, goal emphasis, construction animation and optional short sound cues. Settings includes reduced motion and sound controls.
- Contextual hover explanations and keyboard F2 help; financial assumptions available through Why this forecast?; cached presentation snapshots for the expanded screens.
- Correct forecast settlement during a paused final away match and a verified migration from an actual 0.2 mid-match save.

Full clause coverage, advanced loan restrictions and delegation remain on the release checklist. Senior-player free-agent signings and renewals now share the reviewed contract workflow.

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

This is an early playable version, not the finished AA game. The eight-club compact calendar remains development content. Full 14-nation world content, career creation/acquisitions, owner succession, multi-club groups, full attributes/potential, all staff roles/delegation, full transfer/loan clauses and rules, full football rules, promotion/cups, complete commercial demand and rights obligations, autonomous AI finances, detailed assets and the remaining accessibility/QoL requirements are still pending. The new career systems are connected playable implementations of a subset of their approved scope.

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

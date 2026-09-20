# Club Chairman — Figma UI Update (0.9)

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

The update reads **existing 0.1–0.8 / schema 1–7 saves** and upgrades them in memory. Original files remain unchanged on load; new saves use schema 7. An old in-progress match and its remaining matchday fixtures finish with the original engine, preserving the outcome and payments. Later fixtures use the new football engine. Existing reports retain their original evidence; missing attributes stay unknown until reassessed. Older executables cannot read new saves. Existing contracts retain their expiry dates; renew before advancing beyond them. Shortlists, pins, notes and read markers travel with the career; interface preferences are stored separately.

Tab and Shift+Tab move focus; Enter activates the focused control. Ctrl+S saves, Ctrl+F searches players, Alt+Left/Right moves through navigation history, Space pauses live matches and F1 opens Help. Escape cancels an overlay or goes back. In the note editor, Enter does not submit while typing; Tab reaches Save note and Discard. Back/Forward and profile Previous/Next preserve filters, sorting and pagination. The sidebar collapses and the window scales with letterboxing.

Ctrl+K opens global search for known players, clubs, departments and help topics. Settings > Interface size cycles through 100/125/150/175% zoom. Mouse wheel pans vertically at larger sizes; Shift+wheel pans horizontally, and keyboard focus follows controls into view. Ctrl+0 restores 100%. This is whole-interface zoom; full responsive text reflow is still pending.

## New in 0.9

The approved Figma Executive interface is now rendered by the actual Pygame game. Shared charcoal/sage tokens, bundled IBM Plex Sans/Lora fonts, exported navigation icons and the Northbridge crest work offline. The application stays in Python/Pygame.

- Grouped, collapsible navigation and a persistent top bar retain live club/date/decision context, search, saving and Continue. Stadium maps to the existing Facilities system; Competitions maps to League; History & career maps to Career. Responsibilities opens the working staff authority screen.
- The overview shows real cash, budget usage, standings, supporter mood, urgent reviews, fixtures, dated cash forecasts and project status. Sample figures and clubs from the design are not simulation data.
- The split inbox separates unread news from unresolved decisions, keeps message selection, paginates long reports and opens the existing validated approve/decline actions. Reading never approves a decision.
- Player profiles add estimate/confidence cards, grouped attribute rows and an evidence panel. Unknown attributes remain unknown, all 37 attributes stay available, and negotiation, scouting, development, notes and comparison remain connected.
- Squad/recruitment tables, department panels, tooltips, reviews, settings and save recovery share the new components. Long reviews paginate without hiding their controls. Fixtures provides a full paginated season list and opens saved match reports.
- The main menu can continue the latest valid save, resume an active career, open all checkpoints and change presentation settings before starting a career. Original save files are preserved by the existing recovery-timeline workflow.

No simulation rules or save schema changed. The internal canvas remains 1440 × 900, scaled to the window, with the existing 100–175% zoom and focus following. Full responsive reflow, arbitrary dashboard arrangement, single-click person drawers, content management, career-creation choices and multi-club/wealth systems are still open. The full 30-frame Figma prototype is not claimed to be implemented gameplay. See [Figma implementation coverage](docs/FIGMA_UI_IMPLEMENTATION.md).

## Included from 0.8

- Staff > People adds nine departmental roles, assessed capability ranges, shortlists, next-day interviews, salary counters, contract duration, protected approval terms, dated appointments, renewals and notice payments. Recruiting from another club pays compensation and respects a joining delay. Pending salary counts against your wage limit and dated forecast.
- Staff > Responsibilities lets you assign available staff, review coverage and apply Hands-on, Balanced or Executive presets. Each department has approval mode, maximum contract duration and a rolling commitment limit; a shared club limit prevents splitting expenditure between departments. Vacancies remain with the owner and your manager still controls match selection and tactics.
- Delegates can scout, negotiate basic player contracts, maintain training/recovery, admit academy players, negotiate sponsorship, review facilities and handle scheduled club decisions. Future guaranteed wages and project upkeep count toward authority. Cash, consent, medical and registration rules still apply. Bonuses and player options require the normal owner-led Contracts workflow.
- Staff > Approvals presents exceptions for an explicit, single-use decision. Changed authority or terms invalidate old approvals. Reports explain completed actions, and a monthly digest reconciles decisions and commitments. Staff departure reclaims authority and cancels unsigned delegated work while signed obligations remain binding.
- Rival clubs review observed player ability, squad needs, staff vacancies, expiring contracts, wage capacity, pending commitments, dated bills and a cash reserve. Transfers pass conditional agreement and medical stages before payment and registration. League activity shows completed public moves, keeping rival targets and assessments private.
- Fixes from the 0.7 review: weekly sponsorship arrives before same-day transfer bills, outgoing enquiries check the receiving club's registration capacity, and external availability no longer reveals hidden fitness.

To try delegation: appoint a manager, then contact and interview candidates under Staff > People. Sign affordable appointments and advance to their joining dates. In Responsibilities, choose **Review coverage** and review a preset. One employee can cover up to four departments; three employees can cover all nine. Balanced asks you to approve actions; Executive authorises actions within your chosen limits. Watch Approvals and Reports while advancing the career. The original manager hiring workflow remains on Staff > Manager.

## Included from 0.7

- Player profiles show the approved 37 football attributes in Technical, Mental, Physical and Goalkeeping groups, with uncertain position-weighted overall and potential estimates. Stored scouting evidence ages; hidden values are excluded from the interface and search.
- Development plans connect training focus and load to weekly growth, playing time, fatigue, recovery and quarterly potential reviews. Potential is sampled once and saved. Condition, medical estimates and availability help explain squad selection.
- Squad > Registration provides a reviewed competition list with senior, under-21 and non-homegrown allowances. Contract and loan completion check reserved list capacity. Injury, suspension, age, registration and loan-against-parent restrictions apply to selection.
- The new saved possession engine includes manager substitutions, yellow/second-yellow/red cards, future suspensions, dated injuries, added time and tactical responses. Action attributes, condition, fatigue and numerical advantage affect outcomes. Minimum-player failures award the fixture without blocking Continue.
- Live, skipped and saved/resumed matches use one event stream. Match review includes commentary, lineups, substitutions, minutes, action-based ratings and team statistics; bonuses cover participating substitutes. Extra time and shootouts are available to knockout fixtures in the engine; the playable league has no cup schedule yet.
- Full profiles, registration, global search and interface zoom are connected to existing keyboard navigation, confirmation and save flows. Football and development tuning is recorded in [engineering formulas](docs/FORMULAS.md).

## Included from 0.6

- Contracts > Clauses adds negotiable appearance and goal bonuses plus a one-season club extension option. Changes belong to the sent proposal; conditional or completed terms cannot be silently edited. Agent counters retain the clause package.
- Earned bonuses settle once per fixture, using player identities in the match event stream. Live, skipped and saved/resumed matches agree. Unpaid amounts remain visible in the clause register, survive employment ending and settle when funding is available. Loan bonuses remain the parent employer's responsibility.
- The signed clause register shows employment terms, option availability, next-sale rights and earned/paid bonus totals. Exercising a club option previews additional guaranteed wages and cannot be repeated.
- Club purchase/sale reviews support one gross-proceeds or profit-based sell-on right. A resale pays the original beneficiary atomically; profit uses the full acquisition fee, including deferred instalments. Original instalments remain due after resale. Rights persist through a loan and end at the next permanent transfer or release.
- Sales display existing sell-on costs and net receipts. Retaining future upside reduces the receiving club's upfront quote. Purchases preserve a clause proposal alongside the fee and schedule.
- Loan duration controls cover 14–84 days. Newly agreed durations begin at final registration, after the medical, and employment coverage is checked again. This fixes the PR #7 review finding. Existing 0.5 signed loans and pending fixed-date agreements retain their dates.
- Schema 5 reads schemas 1–4 without inventing past clauses or bonus payments. Guaranteed forecasts include earned unpaid bonuses but exclude unknown future performance, unexercised options and untriggered sell-on rights. Base wage budgets exclude performance bonuses; these are additional cash costs with no lifetime cap.

This milestone does not complete the full clause catalogue. Player options, release clauses, conditional transfer/promotion bonuses, wage escalators/relegation reductions, loan purchase clauses, full nation eligibility and autonomous AI negotiation remain open.

## Included from 0.5

- Recruitment includes contracted players, with retained market filters, scouting, notes, shortlists and authorised comparisons. True abilities remain hidden.
- Transfers desk: negotiate a selling-club fee, immediate percentage and deferred date, then complete personal terms and medical through Contracts. Club and player consent must both be valid; cash, registration and future obligations commit together.
- Player sales: select a receiving club, obtain a persisted quote, complete consent/medical checks and confirm registration. Both clubs record the same cash transfer; insufficient counterparty funds or inadequate remaining squad cover blocks completion.
- Incoming and outgoing senior loans: borrower wage shares from 50–100%, consent, medical and final review, preserved original employment, automatic return and window-limited recall. Early recall refunds the unserved fee proportion, shown before approval. The default quote is up to 56 days; duration controls allow 14–84 days where employment permits.
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

Full clause coverage, advanced loan restrictions and complete staff/authority behaviour remain on the release checklist. Senior-player free-agent signings and renewals now share the reviewed contract workflow.

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

This is an early playable version, not the finished AA game. The eight-club compact calendar remains development content. Full 14-nation world content, career creation/acquisitions, owner succession, multi-club groups, complete role/scouting/development behaviour, complete staff agreements, capability effects and group delegation, full transfer/loan clauses and competition rules, complete football/set-piece/tactical models, promotion/cups, complete commercial demand and rights obligations, full AI financial parity, detailed assets and the remaining accessibility/QoL requirements are still pending. The new career systems are connected playable implementations of a subset of their approved scope.

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

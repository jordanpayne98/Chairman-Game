# Club Chairman — Tactical Preparation Update (0.20)

A playable early Python/Pygame football chairman simulation. Take charge of Northbridge Athletic in the compact Northshire world or an England, Wales or Brazil national development scenario, with continuing league seasons and domestic cups. This is a playable development version; the approved full AA game is still being built.

## Play on Windows

Download **ClubChairman-Windows-preview** from the successful GitHub Actions run linked in the implementation pull request. Extract the entire ZIP into a folder, then open **ClubChairman.exe**. Keep the `_internal` folder beside the executable. Python installation is not required for the packaged build.

1. Choose New career and appoint a manager in Staff.
2. Filter and sort free agents in Recruitment. Use Lists to organise named shortlists, add private notes and pin up to four candidates to compare. Scout them before committing; completed scouting reveals exact current ratings; potential remains uncertain.
3. Review Finances > Forecast for the next 28 days, or Plan for the combined impact of pinned free agents. Plans change neither time nor funds; signings need individual confirmation. Review the wage limit and ticket price here too.
4. Continue one day or advance to the next fixture. Required chairman decisions interrupt time.
5. Watch text matches at 1x/2x/4x or skip. Your manager selects the team. Encourage them or request more attacking football; they can refuse.
6. Review player and manager contract expiries, then use Career > Prepare next season after closing the final match. Wages and deadlines continue through the two-week preseason. Previous tables and matches remain in Career history.

Save manually at any time, including mid-match. Autosaves follow management actions and full time. Load / recover career lists manual slots, three rotating autosaves and backups; a loaded career starts a separate save timeline so existing files are preserved. Windows saves live under `%LOCALAPPDATA%\ClubChairman\saves`. The application writes saves outside the game installation folder.

The update reads **existing 0.1–0.19 / schema 1–17 saves** and upgrades them in memory. Original files remain unchanged on load; new saves use schema 18. An old in-progress match and its remaining matchday fixtures finish with the original engine, preserving the outcome and payments. Later fixtures use the new football engine. Existing reports retain their original evidence; external reports remain partial until a new assignment completes. Hired players gain exact current ratings through club access. Older executables cannot read new saves. Existing contracts retain their expiry dates; renew before advancing beyond them. Shortlists, pins, notes and read markers travel with the career; interface preferences are stored separately.

Tab and Shift+Tab move focus; Enter activates the focused control. Ctrl+S saves, Ctrl+F searches players, Alt+Left/Right moves through navigation history, Space pauses live matches and F1 opens Help. Escape cancels an overlay or goes back. In the note editor, Enter does not submit while typing; Tab reaches Save note and Discard. Back/Forward and profile Previous/Next preserve filters, sorting and pagination. The sidebar collapses and the window scales with letterboxing.

Ctrl+K opens global search for known players, clubs, departments and help topics. Settings > Interface size cycles through 100/125/150/175% zoom. Mouse wheel pans vertically at larger sizes; Shift+wheel pans horizontally, and keyboard focus follows controls into view. Ctrl+0 restores 100%. This is whole-interface zoom; full responsive text reflow is still pending.

## New in 0.20

**Staff > Manager > Training report** shows recorded preparation for the manager's preferred formation and style, training sessions, match minutes and the latest attendance. Players without recorded evidence show “Not assessed”. The manager sets the tactical brief; the owner retains existing staffing, facilities and individual training-load controls.

Preparation grows gradually on eligible training days and through actual match minutes, with diminishing returns. Coaching capability, departmental workload, facilities, light loads and player recovery affect learning. Injured players and players needing recovery miss tactical sessions; fixture days are reserved for matches. Intense load does not grant an extra tactical-learning multiplier. Appointments, renewals and repeated clicks grant no learning. Previous systems remain learned through manager changes and player departures.

New matches snapshot preparation for the chosen starting system. A small, bounded passing-coordination effect uses only the players currently on the pitch, recalculating after substitutions and dismissals. Match exposure is credited once after settlement, capped at 90 minutes. Old active matches retain their original state and outcome; no training history is invented on migration.

This first pathway covers the owned senior squad's tactical practice. It does not implement pairwise relationships, full squad cohesion, tactical roles, alternative-system scheduling, memory decay or AI-manager training. The unchanged AI baseline and preparation coefficients remain provisional calibration. Player attributes, ability and morale are separate from this record.

## Included from 0.19

Managers now make starting selections using persistent formation, rotation and youth preferences. Four broad shapes are available: 4-4-2, 4-3-3, 4-5-1 and 3-5-2. If the preferred shape lacks eligible positional cover, tactical judgement and Adaptability can support a better-covered alternative. A suitable preferred shape is retained. Injuries, suspensions, registration and age rules remain binding.

Fresh legs places extra weight on fatigue; Continuity favours recent starters within a bounded window. Develop prospects gives a small opportunity preference to young players close to the best eligible current ability in their position, scaled by youth-development capability. Potential is not used as a selection shortcut. Managers remain responsible for their teams; these preferences are visible in **Staff > Manager > Manager profile**.

**Matchday > Selection** explains the starting plan, selected positional counts and individual selection factors, including the bench. Its dated record remains unchanged by substitutions, later appointments or player development and is retained in completed match reports. Older matches clearly state when no selection record exists.

Existing saves preserve their preferred formations and active matches. New careers start with style-related preferred shapes; rotation/youth preferences use an independent deterministic identity stream. This milestone covers broad starting shapes and selection. Detailed tactical roles, mid-match formation switches, full personality and training-familiarity transitions remain open. Preferences and coefficients are provisional tuning, not guaranteed improvements or extra match bonuses.

## Included from 0.18

**Staff > Manager > Manager profile** shows all eleven manager capabilities and absolute role-weighted current ability. Assess a candidate to gain current coverage; expired coverage becomes stale. Your appointed manager always has current club access. Candidate identities, capabilities and preferences survive appointments, replacement, contract expiry and save/load. Salary and style remain distinct from ability.

New matches preserve the manager's preferred approach and record a separate match plan. Tactical judgement evaluates a late score or numerical disadvantage; Adaptability coordinates a bounded attacking-risk adjustment. Match commentary records actual changes. Accepted owner instructions retain priority; encouragement or a refused request does not disable later manager choices. An unchanged situation does not trigger repeated tactical changes. Commercial or administrative capabilities do not grant a generic passing bonus. An existing saved match retains its original decisions and outcomes; subsequent matches use this pathway.

This first manager pathway covers attacking instructions, not formation/role changes or the complete personality, training-transition and preference model. The three-candidate market remains compact. Capability distribution, role weights, immediate no-cost assessment and tactical coefficients are provisional. There is no additional universal match bonus for manager CA.

## Included from 0.17

**Staff > People** now shows role-specific current ability and the eleven approved departmental capabilities, including Adaptability. An employee's current ratings are exact; completing the existing interview gives a candidate the explicit **Fully assessed** state. Initial references remain partial, and expired external coverage becomes **Stale**. Current ratings follow underlying skills; reputation, workload and salary do not redefine ability. Hiring still uses the existing salary, compensation, joining-date and authority workflow.

Candidate assessment coverage lasts a provisional, configurable 28 days. The profile shows the expiry; employment grants continuing club access. Legacy interviews remain partial until renewed through the contact/interview workflow. Existing saves gain Adaptability through a separate stable identity stream, retaining all ten old skills, personalities, employment and finances. Coverage suggestions now use exact current employee skills through the same authorised read model.

Role weights initially split equally between each department's two existing core capabilities; these are provisional calibration data. Adaptability is recorded and displayed for departmental staff but does not add an automatic work or match bonus. The manager extension is described above; staff development/potential, contextual importance and deeper personality behaviour remain unfinished. This milestone does not claim those systems complete.

## Included from 0.16

Player profiles show **exact current ability and all 37 current attributes** for players at your club and fully scouted targets. Numbers follow actual development and use consistent whole-number rounding; potential remains a dated uncertain forecast. Recruitment sorting and comparisons use the same authorised information.

The existing paid scouting assignment now explicitly finishes as **Fully scouted**. External current coverage lasts 28 days from delivery, a provisional configurable interval. Its expiry is visible on the profile. After expiry, the **Stale** label and widening ranges use the original evidence, without reading hidden current ratings. New scouting restores coverage. Legacy external reports remain partial; migration does not claim an old assignment was complete. Club access lasts while the player is at your club.

This implements the player-current-rating part of living GDD revision 0.10. Staff current ratings, reputation-driven negotiations, richer evidence gathering, historical report browsing and economic/match calibration remain pending. No GDD revision or match-engine change is included.

## Included from 0.15

Supporting pool clubs now use **reduced routine AI reviews**. Outside preseason/registration and urgent cases, they review every 28 days. Primary clubs and your owned club retain detailed weekly reviews. Missing squad or departmental cover, a severe availability crisis, approaching player/staff expiry or transfer bills trigger the existing weekly review. Pending deals, expiries, payments and wages still process daily.

**Competitions** shows the number of reduced and detailed clubs in each division. Promotion restores detailed reviews before next season’s fixtures are generated. Relegated rivals switch to reduced reviews; your owned club stays detailed even in the pool. Detail transitions and the completed season’s levels are saved with career history, without deleting or regenerating anyone.

Existing saves retain their current season’s review behaviour; the new policy starts when you prepare the next season. Saves without feeder pools retain detailed reviews for every club. Loading preserves the original source file, matches, people, signed obligations and evidence.

This is the first background-detail stage: it reduces routine decision work only. Football matches, daily recovery and player development still use their existing detailed simulation. Whole-country detail selection, reduced training/match simulation, the connected world and wider content remain unfinished. The 28-day routine period is provisional tuning in `data/detail.json`, not a full-world performance guarantee.

## Included from 0.14

**Start a new England, Wales or Brazil career** to include an eight-club regional feeder pool below the primary pyramid. Competitions > Regional pool opens its table and rules. Each pool club plays fourteen home-and-away matches spread through the national calendar. Three clubs exchange with England’s lowest primary tier; two exchange in Wales and Brazil.

Pool clubs retain their identities, players, staff, contracts, accounts and history when promoted. Relegated clubs continue playing in the pool; an owned club remains playable and can earn promotion back. Primary cups include primary-division members only, with eligibility updated when preparing the next season. Season history records the pool table and movements alongside the primary divisions.

Existing saves retain their original league structure, including at rollover; loading never inserts clubs or rewrites the source file. Compact careers remain unchanged. New national totals are 108 clubs in England, 32 in Wales and 62 in Brazil. These pools retain detailed football and player data; reduced routine reviews are described above. Wider reduced-detail simulation, the remaining countries and the connected world remain future work. Pool size, fictional club identities, initial squads and prizes are provisional development content in `data/feeders.json`.

## Included from 0.13

**Recruitment > Lists** creates, selects, renames and deletes named target lists. A player can belong to several lists. The selected list controls the table’s Saved/+ List buttons, Shortlist only filter and the profile’s Add/Remove shortlist action. Its name is visible in the table and profile. Up to twenty lists with unique names of 1–32 characters are supported; keep at least one list.

**Save visible page** previews the number of new targets and adds only the displayed page after confirmation. Existing targets are not duplicated. This never commissions scouting or submits an offer. Undo reverses the latest membership edit or list operation, including deletion, until another management action commits.

Shortlist only includes saved targets after signing, transfers or retirement; search and role filters still apply. Market scope is disabled in this mode so it cannot silently hide a saved player. Players keep their stable identity, notes and observed evidence. Unknown attributes remain unknown.

Older careers retain all saved targets in a list named Shortlist. Lists, memberships and the selected list persist in schema 11 saves. Loading does not rewrite the original save. Input validation preserves an unfinished name; closing a name draft asks before discarding it. Tab and Enter work with the list controls, including at the existing zoom settings.

This implements named recruitment lists (GDD Q06), visible-page shortlist additions (part of Q05), and immediate Undo (UQ06). Tags, reminders, expiry rules, broader entity-following, general multi-selection and task templates remain unfinished. Continental entrants and qualification remain unfinished.

## Included from 0.12

On the main menu, click **Scenario** to cycle through Compact, England, Wales and Brazil, then choose **New career** and review the selection. National scenarios currently simulate one country at a time; other countries are not running in the background. Existing saves keep their world, calendar, contracts and results. The compact scenario remains available.

| Scenario | Primary divisions | Primary clubs | Primary league matches per club | Calendar |
| --- | --- | --- | --- | --- |
| Compact | 2 × 8 | 16 | 14 | Short development seasons |
| England | 5 × 20 | 100 | 38 | August–May |
| Wales | 2 × 12 | 24 | 22 | August–May |
| Brazil | 3 × 18 | 54 | 34 | February–November |

All primary-division clubs enter their country's knockout cup. England exchanges three clubs between adjacent tiers; Wales and Brazil exchange two. Larger league tables and archives paginate, retaining promotion/relegation markers, match reports and recorded tie-breaks. New national careers now also exchange clubs with the regional pools described above.

National careers reserve league and cup dates together with a minimum three-day recovery gap. Optional blackout ranges are supported; impossible configurations produce an explanation and preserve the current career. No international windows are enabled yet. Annual season anchors, leap years, contract duration, new extension options, academy admission previews and financial planning now share calendar dates. Preparing next season does not jump time: summer wages, deadlines and construction still process day by day. New national contracts use season-end dates; previous signed terms are never recalculated on load.

`data/nations.json` records all 14 approved formats (38 divisions / 636 senior clubs), with explicit incomplete content families. Only the three national scenarios above are enabled. USA's closed system and top-eight playoff are recorded as requirements, not silently replaced with promotion/relegation. National scenarios use provisional city-based club identities, 18-player squads, existing staff/player name pools, GBP finances and simplified registration windows. Northbridge remains the owned development club. Full authored history, country-specific population/finance/eligibility content, reserve/youth squads, remaining feeder content, other active countries and international/continental competitions remain required.

Weekly AI review avoids repeated squad-cover, cash, payroll and equivalent registration calculations. Decisions retain the same rules and observations. Large national careers still need performance work: this is not a claim that the full-world performance gate has passed.

## Included from 0.11

Competitions lets you switch between the Northshire Premier and Championship. Each division has eight clubs playing fourteen home-and-away league matches; all sixteen enter the shared four-round cup. Three clubs are automatically promoted and three relegated at season end. Final tables and movements are recorded immediately, and **Career > Prepare next season** applies membership changes with the next fixtures. Your club, staff, contracts, cash and scouting records continue in its new division.

Tables resolve equal points by goal difference, goals scored, head-to-head points within the tied group, then a seeded order recorded with the season. Prize money follows the club's division and final position; rival accounts now receive their league prizes too. Championship prizes are provisionally half Premier awards. World expansion and tuning live in `data/leagues.json`.

Older saves finish their existing season with the original fixtures and tie-breaks. The second division is added at the next season boundary, without retrospective relegation or changing old results. Season history retains both division tables, confirmed movement and cup records; old archives remain readable.

This is a playable competition milestone. The connected 636-club world, continental qualification and international calendars remain future work. The two compact divisions and prize values are development content.

## Included from 0.10

Competitions > Northshire Cup shows the seeded draw, round dates, results and archived match reports. New careers enter the cup immediately; existing saves finish their original schedule and enter it from the next season. League and cup fixtures appear together in Fixtures. Defeat ends your cup run, but remaining rounds continue without blocking the career.

Knockout draws go to extra time and penalties. League standings remain league-only; player seasonal totals cover both competitions. Domestic registration, loan-parent restrictions and bans are shared. Cup dates reserve at least three days from league matches. Draws, advancement, the winner and reports persist through saves and season history. Match speed and save/resume do not reroll them.

This is a competition milestone, not the complete world: continental/international calendars and the 636-club database remain unfinished. The compact cup has no prize money yet; owner home fixtures use existing gate receipts. AI finances still use their provisional aggregate income. Both clubs failing the minimum-player rule advances one through a recorded seeded administrative draw without player appearances or goals; this development fallback is not a real-world rule.

## Inherited Figma UI in 0.9

The approved Figma Executive interface is now rendered by the actual Pygame game. Shared charcoal/sage tokens, bundled IBM Plex Sans/Lora fonts, exported navigation icons and the Northbridge crest work offline. The application stays in Python/Pygame.

- Grouped, collapsible navigation and a persistent top bar retain live club/date/decision context, search, saving and Continue. Stadium maps to the existing Facilities system; Competitions maps to League; History & career maps to Career. Responsibilities opens the working staff authority screen.
- The overview shows real cash, budget usage, standings, supporter mood, urgent reviews, fixtures, dated cash forecasts and project status. Sample figures and clubs from the design are not simulation data.
- The split inbox separates unread news from unresolved decisions, keeps message selection, paginates long reports and opens the existing validated approve/decline actions. Reading never approves a decision.
- Player profiles add estimate/confidence cards, grouped attribute rows and an evidence panel. Unknown attributes remain unknown, all 37 attributes stay available, and negotiation, scouting, development, notes and comparison remain connected.
- Squad/recruitment tables, department panels, tooltips, reviews, settings and save recovery share the new components. Long reviews paginate without hiding their controls. Fixtures provides a full paginated season list and opens saved match reports.
- The main menu can continue the latest valid save, resume an active career, open all checkpoints and change presentation settings before starting a career. Original save files are preserved by the existing recovery-timeline workflow.

No simulation rules or save schema changed. The internal canvas remains 1440 × 900, scaled to the window, with the existing 100–175% zoom and focus following. Full responsive reflow, arbitrary dashboard arrangement, single-click person drawers, content management, full career-creation choices and multi-club/wealth systems are still open. The full 30-frame Figma prototype is not claimed to be implemented gameplay. See [Figma implementation coverage](docs/FIGMA_UI_IMPLEMENTATION.md).

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

- New seeded career, compact or national scenarios with division-specific home/away fixture lists.
- Three manager candidates; manager-controlled lineup selection and tactical risk.
- Paid scouting with delayed uncertain reports; cash- and wage-validated free-agent signings.
- Wage budgets, home ticket demand, owner equity injections, payroll, sponsorship, ledger and league prizes.
- Chairman spending decisions and a manager response to bench messages.
- Connected match simulation, commentary, statistics, league standings and season completion.
- Versioned atomic SQLite saves, integrity checks, backups and recoverable timelines.

## Preview boundaries

This is an early playable version, not the finished AA game. Compact and national scenarios remain development content. Full 14-nation world content, career creation/acquisitions, owner succession, multi-club groups, complete role/scouting/development behaviour, complete staff agreements, capability effects and group delegation, full transfer/loan clauses and competition rules, complete football/set-piece/tactical models, full national/continental competition structures, complete commercial demand and rights obligations, full AI financial parity, detailed assets and the remaining accessibility/QoL requirements are still pending. The new career systems are connected playable implementations of a subset of their approved scope.

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

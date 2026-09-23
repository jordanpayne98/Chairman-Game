# Club Chairman release readiness

Implementation tracking against the attached living GDD revision 0.18. Earlier milestone entries below are historical; the latest development checkpoint records current implementation evidence. This is an engineering checklist, not a replacement design document or design approval. The full AA game is not release-ready.

## Batch 3 requirement register — GDD 0.18

### Execution order — systems across all fourteen nations

Jordan's 23 September direction: work horizontally across every playable nation for each system, including domestic cups as one cross-nation batch. Preserve existing identities and reusable services. The later GDD 0.18 approval replaces national league structures with shared English profiles; it does not complete the implementation gates.

| Pass | Coverage required across all playable nations |
|---|---|
| 1. League structures | Five shared English tier profiles across every approved national depth; sizes, points, table ties, promotion/relegation, playoffs, feeder boundaries, national season windows and dated sources |
| 2. Domestic cups | All applicable senior cups and supporting competitions; entrant pools, entry rounds, draw/venue rules, match resolution, calendar windows, awards and qualification routes; explicitly sourced inactive competitions |
| 3. Registration and regulation | Transfer windows, squad/loan/homegrown/foreign-player rules, eligibility exceptions, licensing and financial monitoring |
| 4. Opening world population | Named fictional clubs, supporting pools, squads/staff and current facilities/finances; initial memberships and seeding, without pre-game results or biographies |
| 5. Continental and international access | Complete competition definitions, named eligible opening participants, access slots, holder/duplicate resolution and future outcome-based qualification |
| 6. Integration and final gate | Career scheduling, simulation, cash, persistence, inbox/calendar/UI and one final regression/build gate |

Each pass uses a fourteen-nation coverage matrix and separately records researched, defined, implemented, integrated and verified status. Any missing source or unresolved exception remains a named blocker; never invent rules or mark a whole pass complete because its schema exists. Work through the cross-nation pass before returning to isolated country polish. Next active pass: league structures for all fourteen nations at their approved depths.

The living GDD revision 0.18 approves English league rules by equivalent tier across all fourteen nations. One division per playable level gives 38 divisions and 856 senior league places: 20 per top tier and 24 per lower tier. National registration, employment, financial and ownership rules, domestic cups and continental competitions remain separate. Calendar dates must be reconciled with the new match counts; this is not an approval of identical dates worldwide. Existing careers keep their saved rules.

### Shared league structure pass — CONTENT-047

`data/production_rules_2026.json` holds five versioned shared profiles and 38 national instances. Validation rejects profile drift, extra regional divisions, closed-pyramid overrides, missing profile references and lost bottom-tier feeder boundaries. Current Premier League, EFL and FA handbooks support expanded table, access, playoff-pairing, cessation and feeder definitions. Separate playoff match provisions, National League additions and narrow table interpretations remain open; see `docs/ENGLISH_LEAGUE_RULE_DETAILS.md`. Approval of the adaptation does not certify those gaps. All structures remain PARTIAL and unintegrated with careers.

Completed-fixture standings and an access preview now run for the same profiles in all fourteen nations. They preserve unresolved ties and refuse to guess who crosses an automatic promotion/relegation boundary or receives an EFL playoff seed. Association rulings are explicit inputs. Disciplinary end-of-table decisions, playoff deciders, eligibility, calendar integration and actual careers remain pending; the preview does not certify a finished league pass.

Recorded 42-match EFL disciplinary assessments can now resolve the next published tie stage; missing evidence blocks ordering. An authored calendar plan can be checked against 38/46 full rounds, national windows and blocked dates. Ordinary cross-division and background-feeder exchanges conserve actual named clubs and refuse unrecorded playoff/eligibility decisions. These conditional services do not supply missing national dates or identities, resolve licensing/vacancy exceptions, or create the current National League playoff format. All 38 active divisions still have empty production calendars, opening membership lists and playoff brackets, with pending feeder boundaries. Pass 1 remains open.

| Nations | Depth each | Divisions | Senior places |
|---|---:|---:|---:|
| England | 5 | 5 | 116 |
| Germany, France, Spain, Italy, Scotland, Brazil, Argentina | 3 | 21 | 476 |
| Netherlands, Portugal, Ireland, Northern Ireland, Wales, USA | 2 | 12 | 264 |
| Total | — | 38 | 856 |

The former 43 national league definitions and opening league allocations are retained in `data/reference_national_leagues_2026.json` as superseded research and legacy service fixtures. They are not active production definitions or pre-game sporting history. National split, conference, period-title, Apertura/Clausura and relegation-average formats no longer block the shared league design. The former proposed USL second-level choice is superseded by the approved open two-tier model.

All 284 existing Welsh club identities remain. New league membership lists are deliberately unallocated until the opening-world pass reconciles 20/24 places and feeder pools. The previous cup snapshot, admission facts and reusable services are retained, but cup cohorts and continental nominations require revalidation against the changed memberships. The old Welsh cup builder now refuses to overwrite shared-model data. Empty or stale allocations remain production blockers; they are not replaced by invented past promotions.

Verification: CONTENT-046 passed 31 focused shared-standings, shared-rule, league-structure and content checks; CONTENT-045 passed 13 focused checks and profile-drift validation. The preceding CONTENT-044 passed 65 focused checks across shared rules, legacy access, content, entries, cups and qualification. These cover 20/24-club balanced fixtures, all fourteen depth mappings, drift rejection, preserved legacy playoff behavior and atomic refusal of the old cup builder. No new playable build is claimed. The production gate remains blocked; blocker counts are diagnostics, not progress percentages.

CONTENT-047 additionally passed 35 focused shared-table, national-calendar-validator, ordinary-exchange, existing league and content checks. Those include synthetic season results and named memberships across all fourteen nations. The production audit still reports 593 blockers across Batch 3 and related content; this count is diagnostic, not a Pass 1 percentage. The missing source and authored-input requirements are named in `docs/ENGLISH_LEAGUE_RULE_DETAILS.md`.

Pass 1 remains active: finish the five English profiles and their result-driven table/access paths, then reconcile each national calendar and feeder boundary. Continue the all-nation cup pass next. Population and career integration retain their later pass order. The compact development population catalogue and existing career scenarios remain unchanged and do not certify the 856-place production world.

| Requirement | Design | Rule/content evidence | Behaviour and UI | Persistence and checks | Remaining gate |
|---|---|---|---|---|---|
| World people and careers | Confirmed | Partial: fictional pool and names, no calibrated national distributions | Partial: background ageing, development, free recruitment, employed background purchases and public histories | World lifecycle and same-ID fee checks; snapshot persists | Detailed rosters, origins, bidirectional employed market, staff succession, calibration and long-run scale |
| Domestic national calendars and registration | Confirmed | Partial: shared league profiles plus provisional compact/England/Wales/Brazil scenarios | Partial: domestic fixtures, cup and youth calendars; shared English profiles not integrated | Focused schedule checks; no 14-nation integration | Complete shared tier sources, windows, exceptions/playoffs, state competition reconciliation and licensing |
| Continental and world club tournaments | Confirmed | Missing: full entrant/access and supporting-club allocations | Missing | Missing | Verified format versions, all entrants, duplicate/holder resolution and multi-season qualifier graph |
| National teams and international tournaments | Confirmed | Missing: full qualifying, eligibility and window records | Missing | Missing | Selection, releases, travel, fatigue, caps, results and return in same careers |
| Shared inbox/calendar and world news | Confirmed | Design specified in chapters 22, 26, 37–39 | Partial: existing message list and calendar lists; world cycle counts shown | Message-specific actions, reminders and deadline persistence missing | IC01–IC08 and connected transfer/competition source events |
| Integrated Batch 3 gate | Confirmed | Incomplete | Incomplete | No final regression or Windows build | AF-C01–05, full-world/long-run performance and content validation |

## Earlier design requirement — GDD 0.13 inbox and calendar

Design recorded; implementation pending. The expanded chairman inbox requires per-message unread/workflow state, searchable filtered archives, structured reports, threads, source-specific decisions, delegation tracking, bookmarks/notes, configurable briefings and followed-person/club/competition news. Background nationalities and careers remain eligible for public news regardless of playable-league status, with digests and subscriptions controlling volume.

The shared calendar requires agenda/day, week, month and season/year views; football, contract, financial and project dates; authoritative deadline and event details; provisional/rescheduled status; congestion visibility; linked inbox actions and persistent reminders. Continue must respect the last valid mandatory decision opportunity even when its message is read, archived, muted or snoozed. Migration must preserve known history without inventing actions or past events.

The current plain-text inbox, aggregate read boundary, global decision controls and fixture/calendar lists do not satisfy this scope. Implement common event/message/reminder services and core screens alongside Batch 3, then connect business/project and multi-club sources in their respective batches. All IC01–IC08 acceptance cases remain pending, including selected-message correctness, deadline protection, save/resume, background-person news, rescheduling, calendar consistency, permissions and accessibility/history scale. See DESIGN-013 for the reviewed document and implementation gaps. At that design checkpoint the game was version 0.30; Batch 3 is still open.

## Current update — 0.30 / Batch 3 living world population

Implemented: 239 nationality identities independent of playable leagues; 68 RNG name pools for initial people and later player/staff entrants; 81,039 fully populated background people in the compact opening world; persistent monthly careers, contracts, movement, development/decline, injuries, retirement and annual generation; public country/person/history browser; identity-preserving recruitment entry for unattached players and staff; schema-29 migration preserving old identities and requiring explicit background-world creation. See PLAY-030 for exact evidence and provisional policies. The living GDD revision 0.12 records Jordan's nationality/naming/lifecycle clarification and remains distinct from implementation status.

Verification: focused world and affected-flow checks, a genuine predecessor mid-match migration comparison, five-year reduced-world turnover, a 13-month full-population pass with ledger validation and actual Pygame visual inspection. Final Windows/Linux regression and packaging remain pending. No full-batch or long-run calibration pass is claimed.

Remaining Batch 3 scope: employed international transfers; connected national calendars and continental/international competition/qualification graphs; national-team release/return and registration; full detailed domestic rosters and richer career histories. Wider name pools, national economic/population calibration, full manager succession and efficient cancellable monthly processing remain open. Current compact/England/Wales/Brazil scenarios are development scenarios; the fourteen-nation inventory is not fourteen playable career modes. No Windows update has been published.

## Current update — 0.29 / Batch 3 calendar and population groundwork

Implemented: recovery-safe development scheduling against senior fixtures and all potential cup rounds; configured blackout enforcement; visible scheduling diagnostics; frozen youth and senior-exemption ages; development-to-senior recovery guard; population reconciliation evidence with retained identities; read-only calendar/population UI; schema-28 migration deferring new rules until the next season.

Batch 3 is NOT complete. Connected active/background national worlds, continental and international tournament/qualification graphs, national-team release/return timelines, competition-specific continental registration and sustainable full-scale rosters remain open. Current shipped scenarios remain isolated domestic pyramids. Existing supporting-club detail policy is unchanged. Supporting-region identities and complete qualification allocations are explicitly unresolved in GDD revision 0.11; do not silently create tournament entrants to bypass this gate. Existing automatic background senior replacement and annual intake policies remain provisional.

Verification: nine focused domain/UI checks passed; genuine v0.28 minute-27 save resumes identically for match, fixtures, people, clubs, cash/ledger, pathways and social records, with original SQLite bytes unchanged. Calendar, population and populated reconciliation screens rendered and inspected. The broad regression attempts were interrupted; no complete passing result is available. No remote publication or Windows package.

## Current update — 0.28 / Recruitment and Development Batch 2

Connected implementation: paid staff-capacity scouting with dated evidence and travel previews; recruitment briefs based on observed reports; partial-success saved-target batches; completed-signing outcomes; separate youth/reserve fixtures, appearances and tables; recovery/challenge-adjusted exposure; monthly staff advice, group changes, loan monitoring and academy renewals; bounded annual AI admissions and renewals; schema-27 migration without retroactive population.

Full-GDD requirements remain open: worldwide 18 youth / 18 reserve / 25 senior content and sustainable multi-year population, regional recruitment pools, complete development calendars and frozen eligibility (Batch 3 world scope); personality/reference evidence, mentoring, mature development/retraining and detailed injury policies; staff promises, departmental resources and destination-specific loan advice (Batch 6 football/staff and alpha integration); remaining contract families and full-scale calibration. These are not removed or declared complete by this milestone.

The compact founding rosters and development fixture model are provisional tuning. AI employment still uses existing finance/registration checks. Existing saves are not silently repopulated. Publication and a verified Windows package remain separate pending delivery work.

## Current gameplay scope: Club Dynamics Update 0.27 — Batch 1

Connected senior player contact/influence and settling evidence, actual-participant coordination, manager/coaching witness reactions, confirmed private follow-ups, a concerns overview and monthly summaries now extend 0.25–0.26. Social inputs persist under schema 26 without inventing old contact. The group summary is not a second match modifier. The GDD remains unchanged.

Still open within the wider social pillar: leak/faction/mentoring event families; full stable personality and staff departmental relationships; expanded deferred bench requests; full staff remit/resource commitments; multi-club/successor identities; realism calibration. These remain approved scope, to be reconciled into subsequent connected milestones (particularly recruitment/development, ownership, football/AI and alpha integration). Batch 1 delivers the listed playable flow; it does not close the entire chapter 16 acceptance matrix. Publication and Windows packaging are pending.

## Previous gameplay scope: Private Support and Relationships Update 0.26

Updates 0.25–0.26 add source-based player morale, dated causes and trends, first-team mood summaries, private support meetings and sparse player/chairman relationship evidence. Local verification and limits are recorded in DEVELOPMENT_CHECKPOINT.md and the milestone entries below. Wider social systems remain open; publication and Windows packaging remain pending.

Jordan approved grouping related implementation work into larger milestones on 22 September 2026. The seven-batch delivery sequence is recorded in DEVELOPMENT_CHECKPOINT.md; it does not replace this requirements register or reduce the GDD. Reconcile historical entries against current code before sizing each batch. No fixed version is promised as alpha.

## Previous gameplay scope: Playing-Time Commitments Update 0.24

Explicit senior domestic role agreements now connect employment talks, a profile conversation, pre-kickoff availability, real minutes/starts, dated reviews, persistent private concerns and subsequent consent. Manager selection remains autonomous. Schema 23 preserves older contracts and active matches without inventing promises. New AI arrivals may agree rotation using the shared rules. The wider social influence/morale pillar, manager endorsement, bespoke development plans, loan promises, richer negotiation motives and balancing remain open. See DEVELOPMENT_CHECKPOINT.md for verified checks and the outstanding publication step.

## Previous gameplay scope: Reputation & Career Evidence Update 0.23

Dated player/club performance reviews and season honours now develop domestic standing, with persistent league/cup records, bounded change, public history screens, recruitment consequences and schema-22 compatibility. This extends 0.22 employment consent without bypassing seller, player or buyer gates. It does not close the full reputation/recruitment pillar: calibrated initial reputation profiles, calibrated performance/exposure, staff and international scope, commercial integration, manager-fit forecasts, playing-time commitments, relationships and competing packages remain open. See DEVELOPMENT_CHECKPOINT.md for verification and publication status.

## Historical gameplay scope: Competitions Update 0.10

The compact domestic cup now connects seeded draws, byes, extra time/penalties, background rounds after elimination, fixture/report UI, trophy history and schema-8 persistence. League standings exclude cup results. Existing saves retain their original schedule until the next season. This closes the generated-cup portion of the next dependency, not the complete competition milestone.

Still open: promotion/relegation, multi-division membership and qualified replacements, continental/international qualification and calendar graphs, multiple competition registrations and per-competition player statistics, full financial parity and the approved world content. No cup prize is budgeted in the current development data. Shared domestic bans and an explicit double-forfeit draw are documented provisional rules.

## Inherited presentation scope: Figma UI Update 0.9

The approved Figma visual system now runs in Pygame across existing game screens. Overview, split inbox, player evidence/profile, menu, save manager and fixture list use their connected runtime implementations. Fonts, icons and the Northbridge crest are bundled for offline operation. Long report/review readers paginate and preserve confirmation checks. This changes presentation and navigation only; schema 7 and simulation behaviour are unchanged.

Coverage and explicit remaining Figma gaps: `FIGMA_UI_IMPLEMENTATION.md`. Multi-club/personal investments, extended career setup/content packs, person drawers, responsive text reflow, configurable dashboard arrangement and the complete release/accessibility gates are still open. No full UI or AA completion claim.

## Inherited playable scope: Staff and Delegation Update 0.8

A compact eight-club league continues across seasons, with fourteen weekly rounds and a two-week preseason. This development calendar is not the approved full international football world. Original 0.1/0.2 saves migrate without replacing their source. Their existing contracts retain their actual end dates: review renewals before progressing beyond those dates.

| GDD area | Working coverage | Required before calling the AA game complete |
|---|---|---|
| 1–3: experience, setup, time | Owner-led game, paused management, daily Continue, decision stops, repeatable compact seasons | Club creation/acquisition setup, configurable active nations/detail, full event calendar and decision queue |
| 4–5: owner and group | Finite owner cash separate from club funds | Owner creation, personality, aging/retirement/succession, shares, due diligence, acquisitions and group authority |
| 6–8: world and competitions | Eight fictional clubs, league table, persistent fixture history | Approved 14-nation / 38-division / 636-club content, history, promotion/relegation, domestic/continental cups, supporting nations and internationals |
| 9–11: people and knowledge | Approved 37-attribute catalogue, position-weighted overall, one-time potential sampling, weekly development and bounded youth potential reviews; dated uncertain estimates, hidden-data-safe filtering/comparison | Complete role/retraining models, mature/setback potential policy, complete staff capability effects, richer evidence-based scouting, staff knowledge and discovery |
| 12: contracts | Free-agent and own-player negotiations, counteroffers, expiry/cooldown, reserved capacity, medical review, atomic completion, renewal and expiry; club purchases/sales, deferred fees and senior loans with wage sharing, recall refunds and timed return; appearance/goal bonuses, a one-season club option, gross/profit sell-on rights and earned bonus payables; fixed transfer release amounts, player options, annual wage rises/relegation cuts, employment promotion bonuses, appearance/promotion club payments and consented loan purchases | Buy-backs and first-refusal rights, country-specific buy-outs, loyalty/payment schedules, full-season loan purchase timing, richer club/player negotiations, competition-specific eligibility, advanced loan restrictions and full transaction coverage |
| 13: academy | Persistent annual trial cohort, individual admissions, wages, promotion from 16, training focus/load plans and periodic estimates | Full youth/reserve squads and competitions, regional pools, staff-recommended plans, youth loans, mature development model and population balance |
| 14–16: staff and authority | Existing manager contracts plus nine departmental roles, ten assessed capabilities, interviews/counters, dated employment/compensation/notice, capacity assignments, presets, rolling authority limits, approval cases, action reasons and monthly digest | Unified manager recruitment, full role/part-time/availability models, complex agreements/promises, richer interviews and capability effects, group authority, configurable excluded actions and sparse relationship systems |
| 17: football | Saved possession/action engine, cards/bans, substitutions, injuries/recovery, added time, minimum-player rules, ratings and reports; live/skip/resume equivalence; tested knockout extra-time/shootout primitive | Full restart/set-piece/role/tactical models, advanced keeper changes, discipline resets, deeper injury/workload calibration, competition integration and broad outcome validation |
| 18: finance | Integer-pence ledger, cash/payroll/reservations, owner equity, forecast with dated fees/sponsors/loans, counterparty cash ledgers and wage accrual, dated staff salary forecasts; rival recruitment/renewals within payroll, reservation and cash-cover checks | Complete accrual accounts, debt/investments, taxes/regulation, insolvency and AI financial parity |
| 19: commercial | Tickets/attendance, baseline sponsor income, three negotiable exclusive sponsor inventories with dated cash/expiry and naming sentiment | Full audience segments, season tickets, hospitality, merchandise/marketing, rights geography, performance bonuses and enforceable service obligations |
| 20: facilities | Training/academy/stand proposals, fixed-price construction, timed closure/opening, capacity/upkeep effects | Full stand/asset records, land/leases, permission/tender/inspection, staged payments, risks/change orders, new ground and rights consistency |
| 21: dialogue | State-driven contract transcript and factual event inbox | All approved scenario families, voice variations, promises, condition validation and localisation keys |
| 22–24: interface | Executive shell, complete attribute profile groups, development/medical views, registration review, match statistics, department/player/help search, existing commercial/contract/career screens, connected staff profiles/responsibilities/approval/report desks | Remaining departmental workflows, profile side panels, responsive text scaling and consistent validation/denial coverage |
| 25–26: data and saves | Snapshot tuning, JSON inside atomic SQLite, checksum verification, backups and migrations 1→2→3→4→5→6→7; original-engine completion of old in-progress matchdays | Pack import/conflict tooling, approved mod formats, full normalised/indexed event storage and world-scale performance |
| 27–31: delivery and content | Playable versioned milestones and this evidence register | Full staged gates, complete production database/assets/dialogue manifest, historical retention and population datasets |
| 32: usability/accessibility | Keyboard actions, F2 explanations, safe modal focus, help, reduced motion and 100/125/150/175% whole-interface zoom with focus-following pan | Guided onboarding, responsive text reflow across all scale workflows, remapping/conflicts, contrast audit and representative playtests; zoom alone does not close QAT-12 |
| 33: presentation | Original deterministic crests/portraits/stadium diagram, goal emphasis, construction indicator, optional synthesised cues | Finished art direction/assets throughout, kits/competition/milestone art, complete volume controls/ambience, localisation architecture and editorial pass |
| 34–35: release | Targeted tests, real previous-build save migration, Windows packaging workflow | Ten 50-season full-world runs, performance profile at years 1/10/50, exploit suites, clean offline install and all release gates |
| 37–39: system/UI QoL | Shortlist/notes/pins, estimates/cost comparisons, forecast, history memory, offer/registration drafts, unread distinction, global search and tooltips, retained staff/authority drafts and reviewed coverage/presets | Named lists/scenarios, advanced tables, safe bulk operations, notification policies, saved layouts, calendars, complete recovery browser and all QAT workflows |

Registration coverage now includes senior/age/non-homegrown limits, competing conditional reservations, matchday injury/suspension/loan-parent restrictions and atomic completion checks. Full nation/competition-specific policies, exemption cutoff dates, multiple registrations and appeals remain open.

## Evidence for the staff and delegation milestone

- Contact/interview/counter/appointment, compensation, dated payroll, renewal, notice, vacancy recovery and preserved signed commitments have domain coverage. Capacity, protected approval clauses, split-spending limits, guaranteed future wages, atomic denials and changed/duplicate approval guards are exercised.
- A delegated month includes scouting, player renewal, sponsorship, training and club decisions with a reconciled digest. Saving midway and resuming produces the same complete simulation state. This caught and corrected ordering-dependent choices and assessment calculations after JSON reload.
- Rival recruitment uses persisted noisy observations and public terms; tests alter hidden player truth without changing policy decisions from the same observations. Private targets stay outside the owner snapshot. Insufficient funds and payroll authority block new agreements and renewals, including owner-originated outgoing deals.
- Actual published 0.7 source created a minute-27 save. New-build completion matched cash, ledger, people, clubs, fixtures, clauses, market and commercial records exactly. Original bytes remained unchanged and the schema-7 save roundtripped.
- Staff workflows have rendered mouse/keyboard tests, retained drafts, non-mutating previews and maximum-zoom reachability. People/profile, Responsibilities/editor, Approvals and Reports layouts were rendered and inspected.
- Three PR #9 findings have regression coverage: sponsor/bill ordering, outgoing destination registration checks and hidden external fitness. Final source, cross-platform and packaged executable evidence belongs in the implementation PR.

This is a working compact-league foundation. AI clubs still receive provisional aggregate operating income; their own staff hiring and renewal negotiations are compressed. Scheduled background population repair remains provisional. The separate manager workflow, complete personality/promises, richer staff scouting/interviews, all ten capability effects, group/multi-club authority and full financial parity remain open. Staff Finance currently provides forecasts and briefings; budgets and owner funds remain chairman decisions. Performance-clause contracts return to the ordinary owner Contracts workflow.

## Evidence for the football and development milestone

- Source domain and Pygame input coverage includes 37 attributes and persistent potential, stale knowledge, training, registration refusals, capacity reservations, bans, injuries, no actions after removal, substitutions, match resumption and a deterministic shootout winner.
- Live and skipped football reconcile the same goals, participants, appearance bonuses, financial postings and final states. Unavailable squads produce a settled award so Continue remains usable.
- Actual 0.6 source created a minute-27 save. New-build completion preserved cash, ledger, table, fixtures, contract/market/commercial data and all pre-existing player fields exactly. The source database remained byte-identical and the migrated save roundtripped.
- Rendered profile groups, Development, registration, commentary, lineups, statistics, search and 175% zoom were inspected. Input tests exercise training controls, list confirmation, search, review tabs and keyboard focus at maximum zoom.
- A 1,000-fixture seed sample and provisional formulas are recorded in FORMULAS.md. It does not close full-world simulation or usability gates.
- Final source, Windows/Linux CI and packaged executable evidence is recorded in the implementation PR. Physical Windows playtesting remains open.

## Evidence for the clause milestone

- Bonuses derive from persisted match events, settle once and preserve unpaid balances after expiry/sale. Live, skipped and saved/resumed play agree.
- Gross/profit resale tests reconcile payer, seller and beneficiary cash, retain original deferred debt, handle loss sales and verify a sell-on receipt during repurchase against the review.
- Options extend employment once; invalid or changed clauses after conditional consent fail atomically. Save roundtrips retain rights and payments.
- Loan duration now starts at registration and rechecks employment at completion. Existing signed loan dates remain unchanged.
- Actual published 0.5 code created a minute-27 save with an active loan. Schema-5 resume matched cash, ledger, people, table, loan dates and legacy match results/commentary; new shooter-ID metadata was excluded from the comparison. Original save bytes were unchanged.
- Source test and executable build results are recorded in the implementation PR. Physical Windows playtesting and the full AA gates remain open.

## Evidence for the transfer and commercial milestone

- Purchases and sales conserve inter-club cash, personal and club consent expire together, and simultaneous loan/purchase reservations cannot reuse the wage budget.
- Dated fees settle once and survive season rollover; incoming loans return to their parent and original employment survives. Same-day recall refunds the full unserved fee to prevent fee farming.
- Forecasts reconcile against actual payroll, transfer instalments, loan returns and sponsor payments when uncertain gate receipts are isolated.
- Duplicate exclusive sponsorship rights are rejected; there is no upfront income and receipts match their schedule.
- Rendered mouse flows cover club purchase through Contracts, commercial signing, receiving-club selection, outgoing loan and recall. New layouts are visually inspected.
- Genuine 0.4 mid-match save migration to schema 4 preserves source bytes and exact cash, players, ledger, table and fixture outcome. CI and packaged results are recorded in the implementation PR.

## Evidence retained from the contract milestone

- Removed the instant-signing bypass while preserving old employment and load compatibility.
- Cost previews reconcile with real completion for concurrent offers; negotiated terms and reservations are not counted twice.
- Fast-forward interruption, explicit override, transcript archive and current-versus-draft financial review are connected to real mouse/keyboard controls.
- New screens were rendered and inspected. Exact cross-platform and packaged checks are recorded in the implementation PR.

## Evidence retained from the career milestone

- Automated domain and Pygame input tests cover multiple seasons, duplicate settlement/commands, financial reservations, expiry, notice payments, academy admission/promotion, construction opening, navigation, notes and keyboard explanations.
- A save was generated with the actual 0.2 source, loaded by 0.3 mid-match and resumed: cash, ledger, table and complete fixture results matched the original source exactly; the original save file remained byte-identical.
- New screens were rendered and inspected; this is not a substitute for physical Windows playtesting or representative usability studies.
- The packaged self-test exercises two seasons / 112 fixtures with negotiations, reserved capacity, academy, an operational facility, manager replacement and save/resume.
- The implementation PR records the exact Windows/Linux CI run and downloadable artifact after the checks complete.

## Next dependency sequence

1. Build multiple divisions and validated promotion/relegation on the new domestic-cup foundation before scaling world content.
2. Add academy competitions and long-term population policy, while completing contract/loan clauses, staff capability effects and AI financial parity.
3. Connect career creation, ownership/group management, succession, group delegation, promises and commercial/asset obligations.
4. Complete UI/accessibility/content families and perform full-world simulation, performance, exploit, usability and release gates.

All rows remain part of the approved game. A working screen or one passing test does not close an entire row.

## Recruitment lists milestone 0.13

Q06 now has up to twenty named player shortlists, independent memberships, persistent selection and stable links through transfers/retirement. Q05 has confirmed additions of the current visible page only, with duplicate suppression; this is not general multi-selection, scouting batching or task templates. UQ06 covers exact immediate Undo of membership changes and list create/rename/select/delete, invalidated by later management commands. Existing notes remain shared per player in the current single owned club. Tags, reminders, shortlist rationale/expiry, multi-club scope and other followed entity types remain required.


## Current ability milestone 0.16

Implements revision 0.10 player visibility: hired/fully scouted exact current ratings, dated uncertain potential, explicit full/partial/stale knowledge, shared profile/comparison/sorting permissions and schema 14 compatibility. Existing paid scouting completes coverage; richer assignments and calibration of the provisional 28-day coverage period remain open. Staff exact ratings and the eleven-capability catalogue, contextual importance/reputation, personality and economics calibration are not delivered by this milestone. Reduced supporting-club football/training and wider world expansion remain on the backlog.


## Departmental staff ability milestone 0.17

Implemented exact current departmental capabilities and role-specific CA for hired/fully assessed staff, eleven displayed capabilities, interview completion/expiry states, authorised coverage recommendations and schema 15 migration. Partial or stale evidence stays bounded to recorded information. The separate manager system still requires integration with the catalogue, positive Adaptability role weighting and observable tactical effects. Staff potential/development, importance/rank, personality depth and richer assessment workloads remain open. Departmental weights, initial Adaptability distribution and 28-day coverage are provisional tuning.


## Manager integration milestone 0.18

Implemented persistent candidate capabilities, exact/stale/club-access manager profiles, positively weighted Adaptability in manager CA, retained identities across appointment/expiry and a first observable tactical instruction pathway. New match plans separate preferred risk from actual risk; judgement evaluates context and Adaptability coordinates bounded changes. The prior generic manager passing bonus applies only to legacy matches. Schema 16 adds manager metadata without changing active-match state.

Still open: expanded manager market, richer reference/interview workloads, full identity dimensions and personality, formation/role adaptation, youth/rotation/recruitment tendencies, training transitions/familiarity, staff development/potential and contextual standing. AI opponent managers retain their prior policy. Coefficients and skill generation require calibration; this does not close the complete manager design.


## Starting selection milestone 0.19

Implemented owned-club starting formations responsive to eligible positional shortages, persistent rotation/youth selection preferences, current-readiness safeguards, configurable bounded scoring and a dated starting-selection report with actual natural-position counts. Reports survive substitutions, completed-match archiving and save/load. Schema 17 adds preferences/configuration only; old active matches preserve their outcomes.

Still open: granular tactical positions and roles, mid-match formation changes, expanded manager market and full personality/preference dimensions, squad familiarity/training transitions, opponent manager identities and realism calibration. Current preferred-shape defaults and selection coefficients are provisional. No manager or owner can bypass registration rules through this feature; academy players still require promotion.


## Tactical preparation milestone 0.20

Owned senior players now retain formation/style practice across manager transitions. Daily training uses available coaching, facilities, load and recovery; match minutes add bounded exposure once. A dated training report displays current preparation, evidence and attendance. New match snapshots supply one bounded passing-coordination pathway based on actual on-pitch players. Schema 18 migrates 1–17 without changing active matches, skills or existing preparation.

Verification includes training constraints, real coaching/resource differences, replacement and return to prior systems, on-pitch recalculation, saved-match equivalence, duplicate settlement/forfeit exclusion, unknown-history migration and read-only UI navigation. An actual published 0.19 minute-27 SQLite career resumes to an identical entire world after removing only the new preparation metadata. Source bytes are unchanged. Local regression, rendered report inspection, career/display and final Windows package evidence are recorded in the checkpoint and implementation PR.

Scope: tactical practice only; relationship/pairwise cohesion, alternative-system schedules, full AI manager identities/training and calibration remain open. No complete-cohesion claim, dependency change or predecessor merge.


## Contracts and Loans — Update 0.21

Implemented the remaining simple initial catalogue from GDD 0.10: fixed transfer release amount, player option, annual wage increase, relegation reduction, employment promotion bonus, appearance/promotion club payments and loan purchase options/conditional obligations. The transfer-right extension also implements dated buy-backs, first refusal on complete packages, funded player buy-outs and AI participation. Domain state, consent, controls, reservations, forecasts and schema-20 persistence are connected. Older saves gain empty bookkeeping/configuration only. No retroactive contracts or match changes.

Limitations: binding loans must settle inside the current window; AI option policy uses a simple appearance threshold and affordability; outgoing conditional fees replace guaranteed value at face value in the conservative initial buyer quote. Full risk-based valuation, player willingness/reputation, agent priorities, AI clause negotiation and national legal parity remain open. Real-world evidence and the implemented buy-back/first-refusal/buy-out scope are recorded in CONTRACT_RESEARCH.md; GDD revision 0.11 records the approved rules. A Spain buy-out mechanism profile is not a playable Spanish scenario or full legal parity.

Verification uses focused financial, consent, trigger, deadline, save and UI checks plus syntax/import checks. The final Windows/Linux regression and packaged build are publication gates; actual run evidence belongs in the PR. Jordan handles gameplay/UI feel testing.

### Update 0.25 evidence
Source-based player morale and current first-team summary implemented. Wider circumstances, academy/reserve summaries, general personality/relationship propagation, coordination/cohesion, calibration and Windows verification remain open. Profile reasons are keyboard/touch accessible. No full chapter 16 completion claimed.

### Update 0.26 evidence
Private senior-player meetings, persistent responses/cooldowns, sparse directed chairman relationship evidence and genuine fulfilment-based trust repair implemented. No inferred observers or universal teammate reaction. Relationship state informs support response; the source-based morale path carries its only current match effect. General relationships, staff/manager personality and relationships, succession participant identities, influence, factions/leaks, cohesion and final calibration remain open. No AA release, Windows executable or remote CI completion claimed.

Local combined 0.25/0.26 gate: 284 regression tests passed (626.062 seconds), with additional review-hook and live/skip/resume cases passing in the nine-case relationship run. Genuine 0.24 mid-match compatibility and original-save preservation checked. Two new screens visually inspected. Windows packaging and remote CI remain pending publication approval.

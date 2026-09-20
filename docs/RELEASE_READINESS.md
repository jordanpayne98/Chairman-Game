# Club Chairman release readiness

Implementation tracking against the **approved living GDD revision 0.3**. This is an engineering checklist, not a replacement design document, new design approval or a reduced release scope. The full AA game is **not release-ready**. No percentage-complete claim is made.

## Current presentation scope: Figma UI Update 0.9

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
| 12: contracts | Free-agent and own-player negotiations, counteroffers, expiry/cooldown, reserved capacity, medical review, atomic completion, renewal and expiry; club purchases/sales, deferred fees and senior loans with wage sharing, recall refunds and timed return; appearance/goal bonuses, a one-season club option, gross/profit sell-on rights and earned bonus payables | Release clauses, player options, conditional transfer/promotion bonuses, wage escalators/relegation reductions and loan purchase clauses, richer club/player negotiations, competition-specific eligibility, advanced loan restrictions and full transaction coverage |
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

1. Expand valid competition and season structures on the registration/staff/AI foundation; connect promotion/relegation and generated cups before scaling world content.
2. Add academy competitions and long-term population policy, while completing contract/loan clauses, staff capability effects and AI financial parity.
3. Connect career creation, ownership/group management, succession, group delegation, promises and commercial/asset obligations.
4. Complete UI/accessibility/content families and perform full-world simulation, performance, exploit, usability and release gates.

All rows remain part of the approved game. A working screen or one passing test does not close an entire row.

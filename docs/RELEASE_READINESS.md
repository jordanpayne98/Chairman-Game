# Club Chairman release readiness

Implementation tracking against the **approved living GDD revision 0.3**. This is an engineering checklist, not a replacement design document, new design approval or a reduced release scope. The full AA game is **not release-ready**. No percentage-complete claim is made.

## Current playable scope: Career Update 0.3

A compact eight-club league continues across seasons, with fourteen weekly rounds and a two-week preseason. This development calendar is not the approved full international football world. Original 0.1/0.2 saves migrate without replacing their source. Their existing contracts retain their actual end dates: review renewals before progressing beyond those dates.

| GDD area | Working coverage | Required before calling the AA game complete |
|---|---|---|
| 1–3: experience, setup, time | Owner-led game, paused management, daily Continue, decision stops, repeatable compact seasons | Club creation/acquisition setup, configurable active nations/detail, full event calendar and decision queue |
| 4–5: owner and group | Finite owner cash separate from club funds | Owner creation, personality, aging/retirement/succession, shares, due diligence, acquisitions and group authority |
| 6–8: world and competitions | Eight fictional clubs, league table, persistent fixture history | Approved 14-nation / 38-division / 636-club content, history, promotion/relegation, domestic/continental cups, supporting nations and internationals |
| 9–11: people and knowledge | Four prototype attributes, uncertain delayed reports, hidden-data-safe filtering/comparison | Full attribute catalogue and role models, dynamic potential, richer scouting, staff knowledge and discovery |
| 12: contracts | Free-agent and own-player negotiations, counteroffers, expiry/cooldown, reserved capacity, medical review, atomic completion, renewal and expiry | Club-to-club transfers, loans, complete clause catalogue, agents/registration rules and full transaction coverage. Legacy fixed-price signing shortcut still exists in this development build |
| 13: academy | Persistent annual trial cohort, individual admissions, wages, promotion from 16, periodic training estimates | Full youth/reserve squads and competitions, regional pools, plans, loans, mature development model and population balance |
| 14–16: staff and authority | Three manager candidates, renewal/replacement/notice exposure, trust and bench response | Role catalogue, interviews, complex agreements/promises, capacity, delegation presets, autonomy and sparse relationship systems |
| 17: football | Deterministic possession/chance simulation, live/skip equivalence, commentary, lineups, stored reports | Full football rules, substitutions, cards, injuries/recovery, extra time/penalties, richer tactical reasoning and calibrated outcomes |
| 18: finance | Integer-pence ledger, cash/payroll/reservations, owner equity, forecast with timing/expiry/opening costs | Complete accrual accounts, debt/investments, taxes/regulation, insolvency and AI financial parity |
| 19: commercial | Tickets/attendance and baseline sponsor income | Negotiated sponsorship inventory, rights, segments, season tickets, merchandise and marketing |
| 20: facilities | Training/academy/stand proposals, fixed-price construction, timed closure/opening, capacity/upkeep effects | Full stand/asset records, land/leases, permission/tender/inspection, staged payments, risks/change orders, new ground and rights consistency |
| 21: dialogue | State-driven contract transcript and factual event inbox | All approved scenario families, voice variations, promises, condition validation and localisation keys |
| 22–24: interface | Executive shell, dashboard, comparisons, contracts, academy, facilities, history, hints and keyboard help | Complete departmental screens, profile side panels, responsive text scaling, global search and consistent validation/denial coverage |
| 25–26: data and saves | Snapshot tuning, JSON inside atomic SQLite, checksum verification, backups and migrations 1→2→3 | Pack import/conflict tooling, approved mod formats, full normalised/indexed event storage and world-scale performance |
| 27–31: delivery and content | Playable versioned milestones and this evidence register | Full staged gates, complete production database/assets/dialogue manifest, historical retention and population datasets |
| 32: usability/accessibility | Keyboard actions, F2 explanations, safe modal focus, help and reduced motion | Guided onboarding, 100/125/150/175% text-scale workflows, remapping/conflicts, contrast audit and representative playtests |
| 33: presentation | Original deterministic crests/portraits/stadium diagram, goal emphasis, construction indicator, optional synthesised cues | Finished art direction/assets throughout, kits/competition/milestone art, complete volume controls/ambience, localisation architecture and editorial pass |
| 34–35: release | Targeted tests, real previous-build save migration, Windows packaging workflow | Ten 50-season full-world runs, performance profile at years 1/10/50, exploit suites, clean offline install and all release gates |
| 37–39: system/UI QoL | Shortlist/notes/pins, estimates/cost comparisons, forecast, history memory, offer drafts, unread distinction and tooltips | Named lists/scenarios, advanced tables, safe bulk operations, notification policies, saved layouts, calendars, complete recovery browser and all QAT workflows |

## Evidence for this milestone

- Automated domain and Pygame input tests cover multiple seasons, duplicate settlement/commands, financial reservations, expiry, notice payments, academy admission/promotion, construction opening, navigation, notes and keyboard explanations.
- A save was generated with the actual 0.2 source, loaded by 0.3 mid-match and resumed: cash, ledger, table and complete fixture results matched the original source exactly; the original save file remained byte-identical.
- New screens were rendered and inspected; this is not a substitute for physical Windows playtesting or representative usability studies.
- The packaged self-test exercises two seasons / 112 fixtures with negotiations, reserved capacity, academy, an operational facility, manager replacement and save/resume.
- The implementation PR records the exact Windows/Linux CI run and downloadable artifact after the checks complete.

## Next dependency sequence

1. Replace remaining prototype shortcuts with one consistent contract/registration model; implement full player/staff definitions and AI finances/authority.
2. Expand the valid world and competition calendar, then promotion/cups, academy competitions and population policy.
3. Connect career creation, ownership/group management, succession, delegation, promises and commercial/asset obligations.
4. Complete UI/accessibility/content families and perform full-world simulation, performance, exploit, usability and release gates.

All rows remain part of the approved game. A working screen or one passing test does not close an entire row.

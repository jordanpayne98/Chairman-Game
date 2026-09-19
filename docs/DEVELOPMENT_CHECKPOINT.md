# Development checkpoint

## PLAY-001 — First Season playable preview

Date: 2026-09-19. Design references: current living GDD revision 0.3 chapters 3, 11–12, 14–19, 23–27 and 37–38. Reviewed current design excerpts and the approved overview/player visual references. The older attached revision 0.2 does not supersede revision 0.3. No GDD changes or scope removals were made.

Implemented: one owned fictional club, three manager candidates, 156 players, eight-club home/away season, manager selection and tactical risk, delayed scouting, fixed-term free-agent signings, wage limits, ticket prices and attendance, finite owner funding, accrued payroll, sponsorship, financial ledger, spending decisions, bench encouragement/request with possible refusal, text matches, table and final prize settlement. Playable through season end. All tuning data is provisional playtest content, not a newly approved design baseline.

Interface: main menu, load/recovery browser, Executive overview, inbox, squad/player profiles, staff, recruitment/search, finances/ledger, league/fixtures, live text match view and help. Collapsible sidebar, persistent top bar, confirmation dialogs, focus traversal, pagination and scaled window. UI renders authorised read models; hidden player attributes and simulation RNG are absent from those views. Dark charcoal/green direction follows the approved reference; bespoke art and typography are not complete.

Persistence: SQLite schema 1 contains JSON world state plus metadata checksum. Atomic replacement verifies the new database and preserves a validated previous manual/auto backup. Three autosave slots, manual save and separate recovery timeline. Saves include command receipts, content snapshot and in-progress match RNG. No pickle. Normalised per-entity/indexed event storage and migrations beyond schema 1 remain future architecture work.

Verification performed locally: eleven automated tests cover connected UI hiring/scouting/signing/match/save/load, a complete season, duplicate/stale commands, atomic failure, uncertainty, ledger reconciliation, owner funding, mandatory decisions, live-versus-skip saved-resume equality, autosave rotation and failed-write/corrupt-save recovery. The integrated career smoke completes hiring, scouting, signing, bench intervention, mid-match save/reload and all 56 league fixtures. Headless UI screenshots inspected for overview, recruitment, staff, finances, league, matchday, help and confirmation. Linux source checks pass. Initial Windows CI exposed that fsync requires a writable file handle on Windows; corrected the temporary-save open mode to r+b. Windows CI and packaged executable results must be read from the implementation PR rather than assumed from this file.

Review follow-up: diagnostic SQLite handles were already fixed; replaced removable diagnostic assertions with explicit runtime errors so Python optimisation cannot bypass checks.

Known limitations: one-season end point, no promotion/cups/academy/aging; four prototype attributes; fixed free-agent signing terms; manager hiring cannot be undone/replaced in this build; simplified manager delegation and match engine; no cards/injuries/substitutions/stoppage-time; no audio or authentic club artwork; no normalised save migrations; no full settings/accessibility system. Financial presentation covers cash and payroll rather than full accrual accounts and regulation. Neither the full Foundation acceptance gate nor the complete Ownership/Season milestone is claimed complete.

Next: use playtest feedback to improve the connected loop; expand manager contracts/replacement and recruitment negotiation; then deepen football rules and season continuity. Preserve all approved long-term scope. Do not restart project setup.

## Earlier setup

PR #1 added project instructions. PR #2 introduced the repeatable Python/Pygame environment and passed headless graphics/events/SQLite checks on Windows and Linux after fixing database-handle cleanup. Both were merged before PLAY-001 work.

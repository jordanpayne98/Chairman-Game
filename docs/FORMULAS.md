# Simulation engineering parameters

Version 0.8. These are inspectable implementation details for the fictional compact league, **not a replacement GDD or approval of new full-world rules**. Approved catalogue, potential bands and striker weights follow living GDD revision 0.3 chapters 9–11 and 17. Other weights, rates and league settings are provisional calibration data stored in each career's configuration.

## Ability and knowledge

All 37 football attributes have internal decimal precision, bounded 1–100. `goalkeeping` is a retained legacy compatibility field, not a 38th displayed attribute. Overall is the rounded position-weighted mean; condition and morale do not alter this stored ability summary.

| Position | Weights (sum = 1) |
|---|---|
| Forward, approved striker baseline | Finishing .20, off the ball .15, composure .10, anticipation .10, acceleration .10, first touch .10, heading .08, pace .07, strength .05, decisions .05 |
| Defender, provisional | Tackling .20, marking .18, positioning .15, anticipation .10, heading .10, strength .08, concentration .07, pace .05, passing .04, decisions .03 |
| Midfielder, provisional | Passing .22, vision .15, decisions .13, first touch .12, technique .10, teamwork .08, stamina .07, positioning .05, tackling .04, work rate .04 |
| Goalkeeper, provisional | Reflexes .23, handling .20, one on ones .15, aerial command .12, positioning .10, communication .07, distribution .05, agility .05, rushing out .03 |

Initial coded potential samples uniformly once: −6 = 60–75, −7 = 70–85, −8 = 80–90, −9 = 85–95, −10 = 90–99. Generated values below current overall are corrected to overall; validation rejects subsequently invalid states. The fictional starter database uses −7 for youth, −6 for under-24 seniors and a small age-limited headroom above current overall for older seniors. Sampling frequencies and mature-player policy remain provisional. Reloads, reports and plan changes cannot reroll potential.

A report stores a dated noisy estimate with bounded ranges. Potential uncertainty is wider for youth. Monthly aging widens stored evidence using public age and elapsed time; it never refreshes against hidden truth. The own-club coaching report refreshes every 28 days. Old four-attribute reports remain incomplete until a new assessment. Full observer competence, evidence correlation, regional knowledge and discovery remain open.

## Development and recovery

Weekly growth uses base .30 × age factor × remaining headroom × training load × professionalism × minutes exposure × coaching facility factor. Age factor is clamped (29 − age)/10 in [0, 1.4], headroom is clamped (potential − overall)/20 in [0, 1], minutes exposure is .65 + .35 × min(1, weekly minutes/90), and facility factor is 1 + .06 × training level. Light/normal/intense loads multiply by .6/1/1.25. Growth follows the selected attribute group or all groups for Balanced. Intense load adds fatigue; injured players do not gain training growth. Physical decline starts above age 30 at .012 × (age − 30) per week.

Daily condition recovery is 4 + .05 × natural fitness, with +2 for light load or −2 for intense load; injury reduces it to 45%. Fatigue recovers separately. Medical records expose estimated dates and rehabilitation/conditioning stages, not a guaranteed true recovery date. External-player fitness/medical records are not exposed without assessment.

Quarterly reviews need at least ten weekly observations, 450 minutes, measured development and sufficient professionalism. Under-24 positive revisions are capped at one per quarter and three in a rolling year. Current implementation makes no upward revisions at 24+; exceptional mature development, negative setback reviews, positional retraining and full staff capability effects remain unfinished. Hidden adaptability, consistency and ambition are stored for further work; their full approved behavioural effects are not claimed implemented.

## Match actions and competition

The engine stores a separate RNG stream, elapsed minutes, phase clock, possession zone, active players, bench, events and action statistics. Each minute resolves a representative possession action, not every real-world pass. Passing attempts use a bounded logistic comparison of relevant attributes. Effective attributes include condition, fatigue, sharpness and morale. Home advantage, player numbers, manager skill and tactical risk modify action execution separately from database ability.

Shot quality starts in .03–.21 for ordinary attempts, .05–.17 for crosses, and .76 for penalties, then adjusts for movement, positioning and risk. Goal probability adjusts shot-quality log odds by finishing versus goalkeeping. xG is the pre-finishing chance estimate, not a calibrated claim against real football data. Ratings reflect recorded passes, tackles, saves, goals, errors and fouls; victory itself grants no rating bonus.

Default representative-action rates: foul .18; caution given foul .19; straight red given foul .003; injury .003 before fatigue adjustment; penalty given final-third foul .045. Match condition cost is .19 × (1.25 − stamina/200). Manager changes respond to low condition and score state. Added time is 1–3 minutes in the first half and 2–5 in the second. Extra-time halves add one minute each. Shootout kicks are separate from match goals and bonus events.

Northshire rules: 25 senior places, under-21 exemption from that count, minimum age 16, at most 17 non-homegrown seniors, five incoming loans, eleven starters, nine bench places, five changes in three in-play windows. Half-time changes do not use a window. Five accumulated yellows cause a one-match ban; second yellow and direct red use one and three matches respectively. Loans cannot play against their parent. Employment and registration remain separate; list omission does not stop wages. Minimum seven available players; a single failure awards 0–3, and a double pre-match failure records 0–0. Abandonment preserves real goals and adds administrative goals to award the opponent at least a three-goal winning margin. These are configurable fictional league settings, not claims about any real competition's current regulations.

Remaining football scope includes richer formations/roles, complete restart and set-piece sequences, goalkeeper dismissal decisions, nuanced tactical explanations, workload/injury susceptibility calibration, suspension appeals and competition-specific discipline resets. Extra-time/shootout logic is tested but not yet reachable through a generated cup competition.

## Measured calibration sample

Source version 0.7, seeds 0–999, the first compact-league fixture, default rules and no appointed owner-club manager: 1,000 matches averaged 2.591 goals, 19.561 representative shots, 2.527 xG, 3.286 yellows, .329 dismissals, .271 injuries and 5.351 substitutions across both teams. Mean duration was 95.497 minutes; home/draw/away proportions were 42.2%/22.0%/35.8%. Goals per match ranged 0–9. This catches gross balance errors; it is not empirical validation, a full-season injury study or the approved ten 50-season full-world release gate.


## Staff, authority and rival clubs (0.8)

The nine departmental roles use ten capability fields from the approved staff model. The compact database contains 27 free candidates and three opening staff per rival club. Initial references use ±12-point ranges, interviews ±6, and own working observations ±3 around a stable noisy estimate. These are implementation tuning, not a claim of precise assessment. The original three-manager hiring desk remains separate.

Owner recruitment takes one day before interview, then two days to join from unemployment or seven days from another club. Employer compensation is four weeks of the old salary, transferred at binding acceptance. New salary is reserved immediately and enters actual payroll on the joining date. Contracts last one to three compact seasons. Notice is the lesser of four weeks' salary and remaining guaranteed salary; paid compensation is not refunded if the new appointment is later cancelled. Forecasts include joining and expiry dates. Actual staff salary is included in each club's existing payroll/accrual model.

Each responsibility consumes 25 of 100 capacity units, permitting at most four per employee. Fully allocated owner staff gain two workload points per week; otherwise workload falls by three, bounded 0–100. Relevant departmental capability is reduced by max(.7, 1 − workload/400). Training growth multiplies by 1 + (coaching capability − 50)/250. Scouting report radius multiplies by 1 − (assessment capability − 50)/150, rounded with a minimum radius of four. A medical lead adds operations capability/100 to daily condition recovery. Other capability effects, richer availability and personality behaviours remain incomplete.

Default delegated authority is £80,000 per department and £300,000 club-wide over a rolling 28 days, with a 365-day duration ceiling. Active conditional reservations remain counted until completed or released, even when older than the rolling period. Employment exposure includes signing/transfer fees and guaranteed wages, less remaining existing base wages for renewals. Academy admission includes the fee and guaranteed salary. Project approval includes construction cost and 365 days of upkeep. Performance bonuses/options cannot be auto-authorised. Owner approval can grant a one-off authority exception but cannot bypass domain affordability, consent, medical or registration checks. Cases expire after seven days. These defaults are configurable saved tuning, not new GDD financial policy.

AI clubs review every seven days. Their wage ceiling is 90% of configured weekly operating income minus configured overheads. Cash cover is three weeks of existing payroll/overheads plus pending wages, alongside all scheduled transfer bills and reserved fees. Appointments and renewals check these same commitments; owner-originated outgoing player deals also enforce the receiving club's limits. Target/max senior squad sizes are 19/20. Player selection uses persisted noisy overall estimates, public role, salary and fee; observation uncertainty depends on assessment staff and refreshes after 28 days. Conditional AI registrations take two days and have an 8% seeded medical-withdrawal chance. Final completion rechecks eligibility and financial commitments, transfers the actual fee, settles sell-on rights, pays signing costs and changes employment/registration. No extra funds are injected to make a transfer succeed.

Rival finances still use the provisional aggregate weekly income introduced in 0.5. Full supporter/commercial economics, complex AI negotiations, manager/staff parity and financially complete long-term population policy are future work. The compact implementation is not the full-world economic or 50-season release gate.


## Domestic cup milestone 0.10

GDD chapters 3, 7, 17, 26–27 and QA02–04/10 guide this implementation. Development data in `world.json.cup` reserves season-relative days 22, 50 and 78 with minimum three-day rest from league dates. These compact-season dates are provisional and do not replace the approved August–May world calendar. Draws use an isolated seed keyed by competition, season and round; sorting entrant IDs first makes JSON ordering irrelevant. Each round is drawn only after its predecessor settles.

For N entrants, opening byes = 2^ceil(log2(N)) - N. All other clubs play once. Winners plus byes enter the next round; the engine handles regulation, extra time and shootouts. Shootout kicks never count as match goals. If both clubs cannot field seven players, an explicit seeded administrative draw advances one at 0–0 without played appearances or bonuses; single failures use the inherited 3–0 award. No automatic replacement players are created for a tie.

Cup results do not post league points, goal difference or league form. Player seasonal totals currently aggregate league and cup; per-competition player breakdowns remain future work. Registration lists, loan-parent restrictions and disciplinary accumulators are shared domestic rules at this stage. There is no cup-tied eligibility rule in this provisional database. Owner home gates use the existing ticket/usable-capacity calculation; rival finances retain their aggregate-income limitation. The configured winner prize is zero, so trophy completion creates no invented payment. Non-zero configured prizes use the winning entity's idempotent ledger posting.

Schema 8 adds the competition graph. Schema 1–7 migration leaves the current season's fixtures and RNG unchanged; the first cup is created on the next rollover. Season history retains the graph and trophy; unresolved future cup rounds prevent season completion. Promotion/relegation, multiple leagues and full calendar solving remain outstanding.


## Divisions milestone 0.11

- Development world: two divisions × eight clubs; each ordered pair plays once (56 league fixtures per division). All 16 clubs enter the cup (15 ties). League rounds remain days 5 + 7r; cup dates 22/43/64/85 maintain three days of recovery. Original player/free-agent IDs remain stable; lower-division players use new persistent person IDs.
- Sporting order: points, goal difference, goals scored, head-to-head points among the tied group, recorded seeded draw order. Cup results never affect league statistics. Legacy seasons retain their original ID tie-break until rollover.
- At complete season closure, freeze final tables and bottom-three/top-three exchange records. Pay each club its division/position award exactly once. Owner postings retain historical IDs. Rival awards use season/division/club IDs. Championship awards default to 50% of the existing Premier schedule; other AI income is still provisional aggregate income.
- At next-season commit, archive both tables and movements, exchange exactly six memberships, reset seasonal statistics and generate schedules from new membership. No players, signed obligations, bank balances or staff are moved between clubs by promotion/relegation. Preseason time still advances normally.
- Expansion names, initial lower-club ability range, exchange count, cup dates and prize multiplier are snapshotted from `data/leagues.json` at creation/legacy expansion. Existing seasons and frozen content are never overwritten on load. This is development tuning, not the full national content database.


## National calendars milestone 0.12

- `data/nations.json` validates the approved 14-nation / 38-division / 636-senior-club inventory. England (5×20), Wales (2×12), and Brazil (3×18) are isolated playable development scenarios; remaining nations are format definitions only. The manifest lists incomplete content and is not release-ready. USA is closed with a top-eight playoff requirement and is not selectable until implemented.
- One national rules snapshot is stored in the career config. Start anchors are 1 August or 1 February; season boundaries are 31 May or 30 November. The next anchor is the same month/day in the following year, including leap years. Domestic cups reserve their final on the season boundary. Earlier rounds select the closest unblocked Wednesday to evenly spaced seasonal targets. League rounds select evenly spaced unblocked Saturdays, at least three days from every cup slot and one another. Conflicts reject the plan before fixtures commit. Blackouts are relative to the season anchor and currently empty; international scheduling is not claimed.
- All primary divisions in one scenario have the same size; supporting pools may be smaller. A double round robin produces N×(N−1) fixtures per division; a knockout cup produces club_count−1 ties with byes. League fixtures, saved reservations, membership, calendar year and all cup dates validate together. Draw RNG/fixture IDs keep their existing stable keys.
- New annual contracts end at the configured boundary in the requested season; renewals negotiated after closure cover the next campaign. One-year options add one calendar year to the agreed end, clamping leap-day only when necessary. Existing signed options keep their recorded end. New rival replacement contracts reach the national season end, avoiding the old day-96 expiry. Compact save arithmetic is unchanged.
- National prize awards interpolate linearly from £150,000 to £10,000 across the table; each lower tier receives 70% of the preceding tier's schedule, with integer-pence truncation. This is provisional test tuning. Existing owner/AI finance models and GBP presentation remain. Initial senior squads contain 18 players plus 12 free agents across the world; no complete national population or reserve/youth database is implied.
- Weekly AI review caches release cover across the unchanged employment roster, cash/payroll within each club's review, and incoming eligibility by senior/minimum-age/homegrown traits. Pending bids, consents, observations and final registration checks retain the original paths. A reference-code comparison produced identical entire world state after a Wales review. Initial England review measured 133.113s before and 4.937s after on this runtime; illustrative measurements, not a shipped minimum-hardware guarantee.


## Feeder pools milestone 0.14

- New national careers add eight persistent supporting clubs below the lowest primary division. England exchanges three; Wales and Brazil exchange two. Club/person IDs, staff, signed obligations, accounts and observed history stay attached to the same entities. Pools initially use the existing detailed simulation, so promoted entrants already have full match data before scheduling. Reduced-detail transitions remain unimplemented.
- A pool plays 14 rounds. Round r selects national league date round(r × (available_rounds − 1) / 13), including first and last league dates. These are already reserved away from cup dates. Each ordered club pair plays once; no extra match RNG stream is introduced. All division membership and fixture checks apply to the pool.
- Only primary members enter the primary cup. The membership snapshot changes at next-season commit after exchanges; cup results from the completed season remain archived. An owner relegated to the pool stays detailed and playable, with no primary-cup entry until promoted back. There is no further relegation below the pool.
- `data/feeders.json` supplies explicit fictional identities in real cities, an initial ability range of 35–55, 18 players and three staff per club. The eight-club pool and these populations are provisional content. Pool prizes sample the lowest primary tier’s award curve across eight positions and apply 70%, truncating integer pence. Existing GBP/aggregate rival income limitations remain.
- Schema 12 migration changes only the schema marker for schema 11 careers: no clubs, fixtures, cash, obligations or RNG are added or replaced on load or later rollover. New pool definitions are snapshotted in the career and validated against persistent identities, division links and account existence. Compact careers retain their existing format.


## Background reviews milestone 0.15

- Every club has a saved `detailed` or `reduced` review level. Only non-owned supporting-pool members become reduced; all primary members and c0 remain detailed. This first stage changes routine AI review scheduling only. Match simulation, recovery, training, dated transactions and financial accrual retain their existing paths.
- On each existing weekly AI tick, a reduced club reviews when at least 28 days have passed since its last review, or an urgency predicate holds: preseason/registration is open, fewer than 2 GK/6 DEF/6 MID/4 FWD remain, fewer than seven players are free of injury/bans, an Executive/Football director/Coaching vacancy exists, a player/staff contract expires within 28 days, or a scheduled outgoing transfer bill falls due within 28 days. Due medical decisions are handled before this filter every day, preserving completion/cancellation timing. Review still observes existing affordability, consent and registration rules.
- `data/detail.json` is copied into career configuration. Validate the routine interval as an integer multiple of the weekly interval and the urgent horizon as at least one interval. Defaults are development tuning. A quiet 84-day fixture produces three reduced finance reviews versus twelve detailed reviews; this measures review count, not runtime performance or full-world readiness.
- Membership changes update levels before schedule generation. The transition records club, old/new level, day and season; repeated synchronization is idempotent. No people, contracts, accounts, history or scouting reports are replaced. All supporting records already exist at this stage; missing-record expansion and acquisition are not implemented.
- Schema 13 migration adds only configuration/detail metadata and changes the schema marker. Existing seasons remain fully detailed until their next season preparation. Completed season detail levels are archived with the competition state. Older schema 12 executables cannot read schema 13 saves.


## Current ability milestone 0.16

- Owned players and explicitly completed paid scouting assignments permit live current attributes and position-weighted CA. Display rounding is floor(value + 0.5); CA retains the existing unrounded-attribute weighted calculation. Pair-shaped read-model fields use [value, value] for compatibility; the UI prints a single number.
- Potential remains the stored observer estimate. Knowledge completion is distinct from forecast confidence. Hidden personality, actual potential and simulation RNG remain private.
- `people.full_coverage_days` defaults to 28 (provisional calibration). Coverage is active for day < report.coverage_until. Expired reports use only frozen evidence with the existing age-dependent widening, at least one point. Hired players retain exact ratings even when their potential forecast is stale; external legacy evidence is never retroactively promoted to full coverage.
- Reads never rewrite report snapshots. Current values use current-day access; report day continues to date the potential forecast. Existing one-report-per-person storage remains; a browsable archive and richer evidence accumulation remain open.
- Schema 14 adds only the coverage configuration during migration from 13. No player, finance, match or RNG record changes. Source SQLite bytes remain untouched.


## Staff ability milestone 0.17

Departmental staff have eleven visible capabilities; Adaptability is sampled once from 25–85 using the independent `staff-adaptability:<id>` identity stream. This is provisional fictional population tuning. Existing ten-capability generation consumes the same original stream draws, preserving skills, quoted wages and risk preferences. Migration adds missing values without rerolling existing ones.

Departmental CA = floor(sum(capability × role weight) + 0.5). Initial weights split .5/.5 across each role's existing two core skills in staff.ROLES; stored `config.staff.weights` permits calibration, requires nonnegative finite weights summing to one, and includes zero implicit weight for other capabilities. Current capability display uses floor(value + 0.5). CA is absolute for the stated role, independent of employer, wages, reputation and workload. No manager role is introduced here; its positive Adaptability weight remains pending alongside manager integration.

Initial contact records a partial reference assessment. Completing the interview records Fully assessed and a frozen exact-current snapshot with coverage_until = day + config.staff.full_coverage_days (default 28, provisional). While day < coverage_until, current read models use exact live skills. Club employees always have exact access. Expired external snapshots widen one point per coverage interval, at least one and at most twenty, without consulting current truth. All ranges clamp to 1–100; CA ranges derive only from available assessed core skills. Legacy missing fields remain unknown. Reading never rewrites a stored report.

Schema 15 migrates schemas 1–14 by adding only staff coverage/weight configuration and missing Adaptability. Existing reports stay partial, signed money and dates stay intact, and match RNG is unchanged. Role authority and automatic work retain their existing mechanics; the owner-facing coverage suggestion now uses exact employee skills through authorised views. Staff future development, potential, manager conversion and contextual importance remain unimplemented.


## Update 0.18 manager ability and tactical instructions

Manager CA uses tactical judgement .30, coaching .20, people management .15, ability assessment .10, youth development .05 and Adaptability .20. Other capabilities have zero weight for this summary. Use the existing absolute staff rounding and knowledge rules. Weights are configurable, nonnegative and sum to one; Adaptability must remain positive. Eleven capabilities are generated once from an independent `manager-capabilities:<id>` stream: legacy skill plus an integer -18…18, clamped 1–100. Legacy skill remains compatibility data, not displayed CA.

Each new owned-club match snapshots capability, preferred risk and tuning. Preferred risk remains 1.12 attacking, 1.00 balanced or .92 cautious. At existing manager-review stoppages, tactical judgement at least 40 permits assessment. A numerical disadvantage takes priority and targets .85. From minute 65, a deficit targets 1.22, a lead .90 and level scores the preferred risk. Coordinated instruction = preferred risk + (target - preferred risk) × Adaptability / 100, rounded to six places. Apply and log only changes at least .015; an accepted owner intervention retains priority. Encouragement and refusal do not freeze future adjustments. These are provisional coefficients, not validated calibration or inferred personality. No formation switch, tactical-familiarity transition or outcome guarantee is implied.

Risk uses the existing shot frequency and defensive exposure pathways. New matches omit the legacy `(manager skill - 62) × .12` generic passing advantage; no CA or administrative-skill bonus replaces it. Saves without a match-plan snapshot use the original match rules through that match. Migration never inserts a plan into an active match or changes its RNG. AI opponents retain their prior tactical policy in this milestone. Manager identities/preferences are retained separately from dated assessments and observed match events.

Manager assessment currently completes immediately at no cost, with the staff coverage period (28 days by default). This is a provisional compact interaction, not a complete interview workload or personality assessment. Appointments still validate budget, reserved commitments, cash, notice and matchday restrictions.


## Update 0.19 starting selection and shape

Eligibility uses the existing registration/medical/discipline rules before any scoring. Readiness score = position-weighted current ability × (.45 + .55 × condition / 100) − fatigue × .12. Fresh legs additionally subtracts fatigue × .15. Continuity adds 2 for starting the most recent completed current-season fixture within 14 days. Develop prospects adds up to 3 × youth-development / 100 for players aged at most 21 whose current ability is within 5 points of the best eligible player in their own broad position. No potential, reputation or wage term enters selection. These coefficients are configurable provisional tuning, capped by validation.

Rotation choices (Balanced, Fresh legs, Continuity) and youth choices (Readiness first, Develop prospects) persist from an independent manager-selection identity stream. New preferred shapes are Balanced 4-4-2, Attacking 4-3-3 and Cautious 4-5-1. Migration does not rewrite any existing preferred shape, capability, risk instruction, assessment or active match.

The four shape definitions specify DEF/MID/FWD counts; one GK is requested separately. Preferred shapes with enough outfield cover are retained. If short, tactical judgement at least the configured 40 and Adaptability at least 50 permit choosing the shape with the fewest missing natural-position places, only when strictly better. Ties prefer the original shape then the definition order. This represents broad starting personnel shape, not detailed positional roles or tactical familiarity. Missing places use eligible outfield cover before extra goalkeepers; the report displays actual natural-position counts and warns when fewer than eleven players or no goalkeeper are available.

Within each position, score descending then player ID selects starters. Remaining bench choices retain the existing goalkeeper-first coverage rule, then selection score and ID. These choices affect which players enter the existing football engine; no formation or preference bonus is added to action probabilities. Starting-plan records own separate copies of starter/bench IDs, so live substitutions cannot mutate history. AI opponents retain their existing selection policy. In-progress legacy matches have no retroactive selection record.


## Tactical preparation — Update 0.20

Separate per-player records key learning by formation plus manager style. New and migrated records start absent (Not assessed); unrecorded preparation supplies zero added edge, not a penalty. No past training is reconstructed. Appointments record a dated brief without resetting records, modifying attributes or granting preparation. Memory is retained without decay in this first pathway.

Once per advancing day, after medical/recovery processing, the owned senior squad trains unless there is an owned-club fixture that day. Retired/youth players are excluded; injured players, condition below 65 or fatigue above 70 miss the session. No learning is backfilled for missed days or newly joined players. A return to an earlier system retains its prior record.

Daily gain = 0.8 × (0.5 + teaching) × (1 + .04 × min(5, training facility level)) × load × condition/100 × (1 − fatigue/100) × (1 − preparation/100). Teaching = (manager Coaching + workload-adjusted active departmental Coaching)/200; no departmental employee contributes zero, leaving the manager to teach. Existing staff workload adjusts the departmental capability. Light load uses .5; normal and intense use 1, while their existing recovery/fatigue effects remain. Gains are capped at 100, rounded to six decimals. No attribute or potential bonus is added.

New owned-club match snapshots record every starter and bench player's preparation in the actual selected formation/style. The passing-action edge is the mean of current on-pitch recorded values /100 × 2, subtracting the opposing side's equivalent once. This is recomputed after substitutions/dismissals and is not applied again to finishing, selection, morale or a squad dashboard total. Missing histories and the unchanged AI training baseline contribute zero. Snapshots and maximum effect are frozen for save/resume; public reports contain only owned-player learned records. Old matches without a snapshot receive zero additional edge and no retrospective learning.

Once a fixture is settled, actual participants receive 1.2 × min(90, played minutes)/90 × (1 − preparation/100) in its snapshotted system. Unused substitutes and forfeits earn nothing. Extra-time exposure is capped; shootouts add no training minutes. Fixture settlement guards prevent duplicate credit. Configuration stores daily gain, match gain, maximum edge and light-load factor; bounds are validated. All coefficients and the asymmetric owned-club pathway are provisional, not a calibrated claim about football. Pairwise cohesion, relationship evidence, alternative training schedules and wider AI training remain pending.

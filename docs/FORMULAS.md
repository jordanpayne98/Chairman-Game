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

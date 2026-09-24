# Shared English league details — CONTENT-045

Implementation record for GDD 0.19, updated 24 September 2026. This is not a new design document or a completed playable rulebook. Five shared profiles feed all 38 national divisions. Source verification, recorded rule definitions and executable behaviour are separate gates. Club licensing and separate destination admission gates are removed from the active model. National employment, registration, financial rules and calendars remain separate.

## Current evidence

| Profile | Added to definitions | Remaining source or interpretation gaps |
|---|---|---|
| Tier 1 | Withdrawal and vacancy consequences; curtailed-season ranking and decision requirements | Broader disciplinary/administrative exceptions and recorded decision execution |
| Tiers 2–4 | Full published table-order sequence; ordinary access; current playoff pairings; cessation timing and relegation cascades | Separate current playoff match rules, final venue, Championship semifinal hosting, regular-season fixture obligation, narrow table interpretations |
| Tier 5 | Mandatory FA table-order sequence; four relegations and Step 2 feeder access | National League inserted provisions and current playoff appendix; feeder draw adjustments/geography and reserve eligibility |

All five profiles remain PARTIAL. Table ordering, exception policies and descriptive playoff stages added here are **definitions, not an executed season service**. No brackets with guessed deciders were activated. Opening memberships, national scheduling, background feeder resolution and career integration remain gated.

## CONTENT-046 — completed standings and access preview

`club_chairman/shared_standings.py` now resolves a completed 20/24-club, home-and-away season from match results. It applies recorded points deductions, points/goal criteria, conditional Premier League head-to-head tests, EFL head-to-head and later wins/away goals, and the FA standardised wins criterion. The output preserves groups sharing a rank and names every unresolved decision. An optional recorded adjudication supplies an exact order with a decision ID and basis; it cannot change a decided result or unrelated tie. The function never silently sorts tied clubs by ID.

`shared_access_preview` identifies automatic promotion and relegation **candidates** and ordered EFL playoff seeds only when the decisive places resolve. It blocks ties crossing an access boundary or leaving playoff seeds unknown. The tier-5 playoff remains pending the operative National League appendix. These operations are standalone validations: eligibility, disciplinary evidence past the sourced criteria, withdrawal decisions, actual playoff match rules and career scheduling remain separate.

Focused tests exercise all 38 instantiated tiers, full fixture reconciliation, a title decided by the published head-to-head away-goal criterion, deductions, unresolved ties, explicit adjudication, access-boundary refusal and stable ordering. No synthetic season or club was written into production data.

## CONTENT-047 — discipline, calendar validation and ordinary exchange

The table resolver now accepts a separately evidenced EFL regulation 9.4 assessment for each still-tied club. It requires 42 matches assessed, a nonnegative penalty-point total and an assessment decision ID. It ranks the lower total first. If evidence is absent, a supplied generic ordering cannot bypass the published disciplinary criterion. A tie remaining after this stage still needs regulation 9.7 interpretation or an actual deciding-match/association decision. The service does not fabricate card events or decide the unclear sending-off assessment period.

`shared_calendar.py` accepts a nation-authored plan and checks 38/46 complete round dates against its stated season window, blocked cup/international dates and minimum rest. Its tests use clearly synthetic dates; it does not generate or validate the *authority* of the national dates. `shared_exchange.py` takes completed results, resolved playoff outcomes, eligible named background entrants and membership lists, then settles the ordinary pyramid in one identity-preserving transaction. It refuses missing outcomes, boundary ties, ineligible or duplicate feeder clubs and unbalanced movements. A recorded fifth-tier playoff winner must hold an individually resolved rank of 2–7; no association admission approval is requested. The current National League bracket still needs its operative rules and real match outcomes. Withdrawal and genuine sporting vacancy exceptions need separate decisions.

**Production gate after CONTENT-047:** 38/38 active divisions have no dated national calendar, no first-season members, no activated playoff bracket and a pending feeder status. That overlaps the explicitly later opening-world population pass: conditional league services can be tested before those memberships exist, but neither Pass 1 production activation nor Batch 3 completion follows from the synthetic tests. The current EFL play-off document page exposes no operative 2026/27 match-resolution file; its HTML contains a hidden documentation widget without a usable current rule attachment. The football National League appendix is likewise not retrieved in its operative 2026/27 edition. An unrelated US youth league using the same name was excluded. The current EFL master regulations establish the bracket pairing and the League's scheduling/discretionary powers, but not every playoff decider.

## Rules requiring care in implementation

- EFL table ties continue past head-to-head records to wins, away goals and disciplinary criteria. Regulation 9.4 explicitly says **42** league matches; the data preserves that text rather than changing it to 46. The scope of the subsequent sending-off count and treatment of a partially separated head-to-head group need an explicit interpretation before execution. Successful wrongful-dismissal claims affect the disciplinary calculation.
- Championship semifinal opponents are reseeded by final league position after both quarterfinals. An upset does not retain the defeated club's seed. League One and League Two use fixed semifinal pairings; the higher club normally hosts the return leg, subject to Board agreement.
- EFL cessation rules distinguish departure during the regular season, after it but before playoffs finish, and after playoffs finish. Results, affected relegation season and cascading vacancies differ. Additional admissions/restoring divisional sizes require Board action; no arbitrary replacement club may be generated.
- The sourced English tier 4/5 admission procedure is research context only. The approved fictional league moves clubs through recorded sporting results without a club licensing or admission decision. Reserve restrictions and genuine sporting vacancies still need defined handling.
- FA standardised rules apply mandatorily to NLS Steps 1–6; approved additions and inserted league provisions must still be reconciled. Rule 12.2.4 names a two-club head-to-head comparison without spelling out numeric subcriteria. Do not substitute the EFL mini-table algorithm.
- Step 2 feeder playoffs and National League promotion playoffs are different competitions. The sourced feeder provision gives single-leg rounds at the higher club, excludes ineligible entrants without replacements, and lets the competition adjust the draw. It does not establish the tier-5-to-tier-4 bracket.
- Top-flight curtailment has its own ranking sequence. Ranking clubs does not itself authorize a promotion/relegation outcome. Board resolutions and discretionary reprieves must be recorded separately from calculated standings.

## Primary source register

The operative edition was checked in the downloaded text, not inferred from search-result crawl dates. Source records include checksums because the EFL master URL is mutable. Full publications are not copied into this repository.

- [EFL Regulations 2026/27](https://images.gc.eflservices.co.uk/EFL+Regulations+[MASTER+VERSION].pdf): regulations 5.1–5.2, 7–11; especially 9 (tables), 10 (access/playoffs), 11 (cessation). Membership application and stadium compliance have distinct deadlines, returnee provisions and appeal rights; they are not implemented as national licensing rules in this pass.
- [FA Handbook 2026/27](https://www.thefa.com/-/media/files/thefaportal/governance-docs/rules-of-the-association/2026-27/the-fa-handbook-2026-27.ashx): section 21 regulations 3.1 and 5.2; section 27 introduction and rules 12.1–12.7. The maximum Step 1 membership is 24; 24 is the approved game baseline, not a guarantee against vacancies.
- Premier League Handbook 2026/27, 31 July edition: source `ENG-PL-HANDBOOK-26` in production data, C1–C7, C14–C17 and C25–C30. Its full publication URL is preserved there.

The EFL site’s current play-off document page did not expose readable operative match rules. Retrieved 2023/24 and 2025/26 PDFs were excluded from current-rule certification. The National League’s public competition-rules page did not provide readable operative inserted rules during this pass. These specific retrieval gaps remain open; historical rules are not silently promoted to current evidence.

## GDD 0.19 implementation follow-up

The active shared profiles and 38 tier instances no longer contain a `licensing` or `promotion_eligibility` field. The active Welsh cup no longer checks a club licence, an association admission decision or a ground certificate at opening allocation. Its earlier nomination and cup application code remains isolated as superseded reference behavior; it is not a valid production career route. A sporting cup entrant still needs an explicit opening allocation and eligible competition membership. Venue and match scheduling must be resolved in the later cup pass without restoring a club licensing gate.

The tier-five ordinary exchange now accepts a recorded playoff winner ranked 2–7 without `association_approved`. It still rejects an unqualified or unresolved entrant and cannot invent the playoff fixtures. Genuine sporting vacancies, reserve restrictions, full first-season memberships, national dates and integration remain open.

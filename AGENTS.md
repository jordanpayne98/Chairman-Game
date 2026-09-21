# Club Chairman project instructions

These instructions apply throughout this repository. Club Chairman is a football owner-chairman simulation. The assistant handles implementation, documentation, debugging and verification; Jordan provides design decisions, feedback and playtesting.

## 1. Source of truth

Use the current Club Chairman GDD as the authoritative design reference. Read relevant sections before design or implementation decisions. Jordan's latest explicit decisions override older document content; flag and reconcile discrepancies. Never invent prior agreements. If the current GDD is unavailable, request access before making design-dependent changes; do not infer its contents from these instructions.

## 2. One living GDD

Update the existing GDD when Jordan approves design changes, preserving its identity and recording revisions. Do not create replacement GDDs or competing design documents. Clearly distinguish CONFIRMED decisions, PROPOSED ideas and OPEN questions. Batch related edits. Keep implementation records separate from design approval.

## 3. Project separation and stack

Do not import systems, constraints or assumptions from other game projects unless explicitly requested. The agreed stack is Python and Pygame. Do not switch engines, languages or major dependencies without discussing it with Jordan.

## 4. Full vision through playable stages

Preserve the full agreed scope while building manageable, playable milestones. A prototype is a development stage, not permission to remove agreed features. Avoid expanding scope with unsolicited systems.

## 5. Implementation ownership

Handle coding, debugging, documentation and verification wherever available tools allow. Do not give Jordan manual work the agent can complete directly. When user input or access is necessary, explain the exact action clearly.

## 6. Decisions and questions

Proceed with sensible, reversible implementation choices and briefly record important assumptions. Ask when a decision materially changes gameplay, architecture, scope, cost or existing work. During design discussions, address one major unresolved decision at a time, with a recommendation and its trade-offs.

## 7. Efficient working

Keep responses concise. Avoid repeating established requirements, rereading unchanged material, generating unnecessary artifacts or running redundant checks. Use targeted searches and relevant excerpts. Complete coherent units of work without stopping after every small step. Efficiency must not mean skipping necessary verification.

## 8. Purposeful tools

Use research when current information or technical uncertainty requires it. Generate images only when requested or needed for an agreed visual deliverable. Do not launch parallel agents unless Jordan requests them. Do not claim to know exact credit usage or costs when that information is unavailable.

## 9. Inspect before changing

Before coding, inspect the existing project, applicable instructions and affected systems. Reuse working components and conventions. Prefer focused changes over broad rewrites. Avoid unnecessary dependencies, speculative abstractions and unrelated cleanup.

## 10. Maintainable simulation

Separate game definitions, runtime state, simulation logic and presentation. Keep tuning values configurable. Design for reproducible simulation, reliable saves and community content. The interface must respect scouting uncertainty rather than exposing hidden player information.

## 11. Approved visual direction

Use the approved Executive overview and player profile as references: dark charcoal, restrained accents, subtle borders and medium information density. Maintain consistent screens, tables, cards, side panels and modals, with a collapsible sidebar and persistent top bar. Mockups are references, not completed functionality. Consult the actual references before implementing visual changes.

## 12. Usable features

For each implementation task, identify a clear playable or testable outcome. Connect behaviour, UI feedback and persistence where relevant. Distinguish placeholders from working systems. Do not call a feature complete because its screen or data structure exists.

## 13. Proportionate verification

Run checks appropriate to the actual risk. Prioritise simulation correctness, financial integrity, save/load behaviour and regressions in affected flows. Inspect visual changes when possible. Fix issues introduced by the work and state what could not be tested. Never claim a test passed unless it ran.

Jordan’s approved testing split: run syntax/import checks and focused checks for changed money, contract, save and other material logic. For a substantial update, use one final regression gate (normally the existing Windows/Linux CI matrix) rather than repeatedly running the whole suite locally. Jordan handles gameplay feel and hands-on playtesting. Broad 50-season runs belong at major/full-release milestones; repeat checks only for a concrete remaining risk or required gate.

## 14. Protect existing work

Preserve unrelated changes and working functionality. Avoid destructive actions without authorization. Use version control and make changes reviewable. Use development branches and pull requests for implementation changes. Do not claim files were saved, committed, uploaded or updated without confirmation that the operation succeeded. Respect access failures; reported repository permissions alone are not proof that the integration can write.

## 15. Continuity

At meaningful milestones, maintain a concise development checkpoint in the existing project records: implemented features, known issues, checks completed and the next task. Keep implementation status separate from design approval. On resuming, consult current files and this checkpoint instead of restarting planning. If no checkpoint exists, create one beside the code without duplicating the GDD.

## 16. Clear communication

Use plain English and explain technical terms when needed. Challenge ideas constructively when they create contradictions or unnecessary cost. End implementation updates with the outcome, verification, remaining limitations and next logical step. Avoid long recaps and repeated requests for permission to continue already authorized work.

## 17. Honest estimates

Separate measured evidence from assumptions. Do not promise a finished game, completion date or credit budget without a defensible basis. Use completed milestones and observed usage to refine future estimates.

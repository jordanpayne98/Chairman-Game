# Presentation asset register

## Original procedural content (0.3)

`club_chairman/presentation.py` draws eight distinct fictional club crests from original geometric templates and colour palettes. Portraits are original modular illustrations generated from stable person IDs; skin, hair and appearance do not use hidden abilities, potential or relationships. Stadium artwork is an original plan view with seats, pitch markings and a construction overlay. No real club branding, photographed likeness, downloaded artwork or AI-generated bitmap is included.

These assets are rendered at logical interface sizes and scale with the Pygame canvas. Identity survives save/load. They are development artwork; the final AA art-quality/content gate remains open.

Goal emphasis and the moving construction indicator are decorative presentation only. Reduced motion removes those effects. Neither artwork nor animation reads or advances the simulation random stream. A match highlight only follows an already committed score change.

Click, goal and notice sounds are original short sine-wave envelopes generated locally. They contain no external recordings. The current build exposes interface sound on/off; missing audio hardware gracefully disables playback. Full channel mixing, ambience, music and unfocused muting remain release work.

## Figma UI assets (0.9)

Source: the user’s approved Club Chairman file `Q0grGlgTJOhObKeOgWelbo`, exported 20 September 2026. `assets/figma/provenance.json` records the exact node IDs. Navigation icons and the Northbridge crest are unmodified PNG exports at 3x, loaded locally and scaled to explicit dimensions. Figma is not contacted at runtime. Other clubs keep the original procedural crests; the Figma sample opponents are not substituted for game clubs. Portraits and the stadium plan retain their stable procedural identities.

`assets/figma/tokens.json` copies the approved handoff palette and reference dimensions. The existing runtime translates those reference dimensions to its 1440 × 900 canvas. `assets/fonts/IBMPlexSans.ttf` and `Lora.ttf` are the unmodified font files from the design handoff. Their SIL Open Font License 1.1 notices are stored beside them. PyInstaller includes the full assets tree and therefore the font notices.

The earlier procedural-asset description above records the 0.3 origin; 0.9 adds these explicit Figma exports and replaces Pygame’s default interface font. No real club branding or external person likenesses have been introduced.

# Presentation asset register

## Original procedural content (0.3)

`club_chairman/presentation.py` draws eight distinct fictional club crests from original geometric templates and colour palettes. Portraits are original modular illustrations generated from stable person IDs; skin, hair and appearance do not use hidden abilities, potential or relationships. Stadium artwork is an original plan view with seats, pitch markings and a construction overlay. No real club branding, photographed likeness, downloaded artwork or AI-generated bitmap is included.

These assets are rendered at logical interface sizes and scale with the Pygame canvas. Identity survives save/load. They are development artwork; the final AA art-quality/content gate remains open.

Goal emphasis and the moving construction indicator are decorative presentation only. Reduced motion removes those effects. Neither artwork nor animation reads or advances the simulation random stream. A match highlight only follows an already committed score change.

Click, goal and notice sounds are original short sine-wave envelopes generated locally. They contain no external recordings. The current build exposes interface sound on/off; missing audio hardware gracefully disables playback. Full channel mixing, ambience, music and unfocused muting remain release work.

Typography uses the font bundled with Pygame. Dependency notices are included by the Windows packaging script; see THIRD_PARTY.md. No additional external fonts were introduced.

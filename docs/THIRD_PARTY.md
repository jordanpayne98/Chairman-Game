# Third party software

The playable preview uses Python 3.12 (Python Software Foundation licence), Pygame 2.6.1 (LGPL 2.1) and its bundled SDL-related libraries. Pygame's distributed licence and dependency notices are copied into the Windows package's licences folder. Interface typography uses the bundled IBM Plex Sans and Lora fonts under the SIL Open Font License 1.1. Their original notices are in `assets/fonts/IBMPlexSans-OFL.txt` and `assets/fonts/Lora-OFL.txt`, included in the executable’s assets. The UI icon and Northbridge crest PNGs are exports of the user’s approved Figma design; provenance is in `assets/figma/provenance.json`. Other procedural illustrations retain their original implementation. No real club brands or photographed player likenesses were added.

SQLite is supplied with Python. PyInstaller 6.16.0 packages the executable; its bootloader exception permits distribution of bundled applications under their own terms. PyInstaller is a build dependency, not a game engine.

Source and upstream licence information:

- Python: https://docs.python.org/3/license.html
- Pygame: https://github.com/pygame/pygame
- SDL: https://www.libsdl.org/license.php
- SQLite: https://www.sqlite.org/copyright.html
- PyInstaller: https://pyinstaller.org/en/stable/license.html

This is a development inventory. A full binary dependency and redistribution audit remains a commercial release gate. No open-source licence is granted for the original Club Chairman code by this notice.

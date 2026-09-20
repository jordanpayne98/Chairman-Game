"""Executive Figma tokens and bundled assets, shared by every runtime screen."""
import json
from pathlib import Path
import sys

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))
ASSETS = ROOT / 'assets'
TOKENS = json.loads((ASSETS / 'figma/tokens.json').read_text())
COLORS = {key: tuple(bytes.fromhex(value.lstrip('#'))) for key, value in TOKENS['colors'].items()}
BG = COLORS['canvas']
PANEL = COLORS['surface']
RAISED = COLORS['raised']
BORDER = COLORS['border']
TEXT = COLORS['text']
MUTED = COLORS['muted']
FAINT = COLORS['faint']
GREEN = COLORS['accent']
BUTTON = COLORS['accentFill']
SELECTED = COLORS['accentSoft']
RED = COLORS['danger']
WARNING = COLORS['warning']


def font(size, heading=False):
    import pygame
    # Existing screen sizes were authored against Pygame's smaller default font.
    # Preserve their physical text size while adopting the approved font families.
    pixels = max(11, round(size * .74))
    result = pygame.font.Font(str(ASSETS / 'fonts' / ('Lora.ttf' if heading else 'IBMPlexSans.ttf')), pixels)
    return result

"""Development prerequisites check; this is not the game or its save system."""
import argparse
import json
import os
from pathlib import Path
import platform
import sqlite3
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--headless', action='store_true')
parser.add_argument('--output', type=Path)
args = parser.parse_args()
if args.headless:
    os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame

with tempfile.TemporaryDirectory() as temp:
    db = Path(temp) / 'check.sqlite3'
    with sqlite3.connect(db) as connection:
        connection.execute('CREATE TABLE checks (value INTEGER NOT NULL)')
        connection.execute('INSERT INTO checks VALUES (?)', (12345,))
    with sqlite3.connect(db) as connection:
        assert connection.execute('SELECT value FROM checks').fetchone() == (12345,)
        assert connection.execute('PRAGMA integrity_check').fetchone() == ('ok',)

pygame.display.init()
pygame.font.init()
try:
    surface = pygame.display.set_mode((960, 540))
    pygame.display.set_caption('Club Chairman | Environment check')
    surface.fill((25, 27, 31))
    font = pygame.font.Font(None, 36)
    surface.blit(font.render('Club Chairman - environment check', True, (232, 234, 238)), (40, 60))
    surface.blit(font.render('Graphics and SQLite ready. No gameplay yet.', True, (170, 185, 174)), (40, 115))
    pygame.display.flip()
    pygame.event.post(pygame.event.Event(pygame.USEREVENT))
    assert any(event.type == pygame.USEREVENT for event in pygame.event.get())
    report = {'python': platform.python_version(), 'platform': platform.system(),
              'pygame': pygame.version.ver, 'sdl': list(pygame.get_sdl_version()),
              'sqlite': sqlite3.sqlite_version, 'video_driver': pygame.display.get_driver(),
              'checks': ['SQLite disk round trip and integrity', 'display and font rendering', 'event queue'],
              'limitations': ['No game systems tested', 'No Windows executable tested', 'No audio tested']}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
finally:
    pygame.quit()

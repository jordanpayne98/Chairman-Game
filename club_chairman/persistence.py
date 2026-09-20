"""Verified atomic SQLite saves with three rotating autosaves and backup recovery."""
from contextlib import closing
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
from .simulation import validate
from .career import initialise
from . import market, commercial


def user_directory():
    base = Path(os.environ.get('LOCALAPPDATA', Path.home() / '.local/share'))
    return base / 'ClubChairman'


class SaveError(ValueError):
    pass


def migrate(state):
    """Upgrade a verified world in memory; never rewrite the source save."""
    s = deepcopy(state)
    if s.get('schema') == 1:
        s['schema'] = 2
        s['planning'] = dict(shortlist=[], comparison=[], notes={}, inbox_read=0)
    if s.get('schema')==2:initialise(s)
    if s.get('schema')==3:
        market.initialise(s);commercial.initialise(s)
    validate(s)
    return s


def load(path):
    path=Path(path)
    try:
        if not path.is_file(): raise SaveError('No save exists in this slot.')
        with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)) as db:
            if db.execute('PRAGMA integrity_check').fetchone() != ('ok',):raise SaveError('Save integrity check failed.')
            metadata=dict(db.execute('SELECT key, value FROM metadata'))
            if metadata.get('schema') not in ('1','2','3','4'):raise SaveError('Unsupported save version. This build reads schemas 1, 2, 3 and 4.')
            raw=db.execute("SELECT payload FROM entities WHERE id='world'").fetchone()[0]
            if hashlib.sha256(raw.encode()).hexdigest()!=metadata['checksum']:raise SaveError('Save checksum does not match.')
            s=json.loads(raw)
            if str(s.get('schema')) != metadata['schema']:raise SaveError('Save version does not match its metadata.')
            return migrate(s)
    except (sqlite3.Error, OSError, KeyError, TypeError, IndexError, ValueError) as exc:
        raise SaveError(f'Cannot load {path.name}: {exc}') from exc


def save(state,path):
    validate(state)
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    raw=json.dumps(state,sort_keys=True,separators=(',',':'))
    fd,temp=tempfile.mkstemp(prefix='.save-',suffix='.sqlite3',dir=path.parent);os.close(fd)
    try:
        with closing(sqlite3.connect(temp)) as db:
            db.executescript('CREATE TABLE metadata (key TEXT PRIMARY KEY,value TEXT NOT NULL); CREATE TABLE entities (id TEXT PRIMARY KEY,payload TEXT NOT NULL);')
            db.executemany('INSERT INTO metadata VALUES (?,?)',[('schema',str(state['schema'])),('checksum',hashlib.sha256(raw.encode()).hexdigest()),('date',str(state['day'])),('content',state['config']['id'])])
            db.execute('INSERT INTO entities VALUES (?,?)',('world',raw));db.commit()
        load(temp)
        with open(temp,'r+b') as f:os.fsync(f.fileno())
        if path.exists():
            # Preserve only a validated prior save; a damaged slot is never overwritten.
            load(path)
            backup=path.with_suffix('.backup.sqlite3')
            fd,bt=tempfile.mkstemp(prefix='.backup-',dir=path.parent);os.close(fd)
            try:
                shutil.copyfile(path,bt);os.replace(bt,backup)
            finally:
                if os.path.exists(bt):os.unlink(bt)
        os.replace(temp,path)
    except (OSError,ValueError,sqlite3.Error) as exc:
        raise SaveError(f'Save failed; the previous slot is preserved: {exc}') from exc
    finally:
        if os.path.exists(temp):os.unlink(temp)


class SaveStore:
    def __init__(self,root=None):
        self.root=Path(root) if root else user_directory()/'saves'

    def write(self,state,slot='manual'):
        if slot not in ('manual','auto1','auto2','auto3'):raise SaveError('Invalid save slot.')
        directory=self.root/state['career_id']
        save(state,directory/f'{slot}.sqlite3')

    def autosave(self,state):
        # Use revision to select a slot; keep the other two committed checkpoints.
        self.write(state,f"auto{state['revision']%3+1}")

    def entries(self):
        if not self.root.exists():return []
        entries=[]
        for path in self.root.glob('*/*.sqlite3'):
            try:
                s=load(path)
                from .simulation import calendar_date
                entries.append(dict(path=path,date=calendar_date(s),day=s['day'],seed=s['seed'],valid=True,
                                    revision=s['revision'],label=f"Seed {s['seed']} | {calendar_date(s)} | {path.stem}"))
            except SaveError:
                entries.append(dict(path=path,valid=False,revision=-1,label=f'Damaged: {path.parent.name}/{path.name}'))
        return sorted(entries,key=lambda x:(x['path'].stat().st_mtime_ns,x['revision']),reverse=True)

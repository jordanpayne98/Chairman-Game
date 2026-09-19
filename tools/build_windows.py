"""Build on Windows; preserve licensing files with the distributed folder."""
from pathlib import Path
import importlib.metadata
import shutil
import subprocess
import sys

subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir','--console','--hide-console','hide-early','--name','ClubChairman','--add-data','data:data','launch.py'],check=True)
out=Path('dist/ClubChairman')
shutil.copyfile('README.md',out/'READ-ME.md')
shutil.copyfile('docs/THIRD_PARTY.md',out/'THIRD-PARTY.md')
lic=out/'licences';lic.mkdir(exist_ok=True)
pygame_dist=importlib.metadata.distribution('pygame')
for f in pygame_dist.files or []:
    if any(word in str(f).lower() for word in ('license','licence','copying')):
        src=Path(pygame_dist.locate_file(f))
        if src.is_file():
            target=lic/str(f).replace('/','_').replace('\\','_')
            shutil.copyfile(src,target)
for root in [Path(sys.base_prefix),Path(sys.base_prefix)/'Doc']:
    for file in root.glob('LICENSE*'):
        if file.is_file():shutil.copyfile(file,lic/('python-'+file.name))

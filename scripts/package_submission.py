"""Create a self-contained local delivery archive and SHA-256 manifest."""
from pathlib import Path
import hashlib
import json
import zipfile

root=Path(__file__).resolve().parents[1]
folders=['pathsnap','ui','artifacts','results','tests','scripts','docs','output/pdf','data/Student folder']
names=['README.md','REVIEW1_README.md','TEAM_GUIDE.md','VIVA_GUIDE.md','requirements.txt','run.py','start_backend.ps1','start_ui.ps1','Dockerfile','docker-compose.yml','.gitignore','.gitattributes']
files=[root/name for name in names]
for folder in folders:
    files.extend(p for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
files=sorted(set(files))
manifest={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(root/'submission_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
target=root/'PathSnap_Submission.zip'
with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
    for path in files+[root/'submission_manifest.json']:
        archive.write(path,Path('PathSnap')/path.relative_to(root))
with zipfile.ZipFile(target) as archive:
    assert archive.testzip() is None
print(f'{target}: {target.stat().st_size:,} bytes; {len(files)} files; CRC check passed')

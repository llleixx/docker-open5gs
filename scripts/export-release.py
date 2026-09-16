#!/usr/bin/env python3
import hashlib,json,pathlib,subprocess
p=pathlib.Path(__file__).resolve().parent.parent
subprocess.run(['python3','scripts/verify-images.py'],cwd=p,check=True)
refs=[x['image'] for x in json.loads((p/'artifacts/images.json').read_text())]
archive=p/'artifacts/open5gs-v2.8.0-r1.tar.gz'
with archive.open('wb') as f:
    save=subprocess.Popen(['docker','save',*refs],stdout=subprocess.PIPE)
    compress=subprocess.Popen(['gzip','-1'],stdin=save.stdout,stdout=f)
    save.stdout.close();assert compress.wait()==0 and save.wait()==0
with archive.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
(p/'artifacts/SHA256SUMS').write_text(digest+'  '+archive.name+'\n')
print(archive.stat().st_size,digest)

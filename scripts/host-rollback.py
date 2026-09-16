#!/usr/bin/env python3
"""Restore the pre-upgrade database and images; scope is the ncore project only."""
import json,pathlib,shutil,subprocess,sys,tarfile,fcntl
P=pathlib.Path
b=P(sys.argv[1]).resolve();assert b.parent==P('/opt/priv5g/backups') and b.name.startswith('upgrade-v280-')
lock=(b/'rollback.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX)
if (b/'COMMITTED').exists() and '--force' not in sys.argv[2:]:raise SystemExit('Upgrade committed; pass --force only for intentional manual recovery')
def run(*a,check=True):return subprocess.run(a,check=check)
c=P('/opt/priv5g/ncore')
run('systemctl','stop','priv5g-core',check=False)
# A failed oneshot ExecStart can leave containers running: stop explicitly.
services=subprocess.check_output(['docker','compose','-f',str(c/'docker-compose.yml'),'config','--services'],text=True).split()
run('docker','compose','-f',str(c/'docker-compose.yml'),'stop',*services)
assert not json.loads(subprocess.check_output(['docker','inspect','open5gs-db']))[0]['State']['Running']
if (b/'DATA_BACKUP_COMPLETE').exists():
    volumes=json.loads((b/'volumes.json').read_text())
    for v in volumes:
        actual=json.loads(subprocess.check_output(['docker','volume','inspect',v['Name']]))[0]
        assert actual['Mountpoint']==v['Mountpoint']
        mount=P(v['Mountpoint']).resolve()
        assert mount==P('/var/lib/docker/volumes')/v['Name']/'_data'
        assert v['Name'] in ['ncore_db_data','ncore_db_config']
        with tarfile.open(b/(v['Name']+'-after-failure.tar.gz'),'w:gz') as t:t.add(mount,arcname=v['Name'])
        for child in mount.iterdir():
            if child.is_dir() and not child.is_symlink():shutil.rmtree(child)
            else:child.unlink()
        run('tar','-xzf',str(b/'database-before.tar.gz'),'--strip-components=1','-C',str(mount),v['Name'])
for name in ['docker-compose.yml','.env']:shutil.copy2(b/name,c/name)
if (b/'webui-env-existed').read_text()=='False':(c/'.env.webui').unlink(missing_ok=True)
run('systemctl','start','priv5g-core')
(b/'ROLLED_BACK').touch()
run('systemctl','stop','open5gs-v280-rollback.timer',check=False)
print('Restored v2.7.6 configuration and pre-upgrade database snapshot')

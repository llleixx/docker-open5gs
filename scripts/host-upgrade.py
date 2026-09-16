#!/usr/bin/env python3
"""Production-only cutover after isolated acceptance and image import."""
import datetime,hashlib,json,os,pathlib,secrets,shutil,subprocess,sys,tarfile
import yaml
P=pathlib.Path
C=P('/opt/priv5g/ncore')
NFS='nrf ausf udm udr nssf bsf pcf amf smf upf webui'.split()
def run(*a): return subprocess.check_output(a,text=True,stderr=subprocess.STDOUT)
def save(b,name,args): (b/name).write_text(run(*args))
os.umask(0o077)
manifest=json.loads(P(sys.argv[1]).read_text())
assert {x['component'] for x in manifest}==set(NFS) and len(manifest)==11
for item in manifest:
    actual=json.loads(run('docker','image','inspect',item['image']))[0]
    assert actual['Id']==item['id'],item['image']
assert run('systemctl','is-active','priv5g-core').strip()=='active'
assert 'OPEN5GS_VERSION=v2.7.6' in (C/'.env').read_text(), 'Expected v2.7.6 before cutover'
b=P('/opt/priv5g/backups')/('upgrade-v280-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
b.mkdir(mode=0o700)
shutil.copy2(__file__,b/'host-upgrade.py')
shutil.copy2(P(__file__).with_name('host-rollback.py'),b/'host-rollback.py')
for name,args in {'addresses.json':['ip','-j','addr'],'routes.json':['ip','-j','route','show','table','all'],'endpoints.json':['ip','-j','mptcp','endpoint'],'containers.json':['docker','inspect',*run('docker','ps','-q').split()],'networks.json':['docker','network','inspect','open5gs','open5gs-ran','open5gs-service']}.items(): save(b,name,args)
for name in ['docker-compose.yml','.env']: shutil.copy2(C/name,b/name)
with tarfile.open(b/'config-before.tar.gz','w:gz') as tar: tar.add(C,arcname='ncore')
vols=json.loads(run('docker','volume','inspect','ncore_db_data','ncore_db_config'))
(b/'volumes.json').write_text(json.dumps(vols))
(b/'images.json').write_text(json.dumps(manifest))
(b/'webui-env-existed').write_text(str((C/'.env.webui').exists()))
print('BACKUP='+str(b),flush=True)
run('systemd-run','--unit=open5gs-v280-rollback','--on-active=20m','/usr/bin/python3',str(b/'host-rollback.py'),str(b))
try:
    run('systemctl','stop','priv5g-core')
    assert not json.loads(run('docker','inspect','open5gs-db'))[0]['State']['Running']
    with tarfile.open(b/'database-before.tar.gz','w:gz') as tar:
        for v in vols: tar.add(v['Mountpoint'],arcname=v['Name'])
    with tarfile.open(b/'database-before.tar.gz') as tar: assert tar.getmembers()
    (b/'DATA_BACKUP_COMPLETE').touch()
    cfg=yaml.safe_load((C/'docker-compose.yml').read_text())
    for nf in NFS: cfg['services'][nf]['image']=f'ghcr.io/llleixx/open5gs-{nf}:v2.8.0-r1'
    web=C/'.env.webui'
    if not web.exists():
        web.write_text('SECRET_KEY='+secrets.token_hex(32)+'\nJWT_SECRET_KEY='+secrets.token_hex(32)+'\n');web.chmod(0o600)
    mount='./.env.webui:/usr/local/src/webui/.env'
    if mount not in cfg['services']['webui'].setdefault('volumes',[]): cfg['services']['webui']['volumes'].append(mount)
    (C/'docker-compose.yml').write_text(yaml.safe_dump(cfg,sort_keys=False))
    env=(C/'.env').read_text(); assert 'OPEN5GS_VERSION=v2.7.6' in env
    (C/'.env').write_text(env.replace('OPEN5GS_VERSION=v2.7.6','OPEN5GS_VERSION=v2.8.0'))
    run('docker','compose','-f',str(C/'docker-compose.yml'),'config','--quiet')
    run('systemctl','start','priv5g-core')
    for p in b.glob('*.tar.gz'):
        with p.open('rb') as f: digest=hashlib.file_digest(f,'sha256').hexdigest()
        with (b/'SHA256SUMS').open('a') as out:out.write(digest+'  '+p.name+'\n')
    print('CUTOVER_STARTED; watchdog remains active; acceptance required',flush=True)
except Exception:
    subprocess.run(['/usr/bin/python3',str(b/'host-rollback.py'),str(b)],check=True)
    raise

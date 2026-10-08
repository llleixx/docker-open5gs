#!/usr/bin/env python3
"""Guarded deployment/rollback for the approved DSCP UL trial only."""
import concurrent.futures,datetime,json,os,pathlib,shutil,subprocess,sys,time
import yaml
from make_policy import policy_config
R=pathlib.Path('/opt/priv5g/qos-ul1/trial')
C=pathlib.Path('/opt/priv5g/ncore')
TAG='v2.8.0-r1-dscp-ul1'
NODES=[2,4,6,8,10,12,14,16,18,20,23,27,31,35,39]
def run(*args,timeout=90):
    try:return subprocess.check_output(args,text=True,stderr=subprocess.STDOUT,timeout=timeout)
    except subprocess.CalledProcessError as exc:
        print(exc.output,flush=True);raise
def save(name,data): (R/name).write_text(data if isinstance(data,str) else json.dumps(data,indent=2))
def reach():
    def one(n):
        p=subprocess.run(['ping','-I','10.100.67.250','-c','1','-W','2',f'10.100.68.{n}'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        return str(n),p.returncode==0
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as pool:return dict(pool.map(one,NODES))
def dc(*args):return run('docker','compose','-f',str(C/'docker-compose.yml'),*args,timeout=180)
def pin_ips(cfg):
    snapshot=json.loads((R/'containers-before.json').read_text())
    for nf in ['pcf','upf']:
        old=next(x for x in snapshot if x['Name']=='/open5gs-'+nf)
        cfg['services'][nf]['networks']['open5gs']['ipv4_address']=old['NetworkSettings']['Networks']['open5gs']['IPAddress']
    return cfg
def prepare():
    R.mkdir(parents=True,exist_ok=True,mode=0o700)
    assert not (R/'before-compose.yml').exists(),'Existing backup must not be overwritten'
    for nf in ['pcf','smf','upf']:
        shutil.copy2(C/'configs'/f'{nf}.yaml',R/f'before-{nf}.yaml')
    shutil.copy2(C/'docker-compose.yml',R/'before-compose.yml')
    save('containers-before.json',run('docker','inspect',*[f'open5gs-{nf}' for nf in ['pcf','smf','upf','amf']]))
    save('images-new.json',run('docker','image','inspect',*[f'ghcr.io/llleixx/open5gs-{nf}:{TAG}' for nf in ['pcf','smf','upf']]))
    for nf in ['pcf','smf','upf']:
        meta=json.loads(run('docker','image','inspect',f'ghcr.io/llleixx/open5gs-{nf}:{TAG}'))[0]
        assert meta['Config']['Labels']['huizhou.patch-sha256']=='cc7aec461dc9a78f23acbaca84ae09e2e6c4b36e60fffcd8a54121070483897c'
    query='print(JSON.stringify(db.subscribers.find({"slice.session.ue.ipv4":{$in:["10.100.68.8","10.100.68.16","10.100.68.27"]}},{_id:0,imsi:1,slice:1}).toArray()))'
    subs=json.loads(run('docker','exec','open5gs-db','mongosh','--quiet','open5gs','--eval',query))
    assert len(subs)==3
    save('subscriptions.json',subs)
    base=yaml.safe_load((R/'before-pcf.yaml').read_text())
    one=[s for s in subs if any(x.get('ue',{}).get('ipv4')=='10.100.68.8' for sl in s['slice'] for x in sl['session'])]
    assert len(one)==1
    save('pcf-single.yaml',yaml.safe_dump(policy_config(base,one,probe=True),sort_keys=False))
    save('pcf-three.yaml',yaml.safe_dump(policy_config(base,subs,probe=True),sort_keys=False))
    save('pcf-final.yaml',yaml.safe_dump(policy_config(base,subs,probe=False),sort_keys=False))
    save('reachable-before.json',reach())
    save('bridge8-before.txt',run('ssh','-n','root@10.100.65.8','/opt/bridge/bridge-ctl status; sysctl net.mptcp.prefer_ifindex; ip mptcp endpoint; ip route show table all; nft list table inet bridge_daemon_qos'))
    print('Trial backup complete; single and three-bridge policies generated',flush=True)
def restart():
    dc('stop','amf','smf','pcf','upf')
    dc('up','-d','--no-deps','pcf','upf','smf','amf')
def rollback():
    if not (R/'APPLIED').exists(): print('No trial deployment active');return
    for nf in ['pcf','smf','upf']:shutil.copy2(R/f'before-{nf}.yaml',C/'configs'/f'{nf}.yaml')
    (C/'docker-compose.yml').write_text(yaml.safe_dump(pin_ips(yaml.safe_load((R/'before-compose.yml').read_text())),sort_keys=False))
    restart()
    (R/'APPLIED').unlink();save('rolled-back-at',datetime.datetime.now(datetime.timezone.utc).isoformat())
    print('Original core images and configs restored',flush=True)
def apply():
    assert not (R/'APPLIED').exists()
    assert all(reach().values()), 'Restore baseline connectivity before applying'
    run('systemd-run','--unit=qos-ul1-trial-rollback','--on-active=25m','/usr/bin/python3',str(pathlib.Path(__file__).resolve()),'rollback')
    (R/'APPLIED').touch()
    save('applied-at',datetime.datetime.now(datetime.timezone.utc).isoformat())
    try:
        cfg=pin_ips(yaml.safe_load((R/'before-compose.yml').read_text()))
        for nf in ['pcf','smf','upf']:cfg['services'][nf]['image']=f'ghcr.io/llleixx/open5gs-{nf}:{TAG}'
        (C/'docker-compose.yml').write_text(yaml.safe_dump(cfg,sort_keys=False))
        shutil.copy2(R/'pcf-single.yaml',C/'configs/pcf.yaml')
        dc('config','--quiet');restart()
        print('Single-bridge trial applied; rollback watchdog active',flush=True)
    except BaseException:
        rollback();raise
def status():
    save('reachable-current.json',reach())
    print((R/'reachable-current.json').read_text())
    print(run('docker','ps','--format','{{.Names}} {{.Status}}'))
if __name__=='__main__':
    os.umask(0o077)
    {'prepare':prepare,'apply':apply,'rollback':rollback,'status':status}[sys.argv[1]]()

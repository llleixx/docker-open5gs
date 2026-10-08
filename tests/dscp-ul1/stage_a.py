#!/usr/bin/env python3
"""Bounded, reversible original-image QoS capability check for bridge 8."""
import copy, datetime, json, os, pathlib, shutil, subprocess, sys, time
import yaml

ROOT=pathlib.Path('/opt/priv5g/qos-ul1/stage-a')
CORE=pathlib.Path('/opt/priv5g/ncore')
BRIDGE='10.100.65.8'
UNIT='qos-ul1-stage-a-rollback'
def run(*args, timeout=40):
    return subprocess.check_output(args,text=True,stderr=subprocess.STDOUT,timeout=timeout)
def bridge(command,timeout=40):
    return run('ssh','-n','-o','BatchMode=yes','-o','ConnectTimeout=5','-o','ServerAliveInterval=5','-o','ServerAliveCountMax=1','root@'+BRIDGE,command,timeout=timeout)
def save(name,text):
    (ROOT/name).write_text(text)
def prepare():
    ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
    assert not (ROOT/'before-pcf.yaml').exists(), 'Backup already exists; do not overwrite'
    for name in ['pcf','smf','upf']:
        shutil.copy2(CORE/'configs'/f'{name}.yaml', ROOT/f'before-{name}.yaml')
    shutil.copy2(CORE/'docker-compose.yml',ROOT/'before-compose.yml')
    save('containers-before.json',run('docker','inspect','open5gs-pcf','open5gs-smf','open5gs-upf','open5gs-amf'))
    for name,args in [('host-addresses.json',('ip','-j','addr')),('host-routes.json',('ip','-j','route','show','table','all')),('host-endpoints.json',('ip','-j','mptcp','endpoint'))]: save(name,run(*args))
    save('bridge8-before.txt',bridge('hostname; ip -4 -br addr; ip -4 route show table all; ip mptcp endpoint; nft list table inet bridge_daemon_qos; systemctl is-active bridge-daemon openvpn-bridge-client; rm500u module status; ss -tn'))
    query='print(JSON.stringify(db.subscribers.find({"slice.session.ue.ipv4":"10.100.68.8"},{_id:0,imsi:1,slice:1}).toArray()))'
    subs=json.loads(run('docker','exec','open5gs-db','mongosh','--quiet','open5gs','--eval',query))
    assert len(subs)==1
    save('subscription8.json',json.dumps(subs,indent=2))
    sub=subs[0]
    sl=next(x for x in sub['slice'] if x['sd']=='000001')
    session=copy.deepcopy(next(x for x in sl['session'] if x['name']=='slice1'))
    session.pop('ue',None)
    assert session['qos']['index']==9
    session['pcc_rule']=[]
    for qi,port in [(6,12166),(8,12167)]:
        qos=copy.deepcopy(session['qos']);qos['index']=qi
        # Stock SMF creates a DL PDR even for UL-only flows. An unreachable
        # documentation-source DL filter avoids an empty catch-all DL PDR.
        session['pcc_rule'].append({'qos':qos,'flow':[
            {'direction':2,'description':f'permit out tcp from 10.100.67.250 {port} to assigned'},
            {'direction':1,'description':f'permit out ip from 192.0.2.{qi} to assigned'}]})
    cfg=yaml.safe_load((ROOT/'before-pcf.yaml').read_text())
    assert not cfg['pcf'].get('policy'), 'Unexpected existing local policy'
    cfg['pcf']['policy']=[{'supi_range':[f"{sub['imsi']}-{sub['imsi']}"], 'slice':[{'sst':sl['sst'],'sd':sl['sd'],'default_indicator':True,'session':[session]}]}]
    save('candidate-pcf.yaml',yaml.safe_dump(cfg,sort_keys=False))
    save('started-at',datetime.datetime.now(datetime.timezone.utc).isoformat())
    print('Backup and candidate ready; only bridge8, probe ports 12166/12167')
def rollback():
    if not (ROOT/'APPLIED').exists():
        print('Nothing applied');return
    shutil.copy2(ROOT/'before-pcf.yaml',CORE/'configs/pcf.yaml')
    run('docker','restart','open5gs-pcf')
    save('rollback-at',datetime.datetime.now(datetime.timezone.utc).isoformat())
    # An existing PDU session retains its policy; explicitly reconnect bridge8.
    result=bridge('rm500u module restart --yes',timeout=60)
    save('rollback-module.txt',result)
    (ROOT/'APPLIED').unlink()
    (ROOT/'ROLLED_BACK').touch()
    print('Original PCF restored; bridge8 modem restarted')
def apply():
    assert (ROOT/'candidate-pcf.yaml').exists()
    assert not (ROOT/'APPLIED').exists()
    run('systemd-run','--unit='+UNIT,'--on-active=8m','/usr/bin/python3',str(pathlib.Path(__file__).resolve()),'rollback')
    (ROOT/'APPLIED').touch()
    try:
        shutil.copy2(ROOT/'candidate-pcf.yaml',CORE/'configs/pcf.yaml')
        run('docker','restart','open5gs-pcf')
        time.sleep(3)
        assert json.loads(run('docker','inspect','open5gs-pcf'))[0]['State']['Running']
        save('apply-module.txt',bridge('rm500u module restart --yes',timeout=60))
        print('Applied candidate; watchdog active for 8 minutes; bridge8 modem restarted')
    except BaseException:
        rollback();raise
if __name__=='__main__':
    os.umask(0o077)
    {'prepare':prepare,'apply':apply,'rollback':rollback}[sys.argv[1]]()

#!/usr/bin/env python3
import json,pathlib,subprocess,sys,time
root=pathlib.Path(__file__).resolve().parent
compose=pathlib.Path(sys.argv[1]).resolve()
cid=subprocess.check_output(['docker','compose','-f',str(compose),'ps','-q','n6-test'],text=True).strip()
meta=json.loads(subprocess.check_output(['docker','inspect',cid]))[0]
network=next(iter(meta['NetworkSettings']['Networks'].values()))['NetworkID']
bridge='br-'+network[:12]
pid=str(meta['State']['Pid']);rules=[];server=None
try:
    # Docker internal bridges reject routed UE source addresses by default.
    # Permit only the test N6/UE prefixes within this specific isolated bridge.
    for pool in ['10.250.83.0/24','10.250.84.0/24','10.250.85.0/24']:
        for src,dst in [(pool,'10.250.82.0/24'),('10.250.82.0/24',pool)]:
            rule=['DOCKER-USER','-i',bridge,'-o',bridge,'-s',src,'-d',dst,'-j','ACCEPT']
            subprocess.run(['iptables','-I',*rule],check=True);rules.append(rule)
    log=(compose.parent/'results');log.mkdir(exist_ok=True)
    with (log/'n6.log').open('w') as out:
        server=subprocess.Popen(['nsenter','-t',pid,'-n','python3',str(root/'n6-server.py')],stdout=out,stderr=subprocess.STDOUT)
        time.sleep(1)
        subprocess.run(['python3',str(root/'verify.py'),'--compose',str(compose)],check=True)
finally:
    if server:server.terminate();server.wait()
    for rule in reversed(rules):subprocess.run(['iptables','-D',*rule],check=True)

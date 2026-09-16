#!/usr/bin/env python3
"""Run as root in the WSL Docker host. Uses synthetic subscribers only."""
import argparse,datetime,hashlib,json,pathlib,socket,struct,subprocess,time
p=argparse.ArgumentParser();p.add_argument('--compose',default=str(pathlib.Path(__file__).with_name('compose.json')));a=p.parse_args()
compose=pathlib.Path(a.compose).resolve();base=['docker','compose','-f',str(compose),'--profile','sim']
def run(*args):return subprocess.check_output(args,text=True,stderr=subprocess.STDOUT)
def dc(*args):return run(*base,*args)
def cid(name):return dc('ps','-q',name).strip()
def inspect(name):return json.loads(run('docker','inspect',cid(name)))[0]
def ex(name,*args):return run('docker','exec',cid(name),*args)
def ns(name,code):return run('nsenter','-t',str(inspect(name)['State']['Pid']),'-n','python3','-c',code)
results={'time':datetime.datetime.now(datetime.timezone.utc).isoformat(),'slices':[]}
assert 'PFCP associated' in dc('logs','--no-color','smf'), 'PFCP association absent'
for name in 'ausf udm udr nssf bsf pcf amf smf'.split():
    assert 'NF registered' in dc('logs','--no-color',name),name+' NRF registration missing'
upfaddrs=json.loads(ex('upf','ip','-j','addr'))
assert any(x['mtu']==1600 and any(y.get('local')=='10.250.81.3' for y in x.get('addr_info',[])) for x in upfaddrs)
nat=ex('upf','iptables','-t','nat','-S')
assert not any('MASQUERADE' in line and any('10.250.'+str(i) in line for i in [83,84,85]) for line in nat.splitlines())
for i in [1,2,3]:
    name='ue'+str(i);addr=None
    for attempt in range(30):
        entries=json.loads(ex(name,'ip','-j','-4','addr'))
        addr=next((y['local'] for x in entries if x['ifname']=='uesimtun0' for y in x.get('addr_info',[])),None)
        if addr:break
        time.sleep(1)
    assert addr and addr.startswith('10.250.'+str(82+i)+'.'),(name,addr)
    ex(name,'ip','route','replace','10.250.82.0/24','dev','uesimtun0')
    ex(name,'ping','-c','3','-W','2','10.250.82.10')
    ns('n6-test',f"import subprocess;subprocess.run(['ping','-c','3','-W','2',{addr!r}],check=True)")
    ns(name,f"import urllib.request; assert (b'lab OK '+{addr!r}.encode()) in urllib.request.urlopen('http://10.250.82.10:8080',timeout=5).read()")
    ns(name,"import socket; s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.settimeout(5);s.sendto(bytes.fromhex('123401000001000000000000')+b'\\x03lab\\x04test\\x00\\x00\\x01\\x00\\x01',('10.250.82.53',53));r=s.recv(2048);assert r[-4:]==socket.inet_aton('10.250.82.10')")
    results['slices'].append({'dnn':'slice'+str(i),'ip':addr,'uplink_icmp':True,'downlink_icmp':True,'dns':True,'http':True})
assert inspect('webui')['State']['Health']['Status']=='healthy'
secret=compose.parent/'webui.env';before=hashlib.sha256(secret.read_bytes()).hexdigest()
dc('up','-d','--no-deps','--force-recreate','webui')
for attempt in range(40):
    if inspect('webui')['State'].get('Health',{}).get('Status')=='healthy':break
    time.sleep(1)
assert inspect('webui')['State']['Health']['Status']=='healthy'
assert before==hashlib.sha256(secret.read_bytes()).hexdigest()
results.update(pfcp=True,nrf_registration=True,n3_mtu=1600,no_ue_masquerade=True,webui_healthy=True,webui_secret_persistent=True)
out=compose.parent/'results';out.mkdir(exist_ok=True);(out/'acceptance.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))

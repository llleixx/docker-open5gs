#!/usr/bin/env python3
"""Read-only upgrade acceptance against the immediately preceding baseline."""
import json,pathlib,re,subprocess,sys,urllib.request
baseline=pathlib.Path(sys.argv[1]);current=pathlib.Path(sys.argv[2]);manifest=json.loads(pathlib.Path(sys.argv[3]).read_text())
before=json.loads((baseline/'summary.json').read_text());after=json.loads((current/'summary.json').read_text());checks=[]
def check(name,value):
    checks.append({'check':name,'passed':bool(value)})
def run(*args):return subprocess.check_output(args,text=True,stderr=subprocess.STDOUT)
def ex(name,*args):return run('docker','exec','open5gs-'+name,*args)
old={x['name']:x for x in before['containers']};new={x['name']:x for x in after['containers']}
for item in manifest:
    x=new['open5gs-'+item['component']]
    check(item['component']+' image/running',x['running'] and x['image_id']==item['id'])
    if item['component']!='webui':check(item['component']+' actual version','2.8.0' in ex(item['component'],'open5gs-'+item['component']+'d','-v'))
for name,x in old.items():
    if not name.startswith('open5gs-'):check(name+' unchanged',new[name]['id']==x['id'] and new[name]['started']==x['started'] and new[name]['running']==x['running'])
check('accounts and subscription configuration preserved',before['db']==after['db'])
check('all baseline sessions restored',set(before['sessions'])<=set(after['sessions']))
responders={imsi for imsi,x in before['sessions'].items() if x['ping']}
check('all original ICMP responders restored',all(after['sessions'].get(imsi,{}).get('ping') for imsi in responders))
for name in ['mptcp.txt','mptcp_limits.txt']:check(name+' unchanged',(baseline/name).read_text()==(current/name).read_text())
check('network boundary rules unchanged',[x for x in (baseline/'iptables.txt').read_text().splitlines() if x.startswith('-A') and 'PRIV5G-BOUNDARY' in x]==[x for x in (current/'iptables.txt').read_text().splitlines() if x.startswith('-A') and 'PRIV5G-BOUNDARY' in x])
def ipv4(path):return {x['ifname']:sorted(y['local']+'/'+str(y['prefixlen']) for y in x.get('addr_info',[]) if y['family']=='inet') for x in json.loads(path.read_text()) if any(y['family']=='inet' for y in x.get('addr_info',[]))}
check('host IPv4 addresses unchanged',ipv4(baseline/'addresses.txt')==ipv4(current/'addresses.txt'))
check('default routes unchanged',[x for x in json.loads((baseline/'routes.txt').read_text()) if x.get('dst')=='default']==[x for x in json.loads((current/'routes.txt').read_text()) if x.get('dst')=='default'])
for name in ['amf','smf']:
    metrics=(current/(name+'.metrics')).read_text()
    key='gnb' if name=='amf' else 'pfcp_peers_active'
    check(key+' active',bool(re.search('^'+key+r' [1-9]\d*$',metrics,re.M)))
addrs=json.loads(ex('upf','ip','-j','addr'))
check('N3 MTU 1600',any(x['mtu']==1600 and any(y.get('local')=='10.100.66.3' for y in x.get('addr_info',[])) for x in addrs))
nat=ex('upf','iptables','-t','nat','-S')
check('no UE MASQUERADE',not any('MASQUERADE' in line and any(pool in line for pool in ['10.100.68','10.100.69','10.100.70']) for line in nat.splitlines()))
for name in ['dns','iperf3','sockperf','debugbox','librespeed']:
    routes=ex(name,'ip','route')
    check(name+' UE return routes',all('10.100.'+str(i)+'.0/24 via 10.100.67.1' in routes for i in [68,69,70]))
check('WebUI healthy',new['open5gs-webui']['health']=='healthy')
targets=json.load(urllib.request.urlopen('http://127.0.0.1:9090/api/v1/targets',timeout=5))['data']['activeTargets']
check('all monitoring targets healthy',len(targets)==3 and all(x['health']=='up' for x in targets))
check('formal VPN active',run('systemctl','is-active','huizhou-access').strip()=='active')
check('MPTCP endpoint service active',run('systemctl','is-active','priv5g-mptcp-endpoints').strip()=='active')
(current/'checks.json').write_text(json.dumps(checks,indent=2))
print(json.dumps({'passed':sum(x['passed'] for x in checks),'total':len(checks),'failed':[x['check'] for x in checks if not x['passed']]},indent=2))
sys.exit(0 if all(x['passed'] for x in checks) else 1)

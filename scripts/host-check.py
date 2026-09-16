#!/usr/bin/env python3
"""Capture read-only production baseline/acceptance. Output contains private IMSIs."""
import concurrent.futures,datetime,hashlib,json,pathlib,re,subprocess,sys,urllib.request
out=pathlib.Path(sys.argv[1]);out.mkdir(mode=0o700,exist_ok=True)
def run(*args):return subprocess.check_output(args,text=True,stderr=subprocess.STDOUT)
def metric(ip):return urllib.request.urlopen('http://'+ip+':9090/metrics',timeout=5).read().decode()
def ping(ip):return subprocess.run(['ping','-c','2','-W','2',ip],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
logs=run('docker','logs','open5gs-smf');sessions={}
for line in logs.splitlines():
    m=re.search(r'UE SUPI\[imsi-(\d+)\] DNN\[(.*?)\] IPv4\[([0-9.]+)\]',line)
    if m:sessions[m[1]]={'dnn':m[2],'ip':m[3]}
    m=re.search(r'Removed Session: UE IMSI:\[imsi-(\d+)\].*IPv4:\[([0-9.]+)\]',line)
    if m and sessions.get(m[1],{}).get('ip')==m[2]:sessions.pop(m[1],None)
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as e:
    answers=list(e.map(ping,[s['ip'] for s in sessions.values()]))
for s,answer in zip(sessions.values(),answers):s['ping']=answer
allcontainers=json.loads(run('docker','inspect',*run('docker','ps','-aq').split()))
containers=[{'name':x['Name'].lstrip('/'),'id':x['Id'],'image':x['Config']['Image'],'image_id':x['Image'],'started':x['State']['StartedAt'],'running':x['State']['Running'],'restarts':x['RestartCount'],'health':x['State'].get('Health',{}).get('Status')} for x in allcontainers]
query='JSON.stringify({accounts:db.accounts.find().sort({_id:1}).toArray(),subscribers:db.subscribers.find({}, {_id:0,imsi:1,"security.k":1,"security.opc":1,"security.op":1,"security.amf":1,slice:1}).sort({imsi:1}).toArray()})'
data=json.loads(run('docker','exec','open5gs-db','mongosh','--quiet','open5gs','--eval',query))
summary={'time':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sessions':sessions,'containers':containers,'db':{k:{'count':len(v),'sha256':hashlib.sha256(json.dumps(v,sort_keys=True).encode()).hexdigest()} for k,v in data.items()}}
for name,args in {'addresses':['ip','-j','addr'],'routes':['ip','-j','route','show','table','all'],'mptcp':['ip','-j','mptcp','endpoint'],'mptcp_limits':['ip','mptcp','limits','show'],'sctp':['cat','/proc/net/sctp/assocs'],'iptables':['iptables-save']}.items():(out/(name+'.txt')).write_text(run(*args))
for name,ip in [('amf','10.33.33.9'),('smf','10.33.33.10'),('upf','10.33.33.2')]:
    (out/(name+'.metrics')).write_text(metric(ip))
(out/'summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps({'time':summary['time'],'sessions':len(sessions),'responding':sum(answers),'db':{k:v['count'] for k,v in summary['db'].items()}}))

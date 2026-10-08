import concurrent.futures,itertools,json,pathlib,subprocess,sys,time,re
import gnb_pm
R=pathlib.Path("/opt/priv5g/qos-ul1/trial/competition")
HOSTS={8:"10.100.65.8",16:"10.100.65.16",27:"10.100.68.27"}
def run(*a,timeout=300):return subprocess.check_output(a,text=True,stderr=subprocess.STDOUT,timeout=timeout)
def radios(label):
 out={}
 for n,h in HOSTS.items():
  out[n]=json.loads(run("ssh","-n",f"root@{h}","/opt/rm500u/.venv/bin/python /tmp/qos-ul1-radio.py",timeout=20))
 (R/f"{label}-radio.json").write_text(json.dumps(out,indent=2))
 cells=[re.search(r"460,88,([0-9A-Fa-f]+),(\d+),",v["cell"]) for v in out.values()]
 assert all(cells) and len({m.groups() for m in cells})==1,"Same-cell gate failed"
 assert cells[0].group(1)=="000018014","PM collector currently bound to BS-02; configure collector for the serving cell before testing"
 return out
def one_case(session,label,roles,rate,warm,measure):
 radios(label+"-before")
 before=gnb_pm.snapshot(session);(R/f"{label}-pm-before.json").write_text(json.dumps(before))
 start=time.time()+8
 def one(n):
  h=HOSTS[n];dscp=roles[n];remote=f"/tmp/qos-ul1-load/{label}.json"
  cmd=f"python3 /tmp/qos-ul1-loadtest.py client --source 10.100.68.{n} --dscp {dscp} --mbps {rate} --warmup {warm} --measure {measure} --start {start} --output {remote}"
  output=run("ssh","-n",f"root@{h}",cmd,timeout=warm+measure+35)
  run("scp",f"root@{h}:{remote}",str(R/f"{label}-bridge{n}.json"),timeout=30)
  return n,json.loads(output)
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:results=dict(ex.map(one,HOSTS))
 after=gnb_pm.snapshot(session);(R/f"{label}-pm-after.json").write_text(json.dumps(after))
 radios(label+"-after")
 row=dict(label=label,start=start,roles=roles,rate=rate,warmup=warm,measure=measure,results=results,pm_before=gnb_pm.summary(before),pm_after=gnb_pm.summary(after))
 with (R/"cases.jsonl").open("a") as f:f.write(json.dumps(row)+"\n")
 print(json.dumps({k:v for k,v in row.items() if k not in ["pm_before","pm_after"]}),flush=True)
 assert all(not x["errors"] for x in results.values()),"Traffic generator errors"
 return row

def main(password,mode):
 session=gnb_pm.login(password)
 for n,h in HOSTS.items():
  run("ssh","-n",f"root@{h}","mkdir -p /tmp/qos-ul1-load")
  run("scp","/opt/priv5g/qos-ul1/loadtest.py",f"root@{h}:/tmp/qos-ul1-loadtest.py")
 if mode=="preflight":
  for rate in [0,5,20,50,100]:one_case(session,f"preflight-{rate}",{n:0 for n in HOSTS},rate,5,15)
 elif mode=="full":
  for repeat in range(3):
   one_case(session,f"baseline-r{repeat+1}",{n:0 for n in HOSTS},100,30,180)
   for order,roles in enumerate(itertools.permutations([46,26,0]),1):one_case(session,f"r{repeat+1}-p{order}",dict(zip(HOSTS,roles)),100,30,180)
 else:raise ValueError(mode)
if __name__=="__main__":main(sys.stdin.readline().strip(),sys.argv[1])

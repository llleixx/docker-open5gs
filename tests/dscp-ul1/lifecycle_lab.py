import copy,json,pathlib,subprocess,time,signal
R=pathlib.Path("/root/ws/docker-open5gs/private/dscp-ul1/lab");B=["docker","compose","-f",str(R/"compose.json")];out=R/"results/lifecycle";out.mkdir(exist_ok=True)
def run(*a):return subprocess.check_output(a,stderr=subprocess.STDOUT,text=True)
def capture(name):return subprocess.Popen(["tcpdump","-i","any","-s","0","-U","-w",str(out/name),"net 10.250.80.0/24"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
def close(p):p.send_signal(signal.SIGINT);p.wait()
if not (out/"setup.pcap").exists():
 c=capture("setup.pcap")
 try:
  run(*B,"stop","ue1","ue2","ue3","gnb","smf","amf","pcf","upf")
  run(*B,"start","pcf","upf","smf","amf");run(*B,"start","gnb","ue1","ue2","ue3");time.sleep(12)
 finally:close(c)
hexdata=run("tshark","-r",str(out/"setup.pcap"),"-Y","http2","-T","fields","-e","http2.data.data")
policy=None;uri=None
for line in hexdata.splitlines():
 for val in line.strip().split(","):
  try:x=json.loads(bytes.fromhex(val))
  except:continue
  if not isinstance(x,dict):continue
  if x.get("supi")=="imsi-460889999999901" and "dnn" in x and "notificationUri" in x:uri=x["notificationUri"]
  if "pccRules" in x:policy=x
assert uri and policy,(uri,policy)
# The synthetic lab is bound to its private bridge address; never address production.
assert "/sm-policy-notify/" in uri
smf=json.loads(run("docker","inspect",run(*B,"ps","-q","smf").strip()))[0]
ip=next(iter(smf["NetworkSettings"]["Networks"].values()))["IPAddress"];assert ip.startswith("10.250.80.")
url=uri.replace("smf.open5gs.org",ip)+"/update"
results=[]
def notify(name,decision,expected=204):
 payload=out/f"{name}.json";payload.write_text(json.dumps({"smPolicyDecision":decision}))
 c=capture(name+".pcap");time.sleep(.3)
 try:
  status=run("curl","--noproxy","*","--http2-prior-knowledge","-sS","-o",str(out/f"{name}-response.txt"),"-w","%{http_code}","-H","Content-Type: application/json","--data-binary","@"+str(payload),url)
  assert status==str(expected),(name,status)
  time.sleep(3)
 finally:close(c)
 results.append(dict(name=name,status=status));print(name,status,flush=True)
base={k:policy[k] for k in ["pccRules","qosDecs"]}
bad=copy.deepcopy(base);bad["pccRules"]["slice1-n1"]["flowInfos"][0]["tosTrafficClass"]="b800";notify("invalid-mask",bad,400)
changed=copy.deepcopy(base);changed["pccRules"]["slice1-n1"]["flowInfos"][0]["tosTrafficClass"]="a0fc";notify("tos-update",changed)
notify("deduplicate",changed)
direction=copy.deepcopy(changed);direction["pccRules"]["slice1-n1"]["flowInfos"][0]["flowDirection"]="DOWNLINK";notify("direction-update",direction)
notify("restore-uplink",base)
notify("delete-rules",{"pccRules":{"slice1-n1":None,"slice1-n2":None}})
notify("recreate-rules",base)
(out/"results.json").write_text(json.dumps(results,indent=2))
subprocess.run(["python3",str(R/"network-test.py"),str(R/"compose.json")],check=True)
print("Lifecycle notifications and final data regression passed")


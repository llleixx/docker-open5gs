import concurrent.futures,hashlib,json,pathlib,subprocess,sys,time
sys.path.insert(0,"/opt/priv5g/qos-ul1");import trial
R=trial.R
out={"time":time.time(),"reachability":trial.reach(),"images":json.loads(trial.run("docker","inspect","open5gs-pcf","open5gs-smf","open5gs-upf")),"config_byte_identical":{nf:(trial.C/"configs"/f"{nf}.yaml").read_bytes()==(R/f"before-{nf}.yaml").read_bytes() for nf in ["pcf","smf","upf"]}}
def one(n):
 host=f"10.100.68.{n}" if n==27 else f"10.100.65.{n}"
 cmd="systemctl is-active bridge-daemon openvpn-bridge-client; /opt/bridge/bridge-ctl priority get; sysctl -n net.mptcp.prefer_ifindex; ss -tn dst 10.100.67.250"
 return str(n),trial.run("ssh","-n","-o","ConnectTimeout=5",f"root@{host}",cmd,timeout=20)
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:out["bridges"]=dict(ex.map(one,trial.NODES))
(R/"final-audit.json").write_text(json.dumps(out,indent=2))
print(json.dumps({"missing_5g_vpn_subflow":[n for n,v in out["bridges"].items() if ":12165" not in v],"all_15_reachable":all(out["reachability"].values()),"all_vpn_daemon_active":all(x.startswith("active\nactive\n") for x in out["bridges"].values()),"config_byte_identical":out["config_byte_identical"],"images":[x["Config"]["Image"] for x in out["images"]],"selected_bridges":{n:out["bridges"][n] for n in ["8","16","27"]}},indent=2))

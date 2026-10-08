import pathlib,subprocess,json
R=pathlib.Path("/root/ws/docker-open5gs/private/dscp-ul1/lab/results/lifecycle")
results=[]
for name in ["invalid-mask","tos-update","deduplicate","direction-update","restore-uplink","delete-rules","recreate-rules"]:
 s=subprocess.check_output(["tshark","-r",str(R/f"{name}.pcap"),"-Y","pfcp.msg_type == 52","-V"],stderr=subprocess.DEVNULL,text=True)
 (R/f"{name}-pfcp.txt").write_text(s)
 if name in ["invalid-mask","deduplicate"]:assert not s,name
 elif name in ["tos-update","direction-update"]:assert "ToS Traffic Class: 0xa0" in s and "Mask field: 0xfc" in s,name
 elif name in ["restore-uplink","recreate-rules"]:assert "ToS Traffic Class: 0xb8" in s,name
 elif name=="delete-rules":assert "Remove PDR" in s,name
 results.append(dict(name=name,pfcp_wire_check="pass"))
(R/"wire-checks.json").write_text(json.dumps(results,indent=2));print(json.dumps(results))

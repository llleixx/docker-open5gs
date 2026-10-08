import pathlib,subprocess,time,signal,json
R=pathlib.Path("/root/ws/docker-open5gs/private/dscp-ul1/lab")
c=subprocess.Popen(["tcpdump","-i","any","-s","0","-U","-w",str(R/"results/dscp-final.pcap"),"net 10.250.80.0/24"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
 time.sleep(.5)
 subprocess.run(["docker","compose","-f",str(R/"compose.json"),"restart","smf","amf","pcf","gnb","ue1","ue2","ue3"],check=True)
 time.sleep(20)
finally:
 c.send_signal(signal.SIGINT);c.wait()
v=subprocess.check_output(["tshark","-r",str(R/"results/dscp-final.pcap"),"-Y","nas-5gs.sm.message_type == 0xcb","-T","fields","-e","nas-5gs.sm.qos_rule_precedence","-e","nas-5gs.sm.qfi"],text=True)
print(v)
assert v.strip(), "Missing NAS evidence"
for row in v.strip().splitlines():
 p=row.split("\t")[0].split(",")
 assert len(set(p))==2 and "0" not in p,p
(R/"results/nas-precedence.txt").write_text(v)


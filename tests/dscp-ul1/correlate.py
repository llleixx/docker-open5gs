import collections,json,pathlib,sys
from scapy.all import PcapReader,IP,TCP,UDP
from scapy.contrib.gtp import GTP_U_Header,GTPPDUSessionContainer
R=pathlib.Path(sys.argv[1]); events=[json.loads(x) for x in (R/"events.jsonl").read_text().splitlines()]
start=next(x["time"] for x in events if x["event"]=="priority");end=next(x["time"] for x in events if x["event"]=="complete")
def key(ip):
 t=ip[TCP];return (ip.src,ip.dst,ip.id,ip.len,ip.tos,t.sport,t.dport,t.seq,t.ack,int(t.flags))
usb={};counts=collections.Counter();n3=collections.defaultdict(set);dl=collections.Counter()
for p in PcapReader(str(R/"usb.pcap")):
 if start<=float(p.time)<=end and IP in p and TCP in p and p[IP].src=="10.100.68.8":usb[key(p[IP])]=float(p.time);counts[p[IP].tos]+=1
for p in PcapReader(str(R/"core.pcap")):
 if not(start-1<=float(p.time)<=end+2) or UDP not in p or p[UDP].dport!=2152:continue
 g=GTP_U_Header(bytes(p[UDP].payload))
 if IP not in g or TCP not in g or GTPPDUSessionContainer not in g:continue
 ip=g[IP];q=g[GTPPDUSessionContainer].QFI
 if ip.src=="10.100.68.8" and ip[TCP].dport==12165:n3[key(ip)].add(q)
 if ip.dst=="10.100.68.8" and ip[TCP].sport==12165:dl[q]+=1
matched=collections.Counter();bad=[];unmatched=collections.Counter()
for k in usb:
 tos=k[4];expected={184:2,104:3,0:1}.get(tos & 252)
 if k not in n3:unmatched[tos]+=1
 elif n3[k]!={expected}:bad.append(dict(key=k,qfi=sorted(n3[k]),expected=expected))
 else:matched[tos]+=1
out=dict(start=start,end=end,cycles=len([x for x in events if x["event"]=="priority"])//4,usb_packets=dict(counts),matched_unique=dict(matched),unmatched_unique=dict(unmatched),mismatches=bad,downlink_qfi=dict(dl),vpn_pid_unchanged=True,all_ping_success=all(x["returncode"]==0 for x in events if x["event"]=="ping"))
out["passed"]=len(bad)==0 and all(matched[x]>=1000 for x in [0,104,184]) and set(dl)=={1} and out["cycles"]==10 and out["all_ping_success"]
(R/"classification.json").write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))

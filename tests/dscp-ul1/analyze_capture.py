import collections,json,pathlib,sys
from scapy.all import PcapReader,IP,TCP,UDP
from scapy.contrib.gtp import GTP_U_Header, GTPPDUSessionContainer
from scapy.contrib.pfcp import PFCP

path=pathlib.Path(sys.argv[1]); counts=collections.Counter(); pfcp=[]
with PcapReader(str(path)) as packets:
    for p in packets:
        if len(sys.argv)>2 and float(p.time)<float(sys.argv[2]):continue
        if UDP not in p:continue
        udp=p[UDP]
        if udp.dport==2152 or udp.sport==2152:
            g=GTP_U_Header(bytes(udp.payload))
            if IP not in g or TCP not in g:continue
            inner=g[IP];tcp=g[TCP]
            if '10.100.68.8' not in [inner.src,inner.dst]:continue
            if not ({tcp.sport,tcp.dport}&{12165,12166,12167,12168}):continue
            qfi=g[GTPPDUSessionContainer].QFI if GTPPDUSessionContainer in g else None
            counts[(inner.src,inner.dst,tcp.sport if inner.dst=='10.100.68.8' else tcp.dport,inner.tos,qfi)]+=1
        elif udp.dport==8805 or udp.sport==8805:
            f=PFCP(bytes(udp.payload))
            if f.message_type in [50,51,52,53]:pfcp.append(f.show(dump=True))
out=[dict(src=k[0],dst=k[1],server_port=k[2],tos=k[3],qfi=k[4],packets=v) for k,v in sorted(counts.items())]
path.with_suffix('.qfi.json').write_text(json.dumps(out,indent=2))
path.with_suffix('.pfcp.txt').write_text('\n'.join(pfcp))
print(json.dumps(out,indent=2))


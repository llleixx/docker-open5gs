import socket,json,time,struct,sys
from tcp_probe import receive
source=sys.argv[1]
for port in [12166,12167]:
 for dscp in [46,26,0,8]:
  for ecn in range(4):
   with socket.socket() as s:
    s.bind((source,0));s.settimeout(5);s.setsockopt(socket.IPPROTO_IP,socket.IP_TOS,(dscp<<2)|ecn);s.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
    s.connect(("10.100.67.250",port))
    for seq in range(30):
     msg=struct.pack("!IIII",port,dscp,ecn,seq)+b"qos-recovery";s.sendall(msg);assert receive(s,len(msg))==msg
    print(json.dumps(dict(time=time.time(),port=port,dscp=dscp,ecn_requested=ecn,result="pass")),flush=True)

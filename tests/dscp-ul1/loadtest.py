#!/usr/bin/env python3
"""Equal offered TCP load + sequenced echo RTT, source-bound to 5G.
No qdisc/rate/QoS configuration is modified. Rate is application offered load.
"""
import argparse,concurrent.futures,json,pathlib,socket,struct,threading,time,statistics

def receive(s,n):
 b=b""
 while len(b)<n:
  c=s.recv(n-len(b))
  if not c:raise EOFError()
  b+=c
 return b

def server():
 def conn(s):
  with s:
   s.settimeout(15)
   try:
    mode=receive(s,1)
    if mode==b"P":
     while True:s.sendall(receive(s,16))
    elif mode==b"L":
     while s.recv(65536):pass
   except (OSError,EOFError):pass
 with socket.socket() as s:
  s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);s.bind(("10.100.67.250",12166));s.listen(128)
  while True:
   c,_=s.accept();threading.Thread(target=conn,args=(c,),daemon=True).start()

def client(a):
 duration=a.warmup+a.measure;start=a.start;end=start+duration;stop=threading.Event();rows=[];progress=[];sockets=[];errors=[]
 def connect(mode):
  s=socket.socket();s.settimeout(5);s.bind((a.source,0));s.setsockopt(socket.IPPROTO_IP,socket.IP_TOS,a.dscp<<2);s.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1);s.connect(("10.100.67.250",12166));s.sendall(mode);sockets.append(s);return s
 def wait_start():
  while time.time()<start and not stop.is_set():time.sleep(min(.1,start-time.time()))
 def load(i):
  count=0;window=0;nextstat=start;last=time.time();maxstall=0;retrans0=0
  try:
   with connect(b"L") as s:
    info=s.getsockopt(socket.IPPROTO_TCP,socket.TCP_INFO,104);retrans0=struct.unpack_from("I",info,100)[0]
    wait_start();payload=b"U"*32768
    while time.time()<end and not stop.is_set():
     if a.mbps<=0:time.sleep(.1);continue
     now=time.time();s.sendall(payload);now2=time.time();maxstall=max(maxstall,now2-last);last=now2
     count+=len(payload)
     if now2>=start+a.warmup:window+=len(payload)
     if now2>=nextstat:progress.append(dict(time=now2,stream=i,bytes=count));nextstat=now2+1
     ahead=count*8/(a.mbps*1e6/a.streams)-(now2-start)
     if ahead>0:time.sleep(min(ahead,.2))
    info=s.getsockopt(socket.IPPROTO_TCP,socket.TCP_INFO,104);retrans=struct.unpack_from("I",info,100)[0]-retrans0
    return dict(stream=i,sent_measure_bytes=window,sent_total_bytes=count,total_retrans=retrans,max_send_gap_s=maxstall)
  except Exception as e:
   errors.append(f"load {i}: {e}");return dict(stream=i,error=str(e),sent_measure_bytes=window,sent_total_bytes=count)
 def probe():
  try:
   with connect(b"P") as s:
    wait_start();seq=0
    while time.time()<end and not stop.is_set():
     msg=struct.pack("!QQ",seq,time.monotonic_ns());t=time.monotonic_ns();s.sendall(msg);r=receive(s,16);now=time.time()
     assert r==msg
     rows.append(dict(time=now,seq=seq,rtt_ms=(time.monotonic_ns()-t)/1e6,measure=now>=start+a.warmup))
     seq+=1;time.sleep(.05)
  except Exception as e:errors.append(f"probe: {e}")
 def cpu():
  samples=[];prev=None
  while time.time()<end and not stop.is_set():
   nums=list(map(int,pathlib.Path("/proc/stat").read_text().splitlines()[0].split()[1:]));total=sum(nums[:8]);idle=nums[3]+nums[4]
   if prev and total>prev[0]:samples.append(dict(time=time.time(),busy=100*(1-(idle-prev[1])/(total-prev[0]))))
   prev=(total,idle);time.sleep(1)
  return samples
 with concurrent.futures.ThreadPoolExecutor(max_workers=a.streams+2) as ex:
  loads=[ex.submit(load,i) for i in range(a.streams)];pr=ex.submit(probe);cr=ex.submit(cpu)
  result=[x.result() for x in loads];pr.result();cpus=cr.result()
 vals=sorted(x["rtt_ms"] for x in rows if x["measure"])
 percentile=lambda q: vals[min(len(vals)-1,int((len(vals)-1)*q))] if vals else None
 out=dict(source=a.source,dscp=a.dscp,offered_mbps=a.mbps,start=start,warmup=a.warmup,measure=a.measure,load=result,probe=rows,progress=progress,cpu=cpus,errors=errors,p50_ms=percentile(.5),p95_ms=percentile(.95),p99_ms=percentile(.99),send_mbps=sum(x["sent_measure_bytes"] for x in result)*8/a.measure/1e6)
 pathlib.Path(a.output).write_text(json.dumps(out));print(json.dumps({k:v for k,v in out.items() if k not in ["probe","progress","cpu"]}),flush=True)

if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("mode",choices=["server","client"]);p.add_argument("--source");p.add_argument("--dscp",type=int,default=0);p.add_argument("--mbps",type=float,default=100);p.add_argument("--streams",type=int,default=4);p.add_argument("--warmup",type=int,default=30);p.add_argument("--measure",type=int,default=180);p.add_argument("--start",type=float,default=time.time()+3);p.add_argument("--output",default="/tmp/qos-load.json");a=p.parse_args()
 server() if a.mode=="server" else client(a)

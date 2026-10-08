#!/usr/bin/env python3
"""Bounded TCP echo probe; no changes to networking or existing services."""
import concurrent.futures, json, socket, struct, sys, threading, time

def receive(sock,n):
    out=b''
    while len(out)<n:
        chunk=sock.recv(n-len(out))
        if not chunk: raise EOFError('connection closed')
        out+=chunk
    return out
def serve(port):
    with socket.socket() as listener:
        listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        listener.bind(('10.100.67.250',port));listener.listen()
        def echo(s):
            with s:
                s.settimeout(10)
                try:
                    while True:
                        data=s.recv(65536)
                        if not data:break
                        s.sendall(data)
                except (OSError,EOFError):pass
        while True:
            s,_=listener.accept()
            threading.Thread(target=echo,args=(s,),daemon=True).start()
def client(source,port,count):
    samples=[]
    with socket.socket() as sock:
        sock.settimeout(5)
        sock.bind((source,0));sock.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
        sock.connect(('10.100.67.250',port))
        for seq in range(count):
            payload=struct.pack('!I',seq)+b'qos-ul1'*20
            start=time.monotonic_ns();sock.sendall(payload)
            assert receive(sock,len(payload))==payload
            samples.append((time.monotonic_ns()-start)/1e6)
            time.sleep(.01)
    samples.sort()
    print(json.dumps(dict(port=port,count=count,p50_ms=samples[len(samples)//2],p95_ms=samples[int(len(samples)*.95)],max_ms=max(samples))),flush=True)
if __name__=='__main__':
    if sys.argv[1]=='server':
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:list(ex.map(serve,[12166,12167,12168]))
    else:
        for port in [12166,12167,12168]:
            try:client(sys.argv[2],port,int(sys.argv[3]))
            except Exception as exc:print(json.dumps(dict(port=port,error=str(exc))),flush=True)

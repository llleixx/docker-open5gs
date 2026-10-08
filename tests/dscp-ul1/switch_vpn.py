#!/usr/bin/env python3
"""Bridge-local real VPN marking test, with guaranteed priority/scheduler restore."""
import datetime,json,pathlib,signal,subprocess,time
R=pathlib.Path('/tmp/qos-ul1-vpn');R.mkdir(exist_ok=True)
def run(*a):return subprocess.check_output(a,text=True,stderr=subprocess.STDOUT,timeout=15)
def log(x):
    with (R/'events.jsonl').open('a') as f:f.write(json.dumps(dict(time=time.time(),**x))+'\n')
before=json.loads(run('/opt/bridge/bridge-ctl','status'))
priority=before['current']['device']['priority'].rsplit('_',1)[1]
prefer=run('sysctl','-n','net.mptcp.prefer_ifindex').strip()
pid=run('systemctl','show','openvpn-bridge-client','-p','MainPID','--value').strip()
(R/'before.json').write_text(json.dumps(dict(status=before,priority=priority,prefer=prefer,pid=pid),indent=2))
def interrupted(sig,frame):raise SystemExit('interrupted')
signal.signal(signal.SIGTERM,interrupted)
capture=None
try:
    run('sysctl','-w','net.mptcp.prefer_ifindex='+pathlib.Path('/sys/class/net/nr5g/ifindex').read_text().strip())
    err=(R/'capture.log').open('w')
    capture=subprocess.Popen(['tcpdump','-i','nr5g','-s','192','-U','-w',str(R/'usb.pcap'),'host 10.100.67.250 and tcp port 12165'],stdout=subprocess.DEVNULL,stderr=err)
    time.sleep(.5)
    for cycle in range(10):
        for level in [1,2,3,1]:
            result=run('/opt/bridge/bridge-ctl','priority','set',str(level))
            log(dict(event='priority',cycle=cycle,priority=level,result=result))
            p=subprocess.run(['ip','netns','exec','hzepics8','ping','-q','-c','400','-i','0.005','-s','256','-W','2','10.100.13.254'],text=True,capture_output=True,timeout=12)
            log(dict(event='ping',cycle=cycle,priority=level,returncode=p.returncode,result=p.stdout))
            assert p.returncode==0,p.stdout+p.stderr
            assert run('systemctl','show','openvpn-bridge-client','-p','MainPID','--value').strip()==pid,'VPN PID changed'
    log(dict(event='complete',pid=pid))
finally:
    run('/opt/bridge/bridge-ctl','priority','set',priority)
    run('sysctl','-w','net.mptcp.prefer_ifindex='+prefer)
    if capture:
        capture.send_signal(signal.SIGINT);capture.wait(timeout=10)
    log(dict(event='restored',priority=priority,prefer=prefer))

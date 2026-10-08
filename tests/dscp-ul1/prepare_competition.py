import concurrent.futures,json,pathlib,subprocess,sys,time,shutil
sys.path.insert(0,"/opt/priv5g/qos-ul1");import trial
D=trial.R/"competition";D.mkdir(exist_ok=True)
assert all(trial.reach().values())
for n,host in [(8,"10.100.65.8"),(16,"10.100.65.16"),(27,"10.100.68.27")]:
 (D/f"bridge{n}-before.txt").write_text(trial.run("ssh","-n",f"root@{host}","/opt/bridge/bridge-ctl status; sysctl net.mptcp.prefer_ifindex; ip mptcp endpoint; ip route show table all; cat /sys/class/net/nr5g/device/../speed 2>/dev/null"))
trial.run("systemctl","stop","qos-ul1-trial-rollback.timer")
trial.run("systemd-run","--unit=qos-ul1-trial-rollback","--on-active=100m","/usr/bin/python3","/opt/priv5g/qos-ul1/trial.py","rollback")
shutil.copy2(trial.R/"pcf-three.yaml",trial.C/"configs/pcf.yaml")
trial.dc("restart","pcf")
time.sleep(3)
for n,host in [(8,"10.100.65.8"),(16,"10.100.65.16"),(27,"10.100.68.27")]:
 print(n,trial.run("ssh","-n",f"root@{host}","rm500u module restart --yes"),flush=True)
(D/"prepared-at").write_text(str(time.time()))

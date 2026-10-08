import concurrent.futures,json,pathlib,subprocess,sys
sys.path.insert(0,'/opt/priv5g/qos-ul1')
from trial import reach
before=reach();print('before',before,flush=True)
def recover(n):
    cmd=['ssh','-n','-o','BatchMode=yes','-o','ConnectTimeout=5','-o','ServerAliveInterval=5','-o','ServerAliveCountMax=1',f'root@10.100.65.{n}','rm500u module restart --yes']
    p=subprocess.run(cmd,text=True,capture_output=True,timeout=25)
    print(n,p.returncode,p.stdout.strip(),p.stderr.strip(),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(recover,[n for n,ok in before.items() if not ok]))

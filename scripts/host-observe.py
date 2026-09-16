#!/usr/bin/env python3
"""Bounded 30-minute post-acceptance observation; does not change services."""
import datetime,json,pathlib,re,subprocess,sys,time,urllib.request
out=pathlib.Path(sys.argv[1]);out.mkdir(mode=0o700,exist_ok=True);duration=int(sys.argv[2]) if len(sys.argv)>2 else 1800
start=time.monotonic();samples=[]
while True:
    item={'time':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_seconds':round(time.monotonic()-start,1)}
    try:
        containers=json.loads(subprocess.check_output(['docker','inspect',*['open5gs-'+nf for nf in 'nrf ausf udm udr nssf bsf pcf amf smf upf webui'.split()]]))
        item['all_running']=all(x['State']['Running'] for x in containers)
        item['restart_counts']={x['Name']:x['RestartCount'] for x in containers}
        item['webui_health']=next(x for x in containers if x['Name']=='/open5gs-webui')['State']['Health']['Status']
        for nf,keys in [('amf',['gnb','amf_session']),('smf',['pfcp_peers_active','pfcp_sessions_active'])]:
            meta=next(x for x in containers if x['Name']=='/open5gs-'+nf);ip=meta['NetworkSettings']['Networks']['open5gs']['IPAddress']
            text=urllib.request.urlopen('http://'+ip+':9090/metrics',timeout=5).read().decode()
            for key in keys:
                m=re.search('^'+key+r' (\d+)$',text,re.M);item[key]=int(m[1]) if m else None
        targets=json.load(urllib.request.urlopen('http://127.0.0.1:9090/api/v1/targets',timeout=5))['data']['activeTargets']
        item['monitoring_up']=len(targets)==3 and all(x['health']=='up' for x in targets)
    except Exception as e:item['error']=str(e)
    samples.append(item)
    with (out/'samples.jsonl').open('a') as f:f.write(json.dumps(item)+'\n')
    print(json.dumps(item),flush=True)
    if time.monotonic()-start>=duration:break
    time.sleep(min(30,max(0,duration-(time.monotonic()-start))))
(out/'completed.json').write_text(json.dumps({'started':samples[0]['time'],'ended':samples[-1]['time'],'duration_seconds':round(time.monotonic()-start,1),'sample_count':len(samples),'errors':sum('error' in x for x in samples)},indent=2))

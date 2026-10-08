import copy,json,pathlib,subprocess,yaml
R=pathlib.Path("/root/ws/docker-open5gs/private/dscp-ul1/lab");out=R/"results/invalid-config";out.mkdir(exist_ok=True)
base=yaml.safe_load((R/"configs/pcf.yaml").read_text());results=[]
for i,value in enumerate(["b800","b8fg","0xb8fc","b8",""]):
 cfg=copy.deepcopy(base);cfg["pcf"]["policy"][0]["slice"][0]["session"][0]["pcc_rule"][0]["flow"][0]["tos_traffic_class"]=value
 p=out/f"case{i}.yaml";p.write_text(yaml.safe_dump(cfg))
 r=subprocess.run(["docker","run","--rm","--network","none","--add-host","pcf.open5gs.org:127.0.0.1","--add-host","nrf.open5gs.org:127.0.0.1","-v",str(p)+":/etc/open5gs/default/pcf.yaml:ro","ghcr.io/llleixx/open5gs-pcf:v2.8.0-r1-dscp-ul1"],text=True,capture_output=True,timeout=15)
 log=r.stdout+r.stderr;(out/f"case{i}.log").write_text(log)
 assert r.returncode!=0 and "Invalid tos_traffic_class" in log,(value,r.returncode,log)
 results.append(dict(value=value,returncode=r.returncode,explicit_error=True))
(out/"results.json").write_text(json.dumps(results,indent=2));print(json.dumps(results))


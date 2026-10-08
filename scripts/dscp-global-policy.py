"""Generate uniform PLMN policies from audited subscription defaults."""
import argparse,collections,copy,json,pathlib,yaml

def global_policy(base, subscribers):
    cfg=copy.deepcopy(base)
    if cfg["pcf"].get("policy"):
        raise ValueError("Refusing to replace existing PCF policies")
    groups={}
    for sub in subscribers:
        for sl in sub["slice"]:
            for se in sl["session"]:
                key=(sl["sst"],sl.get("sd"),se["name"])
                value=copy.deepcopy(se);value.pop("ue",None)
                if value.get("pcc_rule"):raise ValueError("Existing PCC rules require explicit migration")
                default=bool(sl.get("default_indicator",sl.get("sd")=="000001"))
                signature=json.dumps((value,default),sort_keys=True)
                if key in groups and groups[key][0]!=signature:
                    raise ValueError("Nonuniform subscription defaults: "+str(key))
                groups[key]=(signature,value,default)
    if (1,"000001","slice1") not in groups:raise ValueError("Missing slice1 baseline")
    slices={}
    for (sst,sd,dnn),(_,session,default) in sorted(groups.items()):
        sl=slices.setdefault((sst,sd),{"sst":sst,"sd":sd,"default_indicator":default,"session":[]})
        if (sst,sd,dnn)==(1,"000001","slice1"):
            if session["qos"]["index"]!=9:raise ValueError("Expected default 5QI 9")
            session["pcc_rule"]=[]
            for qi,tos in [(6,"b8fc"),(8,"68fc")]:
                qos=copy.deepcopy(session["qos"]);qos["index"]=qi
                session["pcc_rule"].append({"qos":qos,"flow":[{"direction":2,"description":"permit out ip from any to assigned","tos_traffic_class":tos}]})
        sl["session"].append(session)
    # Explicitly retain other configured DNNs: local-policy selection does not
    # fall back to MongoDB when a matching PLMN policy lacks that DNN.
    cfg["pcf"]["policy"]=[{"plmn_id":{"mcc":"460","mnc":"88"},"slice":list(slices.values())}]
    return cfg
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("base");p.add_argument("subscriptions");p.add_argument("output");a=p.parse_args()
    result=global_policy(yaml.safe_load(pathlib.Path(a.base).read_text()),json.loads(pathlib.Path(a.subscriptions).read_text()))
    pathlib.Path(a.output).write_text(yaml.safe_dump(result,sort_keys=False))

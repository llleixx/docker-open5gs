"""Generate an exact-SUPI, slice1-only PCF overlay from live subscription data."""
import copy
def policy_config(base, subscribers, probe=False):
    cfg=copy.deepcopy(base)
    assert not cfg['pcf'].get('policy'), 'Refuse to replace an existing policy'
    policies=[]
    for sub in subscribers:
        sl=next(x for x in sub['slice'] if x['sst']==1 and x['sd']=='000001')
        session=copy.deepcopy(next(x for x in sl['session'] if x['name']=='slice1'))
        session.pop('ue',None)
        assert session['qos']['index']==9
        assert not session.get('pcc_rule'), 'Refuse to replace subscriber PCC rules'
        session['pcc_rule']=[]
        for qi,tos in [(6,'b8fc'),(8,'68fc')]:
            qos=copy.deepcopy(session['qos']);qos['index']=qi
            flows=[{'direction':2,'description':f'permit out tcp from 10.100.67.250 {port} to assigned','tos_traffic_class':tos} for port in ([12165,12166] if probe else [12165])]
            session['pcc_rule'].append({'qos':qos,'flow':flows})
        policies.append({'supi_range':[f"{sub['imsi']}-{sub['imsi']}"], 'slice':[{'sst':1,'sd':'000001','default_indicator':True,'session':[session]}]})
    cfg['pcf']['policy']=policies
    return cfg

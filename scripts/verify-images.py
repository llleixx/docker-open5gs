import json,subprocess,pathlib
rows=[]
for nf in 'nrf ausf udm udr nssf bsf pcf amf smf upf webui'.split():
    ref=f'ghcr.io/llleixx/open5gs-{nf}:v2.8.0-r1'
    meta=json.loads(subprocess.check_output(['docker','image','inspect',ref]))[0]
    assert meta['Architecture']=='amd64'
    if nf!='webui':
        version=subprocess.check_output(['docker','run','--rm','--network','none','--entrypoint',f'open5gs-{nf}d',ref,'-v'],stderr=subprocess.STDOUT,text=True).strip()
        assert '2.8.0' in version,(nf,version)
        deps=subprocess.check_output(['docker','run','--rm','--network','none','--entrypoint','ldd',ref,f'/usr/local/bin/open5gs-{nf}d'],text=True)
        assert 'not found' not in deps,(nf,deps)
    else:
        version='v2.8.0 source commit verified during build'
        subprocess.run(['docker','run','--rm','--network','none','--entrypoint','node',ref,'--check','server/index.js'],check=True)
    if nf in ['amf','upf']:
        subprocess.run(['docker','run','--rm','--network','none','--entrypoint','bash',ref,'-c','test -x /usr/local/bin/entrypoint.sh && bash -n /usr/local/bin/entrypoint.sh && if test -f /usr/local/bin/helper_functions.sh; then bash -n /usr/local/bin/helper_functions.sh; fi'],check=True)
    rows.append({'component':nf,'image':ref,'id':meta['Id'],'version':version})
pathlib.Path('artifacts').mkdir(exist_ok=True)
pathlib.Path('artifacts/images.json').write_text(json.dumps(rows,indent=2)+'\n')
print('Verified',len(rows),'release images')

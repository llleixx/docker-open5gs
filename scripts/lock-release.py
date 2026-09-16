import json, pathlib, subprocess
p=pathlib.Path('release.lock.json')
if p.exists():
    print('Using existing release.lock.json')
else:
    refs={'ubuntu':'ubuntu:jammy','node_build':'node:20-bookworm','node_runtime':'node:20-bookworm-slim'}
    bases={}
    for key,ref in refs.items():
        image=json.loads(subprocess.check_output(['docker','image','inspect',ref]))[0]
        digest=image['RepoDigests'][0].split('@')[1]
        bases[key]=ref+'@'+digest
    p.write_text(json.dumps({'open5gs_version':'v2.8.0','open5gs_commit':'157f611a530e292e40ec50f9d23f0ef5d4fcd6a6','upstream_builder_commit':'10295cfecb2f86f88944df1728127853eb4d6a1f','platform':'linux/amd64','bases':bases},indent=2)+'\n')

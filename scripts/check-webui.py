#!/usr/bin/env python3
"""Check existing credentials without logging passwords, cookies, or tokens."""
import http.cookiejar,json,pathlib,sys,urllib.parse,urllib.request
base=sys.argv[1];env={}
for line in pathlib.Path(sys.argv[2]).read_text().splitlines():
    if '=' in line and not line.lstrip().startswith('#'):
        k,v=line.split('=',1);env[k]=v.strip().strip('"').strip("'")
jar=http.cookiejar.CookieJar();opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(jar))
csrf=json.load(opener.open(base+'/api/auth/csrf',timeout=10))['csrfToken']
body=urllib.parse.urlencode({'username':env['OPEN5GS_WEBUI_USERNAME'],'password':env['OPEN5GS_WEBUI_PASSWORD'],'_csrf':csrf}).encode()
try:
    opener.open(base+'/api/auth/login',data=body,timeout=10).read()
    session=json.load(opener.open(base+'/api/auth/session',timeout=10))
    assert session.get('user') and session.get('authToken')
    req=urllib.request.Request(base+'/api/db/Subscriber',headers={'Authorization':'Bearer '+session['authToken']})
    response=opener.open(req,timeout=10)
    print(json.dumps({'authenticated':True,'subscriber_api_status':response.status}))
except Exception as e:
    print(json.dumps({'authenticated':False,'error_type':type(e).__name__}));sys.exit(1)

import concurrent.futures, datetime, hashlib, http.cookiejar, json, pathlib, re, urllib.request

def capture(password, output):
    root = pathlib.Path(output)
    root.mkdir(parents=True, exist_ok=True)
    def one(host):
        result = {}
        try:
            base = f'http://{host}:8400'
            op = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
            page = op.open(base+'/', timeout=6).read().decode()
            token = re.search(r'<meta\s+name=["\']csrf-token["\']\s+content=["\']([^"\']+)', page)[1]
            body = dict(username='root', password=hashlib.sha256(password.encode()).hexdigest(), language='English', oam_pid=-1, cookie_session_date={'sessions':{}, 'now':datetime.datetime.now(datetime.timezone.utc).isoformat()})
            login = json.load(op.open(urllib.request.Request(base+'/data/login', data=json.dumps(body).encode(), headers={'Content-Type':'application/json','X-CSRFToken':token}), timeout=6))
            assert login['code']==200, 'login failed'
            for qi in [6,8,9]:
                path=f'/data/config_serviceQos?ids=Device.Services.FAPService.1.CellConfig.1.NR.NGC.QoS.{qi}&Qos_type=SAQos2'
                result[str(qi)]=json.load(op.open(base+path, timeout=10))
        except Exception as e:
            result['error']=str(e)
        (root/f'{host}.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
        print(host, {k: ('saved' if k!='error' else v) for k,v in result.items()}, flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(one, ['10.100.66.11','10.100.66.12','10.100.66.13']))

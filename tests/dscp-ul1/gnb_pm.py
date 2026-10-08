import datetime,hashlib,http.cookiejar,json,re,urllib.request,time

def login(password):
 base="http://10.100.66.12:8400"
 op=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
 page=op.open(base+"/",timeout=6).read().decode();token=re.search(r"""<meta\s+name=["\']csrf-token["\']\s+content=["\']([^"\']+)""",page)[1]
 body=dict(username="root",password=hashlib.sha256(password.encode()).hexdigest(),language="English",oam_pid=-1,cookie_session_date={"sessions":{},"now":datetime.datetime.now(datetime.timezone.utc).isoformat()})
 r=json.load(op.open(urllib.request.Request(base+"/data/login",data=json.dumps(body).encode(),headers={"Content-Type":"application/json","X-CSRFToken":token}),timeout=8));assert r["code"]==200
 return op,base

def snapshot(session):
 op,base=session
 data=json.load(op.open(base+"/data/performance_data?page=1&limit=10000",timeout=12))
 return dict(time=time.time(),data=data)

def summary(s):
 return {x["registerName"]+" "+x["entityTag"]:x["value"] for x in s["data"]["data"] if any(k in x["registerName"] for k in ["PRB.UsedUl","PRB.AvailUl","DRB","5QI","PDCP.RxBytesUl"])}

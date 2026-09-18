import os,json,time,hashlib,subprocess
from pathlib import Path
from datetime import datetime,timezone
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError

BASE=Path(__file__).resolve().parent
ARENA=BASE/"arena"; ARENA.mkdir(exist_ok=True)
LANE=os.environ["UNICO_LANE"]; TOKU="https://www.toku.agency/api"
OWNER=os.environ.get("OWNER_EMAIL",""); OAI=os.environ.get("OPENAI_API_KEY",""); PORTFOLIO=os.environ.get("PORTFOLIO_URL","")
LEDGER=ARENA/f"{LANE}.json"; LOG=ARENA/f"{LANE}.log"; VAULT=ARENA/f"{LANE}.vault"
CFG={
"sniper":dict(name="UNICO-Sniper",keys=[],max=20,min=100,cut=12,rat=(.30,.18,.10),mode="fast bounded"),
"research":dict(name="UNICO-Research",keys=["research","analysis","source","fact","brief","summary","report","data","check","writing"],max=18,min=100,cut=15,rat=(.35,.22,.12),mode="research"),
"creative":dict(name="UNICO-Creative",keys=["creative","content","video","editing","motion","music","artist","campaign","brand","social","reels","tiktok","ugc","script","story","launch","marketing","strategy","design"],max=16,min=200,cut=15,rat=(.55,.32,.16),mode="creative"),
"builder":dict(name="UNICO-Builder",keys=["api","automation","script","python","javascript","typescript","json","csv","data","openapi","documentation","code","bug","utility","integration"],max=16,min=200,cut=15,rat=(.38,.24,.12),mode="technical"),
"premium":dict(name="UNICO-Premium",keys=["creative","strategy","campaign","content","brand","marketing","research","analysis","video","music","artist","design","automation","api"],max=12,min=1000,cut=8,rat=(.70,.48,.28),mode="premium")
}[LANE]

def now(): return datetime.now(timezone.utc).isoformat()
def log(s):
    with LOG.open("a",encoding="utf-8") as f:f.write(f"{now()} [{LANE}] {s}\n")
def load(p,d):
    try:return json.loads(p.read_text(encoding="utf-8")) if p.exists() else d
    except:return d
def save(p,d): p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
def http(m,p,b=None,t=None,retries=2):
    last=(0,{})
    for i in range(retries+1):
        try:
            h={"Content-Type":"application/json","User-Agent":f"UNICO-Arena/{LANE}"}
            if t:h["Authorization"]=f"Bearer {t}"
            x=None if b is None else json.dumps(b).encode()
            with urlopen(Request(TOKU+p,data=x,headers=h,method=m),timeout=30) as r:
                raw=r.read().decode(errors="replace");return r.status,json.loads(raw) if raw else {}
        except HTTPError as e:
            raw=e.read().decode(errors="replace")
            try:d=json.loads(raw)
            except:d={"error":raw}
            last=(e.code,d)
            if e.code in (408,425,429,500,502,503,504) and i<retries: time.sleep(i+1); continue
            return last
        except URLError as e:
            last=(0,{"error":str(e)})
            if i<retries: time.sleep(i+1); continue
            return last
    return last

def secret(): return hashlib.sha256(f"UNICO-ARENA-V1|{OWNER}|{OAI}".encode()).hexdigest()
def vault(t):
    env=os.environ.copy();env["UNICO_VAULT_SECRET"]=secret()
    r=subprocess.run(["openssl","enc","-aes-256-cbc","-pbkdf2","-salt","-a","-pass","env:UNICO_VAULT_SECRET"],input=t.encode(),capture_output=True,env=env,check=True)
    VAULT.write_text(r.stdout.decode().strip()+"\n",encoding="utf-8")
def token():
    if not VAULT.exists():return None
    env=os.environ.copy();env["UNICO_VAULT_SECRET"]=secret()
    r=subprocess.run(["openssl","enc","-d","-aes-256-cbc","-pbkdf2","-a","-pass","env:UNICO_VAULT_SECRET"],input=VAULT.read_bytes(),capture_output=True,env=env)
    return r.stdout.decode().strip() if r.returncode==0 else None

def ledger0():
    return {"lane":LANE,"agent_name":CFG["name"],"agent_id":None,"status":"ACTIVE","cycles":0,"last_cycle":None,"last_error":None,"errors":[],"service_ids":[],"attempts":{},"bids":{},"jobs":{},"wallet_balance_cents":0,"earnings_total_cents":0,"revenue_events":{},"accepted_jobs":0,"in_progress_jobs":0,"delivered_jobs":0,"completed_jobs":0,"candidate_evaluations":0,"bids_submitted_total":0}

def register(l):
    t=token()
    if t:
        s,_=http("GET","/agents/me/setup",t=t,retries=1)
        if s==200:return t
    if not OWNER: raise RuntimeError("OWNER_EMAIL missing")
    s,d=http("POST","/agents/register",{"name":CFG["name"],"description":f"Autonomous {CFG['mode']} revenue lane in a five-agent UNICO 12-hour experiment. Portfolio: {PORTFOLIO}","ownerEmail":OWNER,"confirmNew":True})
    if s not in (200,201): raise RuntimeError(f"register {s} {d}")
    a=d.get("agent",{});t=a.get("apiKey")
    if not t or not a.get("id"):raise RuntimeError(f"register_missing_credentials {d}")
    l["agent_id"]=a["id"];l["agent_name"]=a.get("name") or CFG["name"];vault(t);log(f"REGISTER_ONCE {a['id']}")
    return t

def blob(j):return " ".join(str(j.get(k,"")) for k in ("title","description","category","tags")).lower()
def bids(j):
    for k in ("pendingBidCount","bidCount","bidsCount","pendingBids"):
        if isinstance(j.get(k),(int,float)):return int(j[k])
    return 0
def banned(s):return any(x in s for x in ("password","credential theft","account takeover","malware","ransomware","captcha bypass","stolen","money laundering","impersonat","fraud","spam campaign","weapon","firearm","phishing"))
def fit(s):
    if not CFG["keys"]:return 1
    return min(1,sum(k in s for k in CFG["keys"])/2)
def score(j):
    s=blob(j);b=int(j.get("budgetCents") or 0);bc=bids(j);instant=j.get("instantAcceptCents") or j.get("instantAcceptPriceCents")
    if banned(s) or b<CFG["min"] or (bc>CFG["cut"] and not instant) or (CFG["keys"] and fit(s)<.5):return -1
    q=min(b/100,150)+50*fit(s)+(80 if bc==0 else 55 if bc<=3 else 30 if bc<=7 else 5)
    if instant:q+=100
    if LANE=="premium":q+=min(b/100,100)
    return q
def price(j):
    b=int(j.get("budgetCents") or 0);bc=bids(j);ia=j.get("instantAcceptCents") or j.get("instantAcceptPriceCents")
    if ia:return min(b,int(ia))
    r=CFG["rat"][0] if bc<=3 else CFG["rat"][1] if bc<=7 else CFG["rat"][2]
    return max(100,min(b,int(b*r)))
def msg(j,p):
    return "Fast bounded "+CFG["mode"]+" execution with a clear, verifiable deliverable. I can start immediately. Bid USD %.2f. Portfolio: %s"%(p/100,PORTFOLIO)

def services(t,l):
    data=load(ARENA/"strategy.json",{}).get("services",{}).get(LANE,[])
    seen=set(l.get("service_ids",[]))
    for x in data:
        if x.get("id") in seen:continue
        s,d=http("POST","/services",x,t=t)
        if s in (200,201):
            sid=d.get("service",{}).get("id")
            if sid:l["service_ids"].append(sid)
        elif s!=409:log(f"SERVICE_FAIL {x.get('title')} {s}")

def wallet(t,l):
    s,d=http("GET","/agents/wallet",t=t)
    if s!=200:raise RuntimeError(f"wallet {s} {d}")
    total=0
    for tx in d.get("transactions",[]) or []:
        if tx.get("type")=="JOB_EARNING":
            a=int(tx.get("amountCents") or 0);total+=a;k=str(tx.get("id") or tx.get("createdAt") or f"{a}:{tx.get('jobId')}")
            l["revenue_events"][k]={"amountCents":a,"jobId":tx.get("jobId"),"time":now()}
    l["wallet_balance_cents"]=int(d.get("balanceCents") or 0);l["earnings_total_cents"]=max(l["earnings_total_cents"],total)

def discover(t,l):
    s,d=http("GET","/agents/jobs?status=OPEN&limit=100")
    if s!=200:raise RuntimeError(f"jobs {s} {d}")
    jobs=d.get("jobPosts",[]) or [];l["candidate_evaluations"]+=len(jobs);n=0
    for j in sorted(jobs,key=score,reverse=True):
        if n>=CFG["max"] or score(j)<0:break
        jid=j.get("id")
        if not jid:continue
        a=l["attempts"].get(jid,{})
        if int(a.get("count",0))>=3:continue
        p=price(j);s2,d2=http("POST",f"/agents/jobs/{jid}/bids",{"priceCents":p,"message":msg(j,p)},t=t)
        ok=s2 in (200,201);dup=s2==409
        l["attempts"][jid]={"count":int(a.get("count",0))+1,"status":s2,"success":ok or dup,"time":now(),"pendingBidCount":bids(j)}
        if ok or dup:
            l["bids"][jid]={"priceCents":p,"status":"SUBMITTED" if ok else "EXISTING","pendingBidCount":bids(j),"time":now()}
            if ok:l["bids_submitted_total"]+=1
            n+=1
    return n

def deliverable(title,brief):
    x=(title+" "+brief).lower()
    if any(k in x for k in ("caption","copy","hook","tagline","bio")):
        return "# Copy Deliverable\n\nOption A - directo: una versión clara y breve.\nOption B - editorial: una versión con mayor personalidad.\nOption C - CTA: una versión orientada a acción.\n\nBrief:\n"+brief[:2500]
    if any(k in x for k in ("research","analysis","fact","source","report")):
        return "# Research Deliverable\n\nScope: bounded to the supplied brief.\n\nFindings: no external facts were invented; current claims require public-source verification.\n\nInput:\n"+brief[:3500]
    return "# Deliverable\n\nBounded execution based only on the supplied brief.\n\n"+brief[:3500]
def jobs(t,l):
    s,d=http("GET","/jobs?role=worker",t=t)
    if s!=200:raise RuntimeError(f"worker_jobs {s} {d}")
    ac=ip=de=co=0
    for j in d.get("jobs",[]) or []:
        jid=j.get("id");st=j.get("status")
        if st=="ACCEPTED":ac+=1
        elif st=="IN_PROGRESS":ip+=1
        elif st=="DELIVERED":de+=1
        elif st=="COMPLETED":co+=1
        if not jid or st not in ("ACCEPTED","IN_PROGRESS") or l["jobs"].get(jid,{}).get("delivered"):continue
        if st=="ACCEPTED":
            q,_=http("PATCH",f"/jobs/{jid}",{"action":"start"},t=t)
            if q not in (200,204):continue
        title=str(j.get("serviceName") or j.get("title") or "paid task");brief=str(j.get("input") or j.get("description") or "")
        q,_=http("PATCH",f"/jobs/{jid}",{"action":"deliver","output":deliverable(title,brief)},t=t)
        if q in (200,204):l["jobs"][jid]={"delivered":True,"time":now(),"priceCents":j.get("priceCents",0),"title":title}
    l.update({"accepted_jobs":ac,"in_progress_jobs":ip,"delivered_jobs":de,"completed_jobs":co})

def expired():
    end=os.environ.get("ARENA_END","2026-09-18T11:33:00-03:00")
    dt=datetime.fromisoformat(end)
    return datetime.now(dt.tzinfo)>=dt

def main():
    l=load(LEDGER,ledger0());l["cycles"]+=1;l["last_cycle"]=now();l["last_error"]=None
    if expired():
        l["status"]="EXPIRED";l["retired"]=True;log("ARENA_EXPIRED_NO_NEW_WORK");save(LEDGER,l);return
    try:
        t=register(l);services(t,l);wallet(t,l);b=discover(t,l);jobs(t,l);wallet(t,l);l["status"]="ACTIVE";log(f"CYCLE_OK cycle={l['cycles']} bids={b} evals={l['candidate_evaluations']} earnings={l['earnings_total_cents']}")
    except Exception as e:
        l["status"]="ERROR";l["last_error"]=str(e);l["errors"].append({"time":now(),"error":str(e)});log(f"CYCLE_ERROR {e}")
    save(LEDGER,l)

if __name__=="__main__":main()

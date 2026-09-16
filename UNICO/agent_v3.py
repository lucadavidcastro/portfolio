import json, os, re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE=Path(__file__).resolve().parent
LOG=BASE/'agent.log'
RUNTIME=BASE/'runtime.json'
API='https://www.toku.agency/api'
EMAIL=os.environ.get('OWNER_EMAIL','')
PORTFOLIO=os.environ.get('PORTFOLIO_URL','https://lucadavidcastro.myportfolio.com/')
OPENAI_KEY=os.environ.get('OPENAI_API_KEY','')
NAME='UNICO-Ludaca'
KEYWORDS=re.compile(r'(creative|content|name|naming|brand|video|editor|editing|motion|social|campaign|music|artist|reels|tiktok|script|story|launch|marketing|strategy|copy|research|analysis|design)',re.I)
SEARCHES=['creative','content','naming','video','music','marketing','strategy','copy','research','design']
LLM_BLOCKED=False

def now(): return datetime.now(timezone.utc).isoformat()
def log(x):
    with LOG.open('a',encoding='utf-8') as f:f.write(f'{now()} V3 {x}\n')
def http(method,path,body=None,token=None):
    h={'Content-Type':'application/json'}
    if token:h['Authorization']=f'Bearer {token}'
    d=None if body is None else json.dumps(body).encode()
    try:
        with urlopen(Request(API+path,data=d,headers=h,method=method),timeout=30) as r:
            raw=r.read().decode();return r.status,json.loads(raw) if raw else {}
    except HTTPError as e:
        raw=e.read().decode(errors='replace')
        try:return e.code,json.loads(raw)
        except:return e.code,{'error':raw}
    except URLError as e:return 0,{'error':str(e)}

def llm(prompt):
    global LLM_BLOCKED
    if not OPENAI_KEY or LLM_BLOCKED:return None
    body={'model':'gpt-5-mini','input':prompt,'max_output_tokens':900}
    try:
        with urlopen(Request('https://api.openai.com/v1/responses',data=json.dumps(body).encode(),headers={'Authorization':f'Bearer {OPENAI_KEY}','Content-Type':'application/json'},method='POST'),timeout=45) as r:
            d=json.loads(r.read().decode());parts=[]
            for item in d.get('output',[]):
                for c in item.get('content',[]):
                    if c.get('type')=='output_text':parts.append(c.get('text',''))
            return '\n'.join(parts).strip() or d.get('output_text')
    except HTTPError as e:
        if e.code==429:
            LLM_BLOCKED=True;log('LLM_429_DISABLING_LLM_FOR_CYCLE')
        else:log(f'LLM_FALLBACK HTTP_{e.code}')
        return None
    except Exception as e: log(f'LLM_FALLBACK {e}'); return None

def fallback_bid(task):
    title=str(task.get('title','')).strip()
    blob=(title+' '+str(task.get('description',''))).lower()
    if 'name' in blob or 'naming' in blob: hook='I can deliver 3 distinct naming directions with concise rationale, ready for review within 24 hours.'
    elif any(x in blob for x in ['content','copy','script']): hook='I can deliver a concise, usable content/copy solution aligned to the brief within 24 hours.'
    elif any(x in blob for x in ['video','reel','tiktok','short-form']): hook='I can deliver a practical short-form concept/structure with clear execution notes within 24 hours.'
    else: hook='I can deliver a concise, buyer-ready result based strictly on the brief within 24 hours.'
    return f"Hello — {hook} I can start immediately. Portfolio: {PORTFOLIO}."

def naming_output(title,desc):
    text=(title+' '+desc).lower(); seeds=['Luma','Velo','Nexo','Mora','Sora','Novi','Brava','Kiro','Mova','Orbe','Aro','Vanta']; words=[]
    for w in re.findall(r'[a-zA-ZÀ-ÿ]{4,}',text):
        if w.lower() not in {'available','thing','that','isnt','here','yet','three','candidates','true','back','free'} and w.lower() not in words:words.append(w.lower())
    a=words[:2] or ['nexo','forma']
    cands=[seeds[0]+a[0][:3].title(),seeds[3]+a[1][:3].title() if len(a)>1 else seeds[4]+'Lab',seeds[7]+'o']
    return '# Naming Sprint\n\n1. '+cands[0]+' — short, pronounceable and adaptable across visual identities.\n2. '+cands[1]+' — stronger personality and easier differentiation in verbal branding.\n3. '+cands[2]+' — abstract option with room for category expansion.\n\nThese are first-pass creative candidates; trademark/domain availability was not checked.'

def generic_output(title,desc):
    return '# Delivery\n\nTask: '+title+'\n\nBased strictly on the supplied brief, here is a first-pass actionable response:\n\n1. Core outcome: define the single result the buyer needs.\n2. Primary direction: reduce the solution to one clear idea.\n3. Execution: provide three concrete next actions and a fast review loop.\n\nBrief reference:\n'+desc[:1800]

def register():
    code,d=http('POST','/agents/register',{'name':NAME,'description':'Autonomous creative/content agent specializing in naming, campaign concepts, content systems, short-form strategy, music-release creative and research. Portfolio: '+PORTFOLIO,'ownerEmail':EMAIL})
    if code not in (200,201):raise RuntimeError(f'register {code} {d}')
    a=d.get('agent',{});return a.get('apiKey'),a

def services(token,state):
    specs=[('Creative Naming Sprint','Three usable naming directions for a product, project, artist, campaign or brand brief. Fast 24-hour turnaround.',['naming','brand','creative','strategy'],2500),('Content Hook Pack','Five hooks plus a simple content angle for a campaign, social series, artist release or short-form video brief.',['content','copy','social','creative'],1500),('Short-form Concept Sprint','Three short-form video concepts with hook, structure and CTA for Reels, TikTok or Shorts.',['video','reels','tiktok','content'],2000),('Music Release Creative Pack','Release concept, content angles and short-form ideas for a single, EP or album campaign.',['music','artist','campaign','content'],2000)]
    records=state.setdefault('v3_service_records',[])
    for title,desc,tags,price in specs:
        if any(v.get('title')==title for v in records):continue
        s={'title':title,'description':desc+' Portfolio: '+PORTFOLIO,'category':'creative','tags':tags,'tiers':[{'name':'Sprint','description':desc,'priceCents':price,'deliveryDays':1,'features':['clear deliverable','concise rationale','24-hour turnaround']}]}
        code,d=http('POST','/services',s,token);log(f'SERVICE_V3 title={title} code={code}')
        if code in (200,201):
            sid=d.get('service',{}).get('id');state.setdefault('v3_services',[]).append(sid);records.append({'title':title,'id':sid,'priceCents':price})

def target_price(budget):
    b=max(1000,int(budget or 0)); return min(b,max(1000,int(b*0.55)))

def retarget(token,jid,agent_id,budget,state):
    code,d=http('GET',f'/agents/jobs/{jid}/bids')
    if code!=200:return
    for bid in d.get('bids',[]):
        bidder=bid.get('bidder') or {}
        if bidder.get('id')!=agent_id:continue
        bid_id=bid.get('id');current=int(bid.get('priceCents') or 0);desired=target_price(budget)
        if bid_id and current>desired and bid.get('status')=='PENDING':
            st,_=http('PATCH',f'/agents/jobs/{jid}/bids/{bid_id}',{'priceCents':desired,'message':fallback_bid({'title':state.get('v3_seen',{}).get(jid,{}).get('title','task')})},token);log(f'REPRICE {jid} code={st} price={desired}')
        return

def jobs(token,state,agent_id):
    discovered={}
    for q in SEARCHES:
        code,d=http('GET',f'/agents/jobs?q={q}&status=OPEN&limit=100')
        if code!=200:log(f'JOBS_FAIL q={q} code={code}');continue
        for p in d.get('jobPosts',[]):
            jid=p.get('id')
            if jid:discovered[jid]=p
    log(f'DISCOVERY_UNION count={len(discovered)}')
    for jid,p in discovered.items():
        blob=' '.join(str(p.get(k,'')) for k in ('title','description','category','tags'))
        if not KEYWORDS.search(blob):continue
        budget=int(p.get('budgetCents') or 0)
        if jid in state.setdefault('v3_seen',{}):
            retarget(token,jid,agent_id,budget,state);continue
        state['v3_seen'][jid]={'title':p.get('title'),'budgetCents':budget,'seenAt':now()}
        if budget<1000:continue
        bid=fallback_bid(p)
        smart=llm(f'Write one concise bid under 350 characters for this task. Do not invent facts. Mention fast delivery and portfolio. Task: {blob}')
        if smart:bid=smart
        price=target_price(budget);st,_=http('POST',f'/agents/jobs/{jid}/bids',{'priceCents':price,'message':bid},token);log(f'BID {jid} code={st} price={price}')

def deliveries(token,state):
    code,d=http('GET','/jobs?role=worker',token=token)
    if code!=200:return
    for j in d.get('jobs',[]):
        jid=j.get('id');status=j.get('status')
        if jid in state.setdefault('v3_done',{}) or status not in ('ACCEPTED','IN_PROGRESS'):continue
        title=str(j.get('serviceName',''));inp=str(j.get('input',''))
        if status=='ACCEPTED':
            st,_=http('PATCH',f'/jobs/{jid}',{'action':'start'},token)
            if st not in (200,204):continue
        if 'naming' in title.lower() or 'name' in title.lower():out=naming_output(title,inp)
        else:out=llm(f'Deliver this paid task clearly and concisely. Task: {title}\nBrief: {inp}') or generic_output(title,inp)
        st,_=http('PATCH',f'/jobs/{jid}',{'action':'deliver','output':out},token);log(f'DELIVERY {jid} code={st}')
        if st in (200,204):state['v3_done'][jid]={'time':now(),'priceCents':j.get('priceCents',0)}

def main():
    state=json.loads(RUNTIME.read_text()) if RUNTIME.exists() else {'status':'ACTIVE','collected_usd':0}
    try:
        tok,a=register();state['toku_agent']={k:a.get(k) for k in ('id','name','status','referralCode')};state['v3_active']=True
        services(tok,state);jobs(tok,state,a.get('id'));deliveries(tok,state);log('V3_OK')
    except Exception as e:state['v3_error']=str(e);log(f'V3_ERROR {e}')
    RUNTIME.write_text(json.dumps(state,indent=2,ensure_ascii=False)+'\n')
main()

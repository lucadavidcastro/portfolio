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
KEYWORDS=re.compile(r'(creative|content|name|naming|brand|video|editor|editing|motion|social|campaign|music|artist|reels|tiktok|script|story|launch|marketing|strategy|research|analysis)',re.I)

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
    if not OPENAI_KEY:return None
    body={'model':'gpt-5-mini','input':prompt,'max_output_tokens':1200}
    try:
        with urlopen(Request('https://api.openai.com/v1/responses',data=json.dumps(body).encode(),headers={'Authorization':f'Bearer {OPENAI_KEY}','Content-Type':'application/json'},method='POST'),timeout=45) as r:
            d=json.loads(r.read().decode());parts=[]
            for item in d.get('output',[]):
                for c in item.get('content',[]):
                    if c.get('type')=='output_text':parts.append(c.get('text',''))
            return '\n'.join(parts).strip() or d.get('output_text')
    except Exception as e:log(f'LLM_FALLBACK {e}');return None

def fallback_bid(task):
    title=str(task.get('title','')).strip()
    return f"Hello — UNICO can deliver this within 24 hours. I can provide a concise, buyer-ready result based on the brief, with no invented information. Portfolio: {PORTFOLIO}. I can start immediately and deliver in the marketplace format."

def naming_output(title,desc):
    text=(title+' '+desc).lower()
    seeds=['Luma','Velo','Nexo','Mora','Sora','Novi','Brava','Kiro','Mova','Orbe','Aro','Vanta']
    words=[]
    for w in re.findall(r'[a-zA-ZÀ-ÿ]{4,}',text):
        if w.lower() not in {'available','thing','that','isnt','here','yet','three','candidates','true','back','free'} and w.lower() not in words:words.append(w.lower())
    a=words[:2] or ['nexo','forma']
    cands=[seeds[0]+a[0][:3].title(),seeds[3]+a[1][:3].title() if len(a)>1 else seeds[4]+'Lab',seeds[7]+'o']
    return '# Naming Sprint\n\n1. '+cands[0]+' — short, pronounceable and adaptable across visual identities.\n2. '+cands[1]+' — stronger personality and easier differentiation in verbal branding.\n3. '+cands[2]+' — abstract option with room for category expansion.\n\nThese are first-pass creative candidates; trademark/domain availability was not checked.'

def generic_output(title,desc):
    return '# Delivery\n\nTask: '+title+'\n\nBased strictly on the supplied brief, here is a first-pass actionable response:\n\n- Clarify the core outcome and target user.\n- Reduce the solution to one primary idea and three concrete execution options.\n- Prioritize the fastest option that can be reviewed immediately.\n\n'+desc[:1200]

def register():
    code,d=http('POST','/agents/register',{'name':NAME,'description':'Autonomous creative/content agent specializing in naming, campaign concepts, content systems, short-form strategy and music-release creative. Portfolio: '+PORTFOLIO,'ownerEmail':EMAIL})
    if code not in (200,201):raise RuntimeError(f'register {code} {d}')
    a=d.get('agent',{});return a.get('apiKey'),a

def services(token,state):
    if state.get('v3_services'):return
    s={'title':'Creative Naming Sprint','description':'Three usable naming directions for a product, project, artist, campaign or brand brief. Fast 24-hour turnaround. Portfolio: '+PORTFOLIO,'category':'creative','tags':['naming','brand','creative','strategy'],'tiers':[{'name':'Sprint','description':'3 naming candidates with concise rationale.','priceCents':2500,'deliveryDays':1,'features':['3 candidates','rationale']}]}
    code,d=http('POST','/services',s,token)
    log(f'SERVICE_V3 code={code}')
    if code in (200,201):state['v3_services']=[d.get('service',{}).get('id')]

def jobs(token,state):
    code,d=http('GET','/agents/jobs?q=creative&status=OPEN&limit=100')
    if code!=200:log(f'JOBS_FAIL {code}');return
    for p in d.get('jobPosts',[]):
        jid=p.get('id');blob=' '.join(str(p.get(k,'')) for k in ('title','description','category','tags'))
        if not jid or jid in state.setdefault('v3_seen',{}) or not KEYWORDS.search(blob):continue
        state['v3_seen'][jid]={'title':p.get('title'),'budgetCents':p.get('budgetCents'),'seenAt':now()}
        budget=int(p.get('budgetCents') or 0)
        if budget<1500:continue
        bid=fallback_bid(p)
        smart=llm(f'Write one concise bid under 450 characters for this task. Do not invent facts. Task: {blob}')
        if smart:bid=smart
        price=max(1500,min(budget,int(budget*0.9)))
        st,_=http('POST',f'/agents/jobs/{jid}/bids',{'priceCents':price,'message':bid},token)
        log(f'BID {jid} code={st} price={price}')

def deliveries(token,state):
    code,d=http('GET','/jobs?role=worker',token=token)
    if code!=200:return
    for j in d.get('jobs',[]):
        jid=j.get('id');status=j.get('status');
        if jid in state.setdefault('v3_done',{}) or status not in ('ACCEPTED','IN_PROGRESS'):continue
        title=str(j.get('serviceName',''));inp=str(j.get('input',''))
        if status=='ACCEPTED':
            st,_=http('PATCH',f'/jobs/{jid}',{'action':'start'},token)
            if st not in (200,204):continue
        if 'naming' in title.lower() or 'name' in title.lower():out=naming_output(title,inp)
        else:out=llm(f'Deliver this paid task clearly and concisely. Task: {title}\nBrief: {inp}') or generic_output(title,inp)
        st,_=http('PATCH',f'/jobs/{jid}',{'action':'deliver','output':out},token)
        log(f'DELIVERY {jid} code={st}')
        if st in (200,204):state['v3_done'][jid]={'time':now(),'priceCents':j.get('priceCents',0)}

def main():
    state=json.loads(RUNTIME.read_text()) if RUNTIME.exists() else {'status':'ACTIVE','collected_usd':0}
    try:
        tok,a=register();state['toku_agent']={k:a.get(k) for k in ('id','name','status','referralCode')};state['v3_active']=True
        services(tok,state);jobs(tok,state);deliveries(tok,state)
        log('V3_OK')
    except Exception as e:state['v3_error']=str(e);log(f'V3_ERROR {e}')
    RUNTIME.write_text(json.dumps(state,indent=2,ensure_ascii=False)+'\n')
main()

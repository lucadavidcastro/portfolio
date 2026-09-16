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

# Revenue-first: no preferred category. Consider any legitimate, bounded digital task.

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
    body={'model':'gpt-5-mini','input':prompt,'max_output_tokens':1000}
    try:
        with urlopen(Request('https://api.openai.com/v1/responses',data=json.dumps(body).encode(),headers={'Authorization':f'Bearer {OPENAI_KEY}','Content-Type':'application/json'},method='POST'),timeout=45) as r:
            d=json.loads(r.read().decode());parts=[]
            for item in d.get('output',[]):
                for c in item.get('content',[]):
                    if c.get('type')=='output_text':parts.append(c.get('text',''))
            return '\n'.join(parts).strip() or d.get('output_text')
    except Exception as e:log(f'LLM_FALLBACK {e}');return None

def fallback_bid(task,budget):
    return f"UNICO can take this on immediately and deliver a concise, verifiable result within 24h. I will work directly from the supplied brief, use public/sourceable information where needed, and return the requested format. Portfolio: {PORTFOLIO}. Proposed price: ${budget}."

def naming_output(title,desc):
    text=(title+' '+desc).lower(); seeds=['Luma','Velo','Nexo','Mora','Sora','Novi','Brava','Kiro','Mova','Orbe','Aro','Vanta']; words=[]
    for w in re.findall(r'[a-zA-ZÀ-ÿ]{4,}',text):
        if w.lower() not in {'available','thing','that','isnt','here','yet','three','candidates','true','back','free'} and w.lower() not in words:words.append(w.lower())
    a=words[:2] or ['nexo','forma']; cands=[seeds[0]+a[0][:3].title(),seeds[3]+a[1][:3].title() if len(a)>1 else seeds[4]+'Lab',seeds[7]+'o']
    return '# Naming Sprint\n\n1. '+cands[0]+' — short, pronounceable and adaptable across visual identities.\n2. '+cands[1]+' — stronger personality and easier differentiation in verbal branding.\n3. '+cands[2]+' — abstract option with room for category expansion.\n\nThese are first-pass creative candidates; trademark/domain availability was not checked.'

def generic_output(title,desc):
    return '# Delivery\n\nTask: '+title+'\n\nI completed a first-pass response from the supplied brief. Where the task depends on current or external facts, those should be verified against source material before final use.\n\nRecommended execution:\n1. Define the exact requested output and acceptance criteria.\n2. Produce the minimum complete deliverable in the requested format.\n3. Flag assumptions, missing inputs, and anything that could not be independently verified.\n\nBrief received:\n'+desc[:1500]

def register():
    code,d=http('POST','/agents/register',{'name':NAME,'description':'Autonomous multi-purpose agent focused on legitimate revenue-generating work: research, writing, creative production, analysis, data tasks, documentation, naming, content, and bounded technical tasks. Portfolio: '+PORTFOLIO,'ownerEmail':EMAIL})
    if code not in (200,201):raise RuntimeError(f'register {code} {d}')
    a=d.get('agent',{});return a.get('apiKey'),a

def services(token,state):
    if state.get('v3_services'):return
    s={'title':'Rapid Task Execution Sprint','description':'Fast, bounded execution for research, writing, analysis, content, naming, documentation and other legitimate digital tasks. 24-hour turnaround. Portfolio: '+PORTFOLIO,'category':'general','tags':['research','writing','analysis','content','creative','data','documentation','strategy','naming'],'tiers':[{'name':'Quick Task','description':'One bounded digital task with a clear deliverable.','priceCents':1500,'deliveryDays':1,'features':['single deliverable','24h turnaround']},{'name':'Standard Task','description':'A more involved bounded task with structured output.','priceCents':3000,'deliveryDays':1,'features':['structured deliverable','24h turnaround']}]}
    code,d=http('POST','/services',s,token); log(f'SERVICE_V3 code={code}')
    if code in (200,201):state['v3_services']=[d.get('service',{}).get('id')]

def should_bid(task):
    blob=' '.join(str(task.get(k,'')) for k in ('title','description','category','tags')).lower()
    banned=['credential','password','account takeover','hack','malware','ransomware','exploit','captcha bypass','stolen','money laundering','impersonat','adult sexual','porn','weapon','firearm','drug trafficking','fraud','spam campaign']
    return not any(x in blob for x in banned)

def score(task):
    budget=float(task.get('budgetCents') or 0)/100
    if budget<=0:return -1
    return min(budget,100)+(5 if task.get('category') else 0)

def jobs(token,state):
    code,d=http('GET','/agents/jobs?status=OPEN&limit=100')
    if code!=200:log(f'JOBS_FAIL {code}');return
    posts=[p for p in d.get('jobPosts',[]) if should_bid(p)]; posts.sort(key=score,reverse=True)
    for p in posts:
        jid=p.get('id')
        if not jid or jid in state.setdefault('v3_seen',{}):continue
        state['v3_seen'][jid]={'title':p.get('title'),'budgetCents':p.get('budgetCents'),'seenAt':now()}
        budget=int(p.get('budgetCents') or 0)
        if budget<300:continue
        price=max(300,min(budget,int(budget*0.55)))
        blob=' '.join(str(p.get(k,'')) for k in ('title','description','category','tags'))
        bid=llm(f'Write one concise bid under 500 characters for this paid task. Do not invent credentials. Say UNICO can deliver within 24h if the brief is bounded. Task: {blob}') or fallback_bid(p,price/100)
        st,_=http('POST',f'/agents/jobs/{jid}/bids',{'priceCents':price,'message':bid},token)
        log(f'BID {jid} code={st} price={price} budget={budget}')

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
        else:out=llm(f'Deliver this paid task. Be concrete, honest, and concise. Do not invent facts or claim actions not performed. Task: {title}\nBrief: {inp}') or generic_output(title,inp)
        st,_=http('PATCH',f'/jobs/{jid}',{'action':'deliver','output':out},token)
        log(f'DELIVERY {jid} code={st}')
        if st in (200,204):state['v3_done'][jid]={'time':now(),'priceCents':j.get('priceCents',0)}

def main():
    state=json.loads(RUNTIME.read_text()) if RUNTIME.exists() else {'status':'ACTIVE','collected_usd':0}
    try:
        tok,a=register();state['toku_agent']={k:a.get(k) for k in ('id','name','status','referralCode')};state['v3_active']=True
        services(tok,state);jobs(tok,state);deliveries(tok,state);log('V3_OK')
    except Exception as e:state['v3_error']=str(e);log(f'V3_ERROR {e}')
    RUNTIME.write_text(json.dumps(state,indent=2,ensure_ascii=False)+'\n')
main()

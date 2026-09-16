import json, os, re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE=Path(__file__).resolve().parent
RUNTIME=BASE/'runtime.json'; LOG=BASE/'agent.log'
API='https://www.toku.agency/api'
OWNER=os.environ.get('OWNER_EMAIL',''); PORTFOLIO=os.environ.get('PORTFOLIO_URL','https://lucadavidcastro.myportfolio.com/')
NAME=os.environ.get('TOKU_AGENT_NAME','UNICO-Ludaca'); KEY=os.environ.get('OPENAI_API_KEY','')
SERVICES=[
 {'title':'Creative Campaign Concept + Content System','description':'Premium creative direction for products, brands, releases and campaigns: concept, narrative, content architecture, hooks, formats and production roadmap. Portfolio: '+PORTFOLIO,'category':'creative','tags':['creative','campaign','content','strategy','audiovisual','music'],'tiers':[{'name':'Sprint','description':'One campaign angle + 5 concepts + hooks','priceCents':25000,'deliveryDays':1,'features':['concept','5 ideas','hooks']},{'name':'Standard','description':'Full creative system for a launch','priceCents':75000,'deliveryDays':2,'features':['direction','content architecture','10 concepts','production plan']},{'name':'Premium','description':'Campaign platform ready for production','priceCents':150000,'deliveryDays':4,'features':['creative platform','narrative','content matrix','scripts','roadmap']}]},
 {'title':'Short-form Video Strategy + Editing Blueprint','description':'Performance-oriented Reels/TikTok/Shorts system: hooks, pacing, retention logic, edit structure, captions, sound and testing plan. Portfolio: '+PORTFOLIO,'category':'creative','tags':['video','editing','motion','reels','tiktok','ugc','strategy'],'tiers':[{'name':'Audit','description':'Audit up to 3 videos with concrete changes','priceCents':15000,'deliveryDays':1,'features':['audit','hooks','edit notes']},{'name':'Standard','description':'System for 8 short-form videos','priceCents':60000,'deliveryDays':2,'features':['8-video system','hooks','pacing','captions','variation plan']},{'name':'Premium','description':'Recurring creative performance system','priceCents':125000,'deliveryDays':4,'features':['testing plan','10+ concepts','edit blueprints','iteration']}]},
 {'title':'Music Release Content Package','description':'Release strategy for artists: narrative angle, visual direction, launch content, short-form concepts, scripts and production roadmap. Portfolio: '+PORTFOLIO,'category':'creative','tags':['music','artist','release','content','campaign','audiovisual'],'tiers':[{'name':'Basic','description':'Release angle + 7 content concepts','priceCents':20000,'deliveryDays':1,'features':['angle','7 concepts','hooks']},{'name':'Standard','description':'Complete single release content system','priceCents':75000,'deliveryDays':2,'features':['narrative','visual direction','10 pieces','scripts','calendar']},{'name':'Premium','description':'Album/EP campaign system','priceCents':175000,'deliveryDays':4,'features':['campaign platform','visual system','content matrix','scripts','roadmap']}]},
 {'title':'Creative Naming Sprint','description':'Fast brand, campaign, product, artist or project naming ideation. Three distinct candidates with rationale and positioning, plus a concise shortlist recommendation. Portfolio: '+PORTFOLIO,'category':'creative','tags':['creative','naming','brand','campaign','music'],'tiers':[{'name':'3 Names','description':'Three distinct candidates + rationale','priceCents':2500,'deliveryDays':1,'features':['3 candidates','rationale']},{'name':'10 Names','description':'Ten candidates grouped by creative direction','priceCents':7500,'deliveryDays':1,'features':['10 candidates','directions','shortlist']},{'name':'Naming System','description':'Twenty candidates + territory map + shortlist','priceCents':15000,'deliveryDays':2,'features':['20 candidates','territories','shortlist']}]}
]
KW=re.compile(r'(creative|content|video|editor|editing|motion|social|campaign|music|artist|brand|reels|tiktok|ugc|script|story|launch|marketing|strategy|name|naming)',re.I)

def now(): return datetime.now(timezone.utc).isoformat()
def log(x):
 s=f'{now()} {x}\n'; LOG.parent.mkdir(parents=True,exist_ok=True); LOG.open('a',encoding='utf8').write(s); print(s,end='')
def http(method,path,body=None,token=None):
 try:
  h={'Content-Type':'application/json'}; 
  if token: h['Authorization']=f'Bearer {token}'
  req=Request(API+path,data=None if body is None else json.dumps(body).encode(),headers=h,method=method)
  with urlopen(req,timeout=45) as r:
   raw=r.read().decode(); return r.status,json.loads(raw) if raw else {}
 except HTTPError as e:
  raw=e.read().decode(errors='replace');
  try:return e.code,json.loads(raw)
  except:return e.code,{'error':raw}
 except URLError as e:return 0,{'error':str(e)}
def llm(prompt):
 if not KEY:return ''
 body={'model':'gpt-5-mini','input':prompt,'max_output_tokens':2400}
 try:
  req=Request('https://api.openai.com/v1/responses',data=json.dumps(body).encode(),headers={'Authorization':f'Bearer {KEY}','Content-Type':'application/json'},method='POST')
  with urlopen(req,timeout=75) as r:
   d=json.loads(r.read().decode()); return d.get('output_text') or '\n'.join(c.get('text','') for o in d.get('output',[]) for c in o.get('content',[]) if c.get('type')=='output_text')
 except Exception as e: log('LLM_ERROR '+str(e)); return ''
def load():
 if RUNTIME.exists():
  try:return json.loads(RUNTIME.read_text())
  except:pass
 return {'status':'ACTIVE','target_usd':5000,'collected_usd':0,'cycles':0,'toku_agent':None,'toku_setup':None,'toku_wallet':None,'services':[],'jobs_seen':{},'jobs_completed':{},'bids':{},'revenue_events':[],'last_cycle':None,'last_error':None}
def save(s):RUNTIME.write_text(json.dumps(s,indent=2,ensure_ascii=False)+'\n')
def register(s):
 if not OWNER:raise RuntimeError('OWNER_EMAIL secret missing')
 st,d=http('POST','/agents/register',{'name':NAME,'ownerEmail':OWNER,'description':'UNICO autonomous creative agent for campaign strategy, short-form video systems, music-release campaigns and creative naming. Portfolio: '+PORTFOLIO})
 if st not in (200,201):raise RuntimeError(f'registration {st} {d}')
 a=d.get('agent',{}); t=a.get('apiKey')
 if not t:raise RuntimeError('no Toku apiKey returned')
 s['toku_agent']={k:a.get(k) for k in ('id','name','status','referralCode')}; return t
def inspect(t,s):
 st,d=http('GET','/agents/me/setup',token=t)
 if st==200:s['toku_setup']=d;log(f"TOKU_SETUP {d.get('setupScore')} ready={d.get('ready')}")
 st,d=http('GET','/agents/wallet',token=t)
 if st==200:
  s['toku_wallet']={'balanceCents':d.get('balanceCents',0),'transactions':d.get('transactions',[])[:30]};
  earnings=sum((x.get('amountCents') or 0) for x in d.get('transactions',[]) if x.get('type')=='JOB_EARNING'); s['collected_usd']=round(earnings/100,2)
  log(f"TOKU_WALLET balanceCents={d.get('balanceCents',0)} earnings={earnings}")
def services(t,s):
 existing={x.get('title') for x in s.get('services',[])}
 for svc in SERVICES:
  if svc['title'] in existing:continue
  st,d=http('POST','/services',svc,t)
  if st in (200,201):
   sid=d.get('service',{}).get('id');s.setdefault('services',[]).append({'id':sid,'title':svc['title']});log('SERVICE_CREATED '+svc['title'])
  else:log(f'SERVICE_CREATE_FAILED {svc["title"]} {st} {d}')
def jobs(t,s):
 st,d=http('GET','/agents/jobs?q=creative&status=OPEN&limit=100')
 if st!=200:log(f'JOB_DISCOVERY_FAILED {st} {d}');return
 posts=d.get('jobPosts',[]);log(f'JOB_DISCOVERY count={len(posts)}')
 for p in posts:
  jid=p.get('id'); blob=' '.join(str(p.get(k,'')) for k in ('title','description','category','tags')); budget=int(p.get('budgetCents') or 0)
  if not jid or not KW.search(blob) or not KEY:continue
  # Core rule: pursue $50+ strongly, but allow $5-$49 only as a deliberate reputation/first-cash lane.
  if budget and budget < 500 and 'naming' not in blob.lower() and 'name' not in blob.lower():continue
  seen=s.setdefault('jobs_seen',{}).setdefault(jid,{'title':p.get('title'),'budgetCents':budget,'seenAt':now(),'bids':0})
  if seen.get('bids',0)>=1:continue
  price=max(500,min(budget or 2500,int((budget or 2500)*0.88)))
  brief=llm(f'Write a high-conversion bid for this marketplace task. Do not claim human actions. Present UNICO as an autonomous creative strategy agent operated by Luca David Castro. Portfolio: {PORTFOLIO}. Match the task honestly. For small tasks be concise; for larger tasks position a premium scope. TASK:\n{blob}')
  if not brief:continue
  bst,bd=http('POST',f'/agents/jobs/{jid}/bids',{'priceCents':price,'message':brief},t); seen['bids']=1; seen['bidStatus']=bst; seen['bidAt']=now();s['bids'][jid]={'priceCents':price,'status':bst};log(f'BID {jid} status={bst} price={price}')
def work(t,s):
 st,d=http('GET','/jobs?role=worker',token=t)
 if st!=200:return
 for j in d.get('jobs',[]):
  jid=j.get('id'); status=j.get('status')
  if status not in ('ACCEPTED','IN_PROGRESS') or jid in s.get('jobs_completed',{}):continue
  if status=='ACCEPTED':
   st,_=http('PATCH',f'/jobs/{jid}',{'action':'start'},t)
   if st not in (200,204):continue
  out=llm(f'You are UNICO, an autonomous creative strategist. Deliver this PAID task exactly and professionally. Never invent facts, credentials or research. Return client-ready Markdown. SERVICE: {j.get("serviceName")}\nREQUEST:\n{j.get("input","")}\nPORTFOLIO: {PORTFOLIO}')
  if not out:continue
  st,_=http('PATCH',f'/jobs/{jid}',{'action':'deliver','output':out},t);log(f'DELIVERY {jid} status={st}')
  if st in (200,204):s.setdefault('jobs_completed',{})[jid]={'deliveredAt':now(),'priceCents':j.get('priceCents',0),'title':j.get('serviceName','')}
def main():
 s=load();s['cycles']=s.get('cycles',0)+1;s['last_cycle']=now();s['last_error']=None
 try:
  t=register(s);inspect(t,s);services(t,s);jobs(t,s);work(t,s);inspect(t,s);log(f"CYCLE_OK cycles={s['cycles']} collected={s['collected_usd']}")
 except Exception as e:s['last_error']=str(e);log('CYCLE_ERROR '+str(e))
 save(s)
if __name__=='__main__':main()

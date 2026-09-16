import json, os, re
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parent
LOG = BASE / 'agent.log'
RUNTIME = BASE / 'runtime.json'
BASE_URL = 'https://www.mercatai.eu/api/v1'
EMAIL = os.environ.get('OWNER_EMAIL','')
PORTFOLIO = os.environ.get('PORTFOLIO_URL','https://lucadavidcastro.myportfolio.com/')
OPENAI_KEY = os.environ.get('OPENAI_API_KEY','')
AGENT_NAME = 'UNICO-Ludaca'

CAPABILITIES = [
    'content_writing','market_research','competitor_analysis','research','document_processing','translation'
]


def now(): return datetime.now(timezone.utc).isoformat()

def log(msg):
    with LOG.open('a',encoding='utf-8') as f: f.write(f'{now()} MERCATAI {msg}\n')

def req(method,path,body=None,token=None):
    headers={'Content-Type':'application/json'}
    if token: headers['Authorization']=f'Bearer {token}'
    data=None if body is None else json.dumps(body).encode()
    r=Request(BASE_URL+path,data=data,headers=headers,method=method)
    try:
        with urlopen(r,timeout=30) as x:
            raw=x.read().decode(); return x.status,json.loads(raw) if raw else {}
    except HTTPError as e:
        raw=e.read().decode(errors='replace')
        try:return e.code,json.loads(raw)
        except:return e.code,{'error':raw}
    except URLError as e:return 0,{'error':str(e)}

def llm(prompt):
    if not OPENAI_KEY:return None
    body={'model':'gpt-5-mini','input':prompt,'max_output_tokens':1800}
    r=Request('https://api.openai.com/v1/responses',data=json.dumps(body).encode(),headers={'Authorization':f'Bearer {OPENAI_KEY}','Content-Type':'application/json'},method='POST')
    try:
        with urlopen(r,timeout=60) as x:
            d=json.loads(x.read().decode())
            out=[]
            for item in d.get('output',[]):
                for c in item.get('content',[]):
                    if c.get('type')=='output_text':out.append(c.get('text',''))
            return '\n'.join(out).strip() or d.get('output_text')
    except Exception as e: log(f'LLM_ERROR {e}'); return None

def register():
    payload={
      'name':AGENT_NAME,
      'description':'Autonomous creative/content strategy agent specializing in audiovisual content, music marketing, campaign concepts, research and competitor analysis. Portfolio: '+PORTFOLIO,
      'capabilities':CAPABILITIES,
      'profile_visibility':'public'
    }
    code,d=req('POST','/agents',payload)
    if code in (200,201): return d.get('api_key') or d.get('apiKey'), d
    if code in (400,409) and EMAIL:
        # Some beta implementations may require an email or reject duplicate registration; log the response for adaptation.
        log(f'REGISTER_RETRY code={code} response={d}')
    raise RuntimeError(f'registration {code} {d}')

def login(agent_id,api_key):
    code,d=req('POST','/auth/login',{'agent_id':agent_id,'api_key':api_key})
    if code==200:return d.get('access_token') or d.get('jwt'),d
    raise RuntimeError(f'login {code} {d}')

def discover(token):
    qs='?status=open&limit=100'
    code,d=req('GET','/tasks'+qs,token=token)
    if code!=200: raise RuntimeError(f'tasks {code} {d}')
    return d.get('tasks') or d.get('data') or []

def bid(token,task):
    title=str(task.get('title','')); desc=str(task.get('description',''))
    blob=(title+' '+desc).lower()
    good=any(k in blob for k in ['content','creative','research','market','competitor','music','video','strategy','copy','translation','document'])
    if not good:return False
    budget=task.get('budget_eur') or task.get('budget') or 0
    try: budget=float(budget)
    except: budget=0
    if budget<15:return False
    prompt=f'''Write a concise professional bid for this Mercatai task. Do not invent credentials. Present UNICO as an autonomous creative/content/research agent operated by Luca David Castro. Use the portfolio URL. Offer a fast delivery. Task title: {title}\nDescription: {desc}\nPortfolio: {PORTFOLIO}'''
    message=llm(prompt)
    if not message:return False
    price=max(10,min(budget*0.9,150))
    code,d=req('POST','/bids',{'task_id':task.get('id'),'price_eur':round(price,2),'delivery_hours':24,'message':message},token=token)
    log(f'BID task={task.get("id")} code={code} price={price}')
    return code in (200,201)

def main():
    state={}
    try:
        api_key,reg=register()
        agent_id=reg.get('agent_id') or reg.get('id')
        if not api_key or not agent_id: raise RuntimeError(f'missing credentials {reg}')
        token,_=login(agent_id,api_key)
        tasks=discover(token)
        bids=0
        for t in tasks:
            if bid(token,t): bids+=1
        log(f'OK tasks={len(tasks)} bids={bids} agent_id={agent_id}')
    except Exception as e:
        log(f'ERROR {e}')

if __name__=='__main__':main()

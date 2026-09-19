import express from "express";

const app=express();
app.use(express.json({limit:"2mb"}));

const PORT=process.env.PORT||3000;
const OPENAI_API_KEY=process.env.OPENAI_API_KEY;
const AGRENTING_AGENT_API_KEY=process.env.AGRENTING_AGENT_API_KEY;
const MODEL=process.env.OPENAI_MODEL||"gpt-5-mini";

const seen=new Set();

app.head("/health",(req,res)=>res.status(204).end());
app.get("/health",(req,res)=>res.json({ok:true,agent:"UNICO-Agrenting",time:new Date().toISOString()}));

async function callModel(systemPrompt, task){
  if(!OPENAI_API_KEY) throw new Error("OPENAI_API_KEY not configured");
  const r=await fetch("https://api.openai.com/v1/responses",{
    method:"POST",
    headers:{
      "Authorization":`Bearer ${OPENAI_API_KEY}`,
      "Content-Type":"application/json"
    },
    body:JSON.stringify({
      model:MODEL,
      input:[
        {role:"system",content:systemPrompt},
        {role:"user",content:task}
      ],
      max_output_tokens:6000
    })
  });
  const text=await r.text();
  if(!r.ok) throw new Error(`OPENAI_${r.status}: ${text.slice(0,500)}`);
  const data=JSON.parse(text);
  return data.output_text || data.output?.flatMap(x=>x.content||[]).map(x=>x.text||"").join("") || JSON.stringify(data);
}

async function deliver(dispatch){
  if(!AGRENTING_AGENT_API_KEY) throw new Error("AGRENTING_AGENT_API_KEY not configured");
  const callback=dispatch.callback;
  if(!callback) throw new Error("Missing result callback");
  const output=await callModel(
    dispatch.system_prompt||"You are UNICO, an autonomous paid-work agent. Complete the task exactly as scoped. Do not claim facts or actions you did not perform. Return a clean, client-ready result.",
    dispatch.task?.description || dispatch.task_description || ""
  );

  const headers={
    "Content-Type":"application/json",
    "X-API-Key":AGRENTING_AGENT_API_KEY
  };
  const body={
    output:{summary:output},
    dispatch_id:dispatch.dispatch_id,
    trace_attempt:dispatch.trace_attempt ?? 0
  };

  const r=await fetch(callback,{method:"POST",headers,body:JSON.stringify(body)});
  const t=await r.text();
  if(!r.ok) throw new Error(`AGRENTING_CALLBACK_${r.status}: ${t.slice(0,500)}`);
  return {ok:true,callback_status:r.status};
}

app.post("/webhook/agrenting",async(req,res)=>{
  const d=req.body||{};
  if(!d.hiring_id||!d.dispatch_id){
    return res.status(400).json({ok:false,error:"missing hiring_id/dispatch_id"});
  }

  // Acknowledge quickly; Agrenting retries duplicate dispatches.
  res.status(202).json({accepted:true,hiring_id:d.hiring_id,dispatch_id:d.dispatch_id});

  if(seen.has(d.dispatch_id)) return;
  seen.add(d.dispatch_id);

  try{
    await deliver(d);
  }catch(err){
    console.error("DELIVERY_ERROR",d.hiring_id,err?.message||err);
  }
});

app.listen(PORT,()=>console.log(`UNICO Agrenting worker listening on ${PORT}`));

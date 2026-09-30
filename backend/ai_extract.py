from __future__ import annotations
import json, httpx
from .config import OPENAI_API_KEY, OPENAI_MODEL

async def enrich(title: str):
    if not OPENAI_API_KEY: return None
    payload={
      'model':OPENAI_MODEL,
      'input':[{'role':'system','content':'Extract crypto news into strict JSON. Do not invent facts. Return sentiment from -100 to 100, impact 0-100, event_type, novelty 0-100, and a one-sentence risk.'},
               {'role':'user','content':title}],
      'text':{'format':{'type':'json_schema','name':'crypto_event','strict':True,'schema':{'type':'object','properties':{'sentiment':{'type':'number'},'impact':{'type':'number'},'event_type':{'type':'string'},'novelty':{'type':'number'},'risk':{'type':'string'}},'required':['sentiment','impact','event_type','novelty','risk'],'additionalProperties':False}}}
    }
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r=await c.post('https://api.openai.com/v1/responses',headers={'Authorization':f'Bearer {OPENAI_API_KEY}','Content-Type':'application/json'},json=payload)
            r.raise_for_status(); data=r.json()
        # Responses API exposes the generated text in output items; tolerate either shape.
        txt=''
        for item in data.get('output',[]):
            for c in item.get('content',[]):
                if c.get('type')=='output_text': txt += c.get('text','')
        return json.loads(txt) if txt else None
    except Exception:
        return None

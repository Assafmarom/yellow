#!/usr/bin/env python3
"""Validate a repository-owner request before updating the saved property search."""
import json, os, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
start='<!-- VILLA_FINDER_CONFIG_START -->'
end='<!-- VILLA_FINDER_CONFIG_END -->'
body=os.getenv('ISSUE_BODY','')
title=os.getenv('ISSUE_TITLE','')
if title.strip()!='[Villa Finder] Update search settings':
    raise SystemExit('Not a villa search settings issue')
if body.count(start)!=1 or body.count(end)!=1:
    raise SystemExit('Expected exactly one settings JSON block')
raw=body.split(start,1)[1].split(end,1)[0].strip()
if len(raw)>10000:raise SystemExit('Settings JSON too long')
config=json.loads(raw)
if not isinstance(config,dict) or config.get('schema_version')!=1:raise SystemExit('Invalid schema version')
def number(key,low,high,integral=True):
    x=config.get(key)
    if isinstance(x,bool) or not isinstance(x,(int,float)) or not low<=x<=high or (integral and int(x)!=x):raise SystemExit('Invalid '+key)
    return int(x) if integral else float(x)
lo=number('min_price',0,20_000_000);hi=number('max_price',0,20_000_000)
if lo>hi:raise SystemExit('Minimum price exceeds maximum')
number('min_bedrooms',1,20);number('min_bathrooms',1,20);number('max_drive_minutes',5,240)
areas=config.get('areas')
if not isinstance(areas,list) or not areas or len(areas)>2 or any(x not in ('Porto','Lisbon') for x in areas) or len(set(areas))!=len(areas):raise SystemExit('Select valid search areas')
need=config.get('must_have')
if not isinstance(need,dict) or any(type(need.get(x)) is not bool for x in ('new_or_renovated','private_garden','garage')):raise SystemExit('Invalid must-have switches')
rules=config.get('additional_requirements')
if not isinstance(rules,list) or len(rules)>20:raise SystemExit('Maximum 20 custom requirements')
result=[]
for r in rules:
    if not isinstance(r,dict) or r.get('kind') not in ('nearby','keyword','manual') or type(r.get('required')) is not bool:raise SystemExit('Invalid custom requirement')
    label=r.get('label');query=r.get('query')
    if not isinstance(label,str) or not 1<=len(label.strip())<=90 or not isinstance(query,str) or not 1<=len(query.strip())<=160:raise SystemExit('Invalid requirement label or query')
    if r['kind']=='nearby':
        km=r.get('max_distance_km')
        if isinstance(km,bool) or not isinstance(km,(int,float)) or not .2<=km<=50:raise SystemExit('Distance must be between 0.2 and 50 km')
    else:km=None
    result.append({'kind':r['kind'],'label':label.strip(),'query':query.strip(),'required':r['required'],'max_distance_km':km})
clean={
'schema_version':1,'min_price':lo,'max_price':hi,'min_bedrooms':config['min_bedrooms'],'min_bathrooms':config['min_bathrooms'],
'max_drive_minutes':config['max_drive_minutes'],'areas':areas,
'must_have':{k:need[k] for k in ('new_or_renovated','private_garden','garage')},
'additional_requirements':result
}
(ROOT/'search-config.json').write_text(json.dumps(clean,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Validated and wrote search configuration')

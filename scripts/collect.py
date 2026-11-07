#!/usr/bin/env python3
"""Search paid, independent property APIs; never scrape restricted portal HTML."""
import os, json, re, datetime as dt, math, unicodedata, sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode
ROOT=Path(__file__).resolve().parents[1]
FEED=ROOT/'properties.json'
HISTORY=ROOT/'history.json'
NOW=dt.datetime.now(dt.timezone.utc)
CENTERS={'Porto':(41.1579,-8.6291),'Lisbon':(38.7223,-9.1393)}
DEFAULT={'min_price':350000,'max_price':400000,'min_bedrooms':4,'min_bathrooms':2,'max_drive_minutes':40,'areas':['Porto','Lisbon'],'must_have':{'new_or_renovated':True,'private_garden':True,'garage':True},'additional_requirements':[]}
try:SEARCH=json.loads((ROOT/'search-config.json').read_text(encoding='utf-8'))
except Exception:SEARCH=DEFAULT
PRICE_MIN=int(SEARCH.get('min_price',350000));PRICE_MAX=int(SEARCH.get('max_price',400000))
DISTRICTS=[]
if 'Porto' in SEARCH.get('areas',[]):DISTRICTS+=['distrito.porto','distrito.aveiro']
if 'Lisbon' in SEARCH.get('areas',[]):DISTRICTS+=['distrito.lisboa','distrito.setubal']
NEARBY_CACHE={};NEARBY_REQUESTS=0;NEARBY_REQUEST_LIMIT=60

def s(v):
    return str(v) if v is not None and not isinstance(v,(dict,list)) else (json.dumps(v,ensure_ascii=False) if v is not None else '')
def n(v):
    return ''.join(c for c in unicodedata.normalize('NFKD',s(v).lower()) if not unicodedata.combining(c))
def integer(v):
    try:return int(float(str(v).replace('€','').replace(' ','').replace(',','.')))
    except (ValueError,TypeError):return None
def request(url,params=None,headers=None,body=None):
    if params:url+='?'+urlencode(params)
    head={'Accept':'application/json','User-Agent':'PortugalVillaFinder/1.0',**(headers or {})}
    if body is not None:head['Content-Type']='application/json'
    q=Request(url,data=json.dumps(body).encode() if body is not None else None,headers=head)
    with urlopen(q,timeout=40) as r:return json.load(r)
def mentions(v,terms):
    t=n(v);return any(x in t for x in terms)
def region(place,lat=None,lon=None):
    if lat is not None and lon is not None:
        def km(c):
            x,y=CENTERS[c];a=math.radians(lat);b=math.radians(x)
            dlat=math.radians(x-lat);dlon=math.radians(y-lon)
            h=math.sin(dlat/2)**2+math.cos(a)*math.cos(b)*math.sin(dlon/2)**2
            return 12742*math.asin(min(1,math.sqrt(h)))
        closest=min(CENTERS,key=km)
        return closest if km(closest)<max(58,int(SEARCH.get('max_drive_minutes',40))*1.6) else None
    t=n(place)
    if mentions(t,['porto','gaia','matosinhos','maia','valongo','gondomar','trofa','espinho','vila do conde','santo tirso','povoa de varzim']):return 'Porto'
    if mentions(t,['lisboa','lisbon','almada','sintra','oeiras','cascais','amadora','loures','odivelas','seixal','barreiro','montijo','alcochete','mafra']):return 'Lisbon'
    return None
def drive(lat,lon,destination):
    key=os.getenv('GOOGLE_MAPS_API_KEY','')
    if not key or lat is None or lon is None:return None
    payload={'origin':{'location':{'latLng':{'latitude':lat,'longitude':lon}}},'destination':{'location':{'latLng':{'latitude':CENTERS[destination][0],'longitude':CENTERS[destination][1]}}},'travelMode':'DRIVE','routingPreference':'TRAFFIC_UNAWARE'}
    r=request('https://routes.googleapis.com/directions/v2:computeRoutes',headers={'X-Goog-Api-Key':key,'X-Goog-FieldMask':'routes.duration'},body=payload)
    routes=r.get('routes') or []
    return round(float(routes[0]['duration'].rstrip('s'))/60) if routes else None
def list_text(x):
    return s(x)
def haversine_km(a,b,c,d):
    x=math.radians(c-a);y=math.radians(d-b)
    h=math.sin(x/2)**2+math.cos(math.radians(a))*math.cos(math.radians(c))*math.sin(y/2)**2
    return 12742*math.asin(min(1,math.sqrt(h)))
def nearby_search(lat,lon,query,radius_km):
    """Google Places API (New), Text Search. Approximate crow-flies distance, NOT a travel route."""
    global NEARBY_REQUESTS
    key=os.getenv('GOOGLE_MAPS_API_KEY','')
    if not key:return (None,'Google Places API key not configured')
    if lat is None or lon is None:return (None,'Exact property coordinates unavailable')
    cache_key=(round(lat,4),round(lon,4),query.lower(),radius_km)
    if cache_key in NEARBY_CACHE:return NEARBY_CACHE[cache_key]
    if NEARBY_REQUESTS>=NEARBY_REQUEST_LIMIT:return (None,'Daily Places query limit reached')
    NEARBY_REQUESTS+=1
    body={'textQuery':query,'languageCode':'pt','pageSize':10,'locationBias':{'circle':{'center':{'latitude':lat,'longitude':lon},'radius':min(50000.0,max(500.0,float(radius_km)*1250))}}}
    try:
        data=request('https://places.googleapis.com/v1/places:searchText',headers={'X-Goog-Api-Key':key,'X-Goog-FieldMask':'places.location,places.displayName'},body=body)
        spots=[]
        for obj in data.get('places') or []:
            point=obj.get('location') or {}
            if point.get('latitude') is None or point.get('longitude') is None:continue
            km=haversine_km(lat,lon,float(point['latitude']),float(point['longitude']))
            name=(obj.get('displayName') or {}).get('text') or query
            spots.append((km,name))
        spots.sort(key=lambda z:z[0])
        if spots and spots[0][0] <= float(radius_km):
            val=(round(spots[0][0],2),spots[0][1])
        else:
            val=(None,'No qualifying place evidenced in limited Places results; absence not proven')
    except Exception as ex:
        val=(None,'Places check unavailable: '+str(ex)[:90])
    NEARBY_CACHE[cache_key]=val
    return val
def evaluate_custom(text,lat,lon):
    rules=[]
    for rule in SEARCH.get('additional_requirements',[]):
        kind=rule.get('kind')
        label=str(rule.get('label') or 'Additional requirement')
        query=str(rule.get('query') or '')
        required=bool(rule.get('required',True))
        status='unverified';detail='Manual confirmation needed'
        distance=None
        if kind=='keyword':
            if n(query) in n(text):
                status='evidenced';detail='Phrase found in listing text (not independently verified)'
            else:detail='Not evidenced in listing text; absence not proven'
        elif kind=='nearby':
            km,info=nearby_search(lat,lon,query,rule.get('max_distance_km',3))
            if km is not None:
                status='evidenced';distance=km
                detail=str(info)+' · approximately '+str(km)+' km straight-line'
            else:detail=str(info)
        rules.append({'kind':kind,'label':label,'query':query,'required':required,'status':status,'detail':detail,'distance_km':distance})
    return rules

def normalize(item,source):
    if not isinstance(item,dict):return None
    code=s(item.get('id') if source=='Casa SAPO' else item.get('propertyCode') or item.get('adid') or item.get('id'))
    if not code:return None
    url=s(item.get('url') or item.get('link'))
    domain='casa.sapo.pt' if source=='Casa SAPO' else 'idealista.pt'
    if not url.startswith('https://') or domain not in url:
        if source=='Idealista':url='https://www.idealista.pt/imovel/'+code+'/'
        else:return None
    price=integer(item.get('price'))
    beds=integer(item.get('bedrooms') if source=='Casa SAPO' else item.get('rooms') or item.get('bedrooms'))
    baths=integer(item.get('bathrooms') or item.get('baths') or item.get('bathRooms') or item.get('numBathrooms'))
    if price is None or not int(SEARCH.get('min_price',PRICE_MIN))<=price<=int(SEARCH.get('max_price',PRICE_MAX)) or beds is None or beds<int(SEARCH.get('min_bedrooms',4)) or baths is None or baths<int(SEARCH.get('min_bathrooms',2)):return None
    title=s(item.get('title') or item.get('suggestedTitle') or 'Moradia T4')
    ptype=n(item.get('propertyType') or item.get('property_type') or item.get('category') or item.get('detailedType'))
    if mentions(ptype,['apartment','apartamento','flat','penthouse']):return None
    if source=='Idealista' and not mentions(ptype+' '+title,['house','villa','moradia','chalet','townhouse','vivenda','terraced','detached']):return None
    loc=item.get('location') or {}
    if not isinstance(loc,dict):loc={'text':str(loc)}
    place=s(loc.get('text') or item.get('municipality') or item.get('district') or item.get('address') or title)
    try:
        lat=float(item.get('latitude') or loc.get('latitude'))
        lon=float(item.get('longitude') or loc.get('longitude'))
    except (ValueError,TypeError):lat=lon=None
    near=region(place,lat,lon)
    if not near or near not in SEARCH.get('areas',[]):return None
    description=s(item.get('description') or item.get('propertyDescription') or '')
    feat=s(item.get('features') or item.get('tags') or '')
    combined=n(description+' '+title+' '+feat)
    condition=n(item.get('condition') or item.get('preservation') or '')
    if mentions(combined+' '+condition,['para remodelar','necessita obras','para renovar','a precisar de obras','under construction','por concluir','em construcao','requires renovation','for renovation']):return None
    new=mentions(combined+' '+condition,['totalmente renovad','totalmente remodelad','remodelacao total','reabilitacao total','recentemente renovad','integralmente renovad','nova construcao','construcao nova','obra nova','fully renovated','new build','brand new'])
    garden=mentions(combined,['jardim privado','jardim privativo','jardim exclusivo','private garden'])
    garage=mentions(combined,['garagem individual','garagem fechada','garagem privativa','box garagem','private garage','enclosed garage'])
    if mentions(combined,['jardim partilhado','jardim comum','shared garden','communal garden']):garden=False
    energy=s(item.get('energyCertificate') or item.get('energyRating') or item.get('energyClass') or item.get('energy') or 'Not stated')
    if isinstance(item.get('energy_certificate'),dict):energy=s(item['energy_certificate'].get('rating') or energy)
    if not re.fullmatch(r'A\+|A|B-|B|C|D|E|F|G',energy,re.I):energy='Not stated'
    try:minutes=drive(lat,lon,near)
    except Exception as e:print('Routing failed:',e,file=sys.stderr);minutes=None
    if minutes is not None and minutes>int(SEARCH.get('max_drive_minutes',40)):return None
    exact=n(item.get('coordinate_precision') or item.get('location_precision')) in ('exact','address','rooftop')
    issues=[]
    if not new:issues.append('New construction or fully completed renovation not verified')
    if not garden:issues.append('Private garden not confirmed')
    if not garage:issues.append('Enclosed private garage not confirmed')
    if minutes is None:issues.append('Drive time to central '+near+' not verified')
    if minutes is not None and not exact:issues.append('Property coordinates may be approximate')
    if energy=='Not stated':issues.append('Energy certificate/rating absent from listing data')
    checks=evaluate_custom(description+' '+title+' '+feat,lat,lon)
    for rule in checks:
        if rule['required'] and rule['status']!='evidenced':
            issues.append(rule['label']+': '+rule['detail'])
    needs=SEARCH.get('must_have',{})
    complete=(not needs.get('new_or_renovated',True) or new) and (not needs.get('private_garden',True) or garden) and (not needs.get('garage',True) or garage) and minutes is not None and exact and energy!='Not stated' and all(rule['status']=='evidenced' for rule in checks if rule['required'])
    images=item.get('images') or item.get('image') or item.get('thumbnail') or ''
    if isinstance(images,list):images=images[0] if images else ''
    if isinstance(images,dict):images=images.get('url','')
    if not s(images).startswith('https://'):images=''
    return {'id':('casa-sapo-' if source=='Casa SAPO' else 'idealista-')+code,'source':source,'sourceShort':source,'region':near,'area':place,'title':title,'price':price,'beds':beds,'baths':baths,'energy':energy,'size':s(item.get('size') or item.get('area_m2') or 'Not stated'),'condition':'New or fully renovated (listing claim)' if new else 'Condition unverified','garden':'Private garden (listing claim)' if garden else 'Not confirmed','garage':'Enclosed garage (listing claim)' if garage else 'Not confirmed','drive':('Approx '+str(minutes)+' min without live traffic' if minutes is not None else 'Not verified'),'category':'verified' if complete else 'possible','categoryLabel':'Listing-based match' if complete else 'Needs verification','link':url,'image':images,'summary':'Search API listing details; seller claims require independent confirmation','issues':issues,'good':[str(beds)+' bedrooms · '+str(baths)+' bathrooms','€'+format(price,',')],'checked':NOW.strftime('%d %b %Y'),'listingRef':code,'drive_minutes':minutes,'latitude':lat,'longitude':lon,'custom_requirements':checks}
def casa():
    key=os.environ['SCRAPPA_API_KEY'];head={'x-api-key':key}
    out=[];seen=set();limit=int(os.getenv('MAX_DETAILS_PER_SOURCE','10'))
    for district in DISTRICTS:
        data=request('https://scrappa.co/api/casa-sapo/search',{'operation':'buy','property_type':'moradias','location':district,'price_min':PRICE_MIN,'price_max':PRICE_MAX,'page':1,'sort':'newest'},head)
        for x in (data.get('data') or {}).get('listings') or []:
            code=s(x.get('id'))
            if code and code not in seen and PRICE_MIN <= (integer(x.get('price')) or 0) <= PRICE_MAX and (integer(x.get('bedrooms')) or 0)>=int(SEARCH.get('min_bedrooms',4)):
                seen.add(code)
                if len(out)>=limit:continue
                try:
                    details=request('https://scrappa.co/api/casa-sapo/listing',{'id':code},head).get('data') or {}
                    r=normalize({**x,**details},'Casa SAPO')
                    if r:out.append(r)
                except Exception as e:print('Casa listing error',code,e,file=sys.stderr)
    return out
def idealista():
    key=os.environ['IDEALISTA_RAPIDAPI_KEY'];base='https://idealista-real-estate.p.rapidapi.com';head={'x-rapidapi-key':key,'x-rapidapi-host':'idealista-real-estate.p.rapidapi.com'}
    ids=[v.strip() for v in os.getenv('IDEALISTA_LOCATION_IDS','').split(',') if v.strip()]
    if not ids:
        for city in ['Porto','Lisboa','Setúbal','Aveiro']:
            matches=request(base+'/v1/locations/autocomplete',{'query':city,'country':'pt'},head)
            for loc in matches.get('locations') or matches.get('results') or []:
                if loc.get('locationId') and n(city) in n(loc.get('name') or loc.get('label')) and mentions(loc.get('type') or loc.get('locationType'),['district','distrito','province']):
                    ids.append(str(loc['locationId']));break
    if not ids:raise RuntimeError('No district location IDs resolved; configure IDEALISTA_LOCATION_IDS')
    out=[];seen=set();limit=int(os.getenv('MAX_DETAILS_PER_SOURCE','10'))
    for place in ids:
        data=request(base+'/v1/search',{'operation':'sale','propertyType':'homes','country':'pt','locale':'pt','locationIds':'['+place+']','priceFrom':PRICE_MIN,'priceTo':PRICE_MAX,'order':'publicationDate','sort':'desc','numPage':1,'maxItems':40},head)
        for x in data.get('elementList') or []:
            code=s(x.get('propertyCode'))
            if not code or code in seen:continue
            seen.add(code)
            if (integer(x.get('rooms')) or 0)<int(SEARCH.get('min_bedrooms',4)) or not PRICE_MIN<=(integer(x.get('price')) or 0)<=PRICE_MAX or len(out)>=limit:continue
            try:
                d=request(base+'/v1/property/'+code,{'country':'pt','locale':'pt'},head)
                detail=d.get('data') or d.get('property') or d
                r=normalize({**x,**detail,'propertyCode':code},'Idealista')
                if r:out.append(r)
            except Exception as e:print('Idealista listing error',code,e,file=sys.stderr)
    return out
def read(path,default):
    try:return json.loads(path.read_text())
    except Exception:return default
def main():
    sources=[('SCRAPPA_API_KEY','Casa SAPO',casa),('IDEALISTA_RAPIDAPI_KEY','Idealista',idealista)]
    results=[];checked=[];errors=[]
    for env,name,fn in sources:
        if not os.getenv(env):
            print(name+': no API key configured; skipping');continue
        try:found=fn();results+=found;checked.append(name);print(name+': '+str(len(found))+' potential candidates')
        except Exception as e:errors.append(name+': '+str(e));print('Error:',e,file=sys.stderr)
    if not checked:
        print('No searches completed; preserving dated snapshot')
        if errors:raise SystemExit('; '.join(errors))
        return
    feed=read(FEED,{'properties':[]})
    old={x['id']:x for x in feed.get('properties',[]) if 'id' in x}
    history=read(HISTORY,{'properties':{}}).get('properties',{})
    current={}
    for x in results:
        k=x['id'];prior=history.get(k,{})
        last=prior.get('price') or old.get(k,{}).get('price')
        x['is_new']=not (k in old or k in history)
        x['previous_price']=last if last is not None and last>x['price'] else None
        x['first_seen']=prior.get('first_seen') or dt.date.today().isoformat()
        x['last_seen']=dt.date.today().isoformat()
        history[k]={'price':x['price'],'first_seen':x['first_seen'],'last_seen':x['last_seen']}
        current[k]=x
    for k,x in old.items():
        if k not in current:
            # Keep previously checked results temporarily; do not suggest they are still available.
            x['statusNote']='Not confirmed by current daily search; may be outdated'
            current[k]=x
    feed={'updated_at':NOW.isoformat(),'source':'Daily API search (partial if only one source configured)','providers_checked':checked,'errors':errors,'coverage_note':'Only newest search pages are checked; route times depend on available geolocation and API keys. Nearby checks use straight-line distance and limited Google Places results; absence cannot be established.','search_config':SEARCH,'properties':list(current.values())[:70]}
    FEED.write_text(json.dumps(feed,ensure_ascii=False,indent=2)+'\n')
    HISTORY.write_text(json.dumps({'properties':history},ensure_ascii=False,indent=2)+'\n')
    print('Saved '+str(len(feed['properties']))+' properties')
if __name__=='__main__':main()

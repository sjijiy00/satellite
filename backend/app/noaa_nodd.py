"""NOAA's public NDVI bucket; objects, not a fabricated STAC catalogue.

Only verified v001 NOAA-20 JP113C1 filenames since 2023 are registered. The
geometry is the global product grid, NEVER a valid-pixel or swath footprint.
"""
from datetime import datetime,timezone
import re
from urllib.parse import urlencode
import xml.etree.ElementTree as ET
import httpx
from .provider_transfer import TransferError

COLLECTION='noaa-viirs-ndvi-cdr'
ENDPOINT='https://noaa-cdr-ndvi-pds.s3.amazonaws.com'
NS={'s':'http://s3.amazonaws.com/doc/2006-03-01/'}
PATTERN=re.compile(r'^VIIRS-Land_v001_JP113C1_NOAA-20_(\d{8})_c(\d{14})\.nc$')


def initial(query,collection):
    return {'method':'POST','url':ENDPOINT,'body':{'start':str(query.start_date),'end':str(query.end_date),'year':query.start_date.year}}


async def listing(client,params,seconds):
    async with client.stream('GET',ENDPOINT+'/',params={'list-type':'2','max-keys':25,**params},timeout=httpx.Timeout(seconds,connect=min(5,seconds))) as r:
        r.raise_for_status();raw=bytearray()
        async for chunk in r.aiter_bytes():
            raw.extend(chunk)
            if len(raw)>2*1024**2:raise ValueError('Listing size limit')
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():raise ValueError('Unsafe XML')
    try:root=ET.fromstring(raw)
    except ET.ParseError:raise ValueError('Invalid XML') from None
    if root.findtext('s:Name',namespaces=NS)!='noaa-cdr-ndvi-pds':raise ValueError('Bucket mismatch')
    return root


def feature(key,size):
    name=key.rsplit('/',1)[-1];match=PATTERN.fullmatch(name)
    if not match:raise ValueError('Product filename mismatch')
    day=datetime.strptime(match[1],'%Y%m%d').replace(tzinfo=timezone.utc)
    if day.year<2023 or key!='data/'+str(day.year)+'/'+name:raise ValueError('Outside reviewed product range')
    if not isinstance(size,int) or size<=0:raise ValueError('Invalid file size')
    return {'id':name[:-3],'collection':COLLECTION,'geometry':{'type':'Polygon','coordinates':[[[-180,-90],[180,-90],[180,90],[-180,90],[-180,-90]]]},
        'properties':{'datetime':day.isoformat(),'end_datetime':day.replace(hour=23,minute=59,second=59).isoformat(),
            'platform':'noaa-20','instruments':['viirs'],'processing:level':'daily_CDR','product:type':'VIIRS NDVI CDR v1 / JP113C1 v001',
            'app:geometry_role':'product_grid_extent','app:temporal_role':'daily_product',
            'app:native_resolution':'VIIRS 관측을 집계한 NDVI 파생 제품; 10 m 상세 영상 대안 아님',
            'app:output_grid':'전 지구 경위도 0.05° (남북 약 5.56 km; 경도 방향은 위도별 상이)'},
        'assets':{'ndvi':{'href':ENDPOINT+'/'+key,'type':'application/x-netcdf','roles':['data'],'title':'NOAA-20 일별 NDVI CDR 원본 NetCDF','file:size':size}},
        'links':[{'rel':'self','href':ENDPOINT+'/?'+urlencode({'list-type':'2','prefix':key,'max-keys':1})}]}


async def request_page(client,request,seconds):
    body=request['body'];year=int(body['year']);prefix=f'data/{year}/VIIRS-Land_v001_JP113C1_NOAA-20_'
    params={'prefix':prefix}
    if body.get('cursor'):params['continuation-token']=body['cursor']
    else:params['start-after']=prefix+body['start'].replace('-','') if year==int(body['start'][:4]) else prefix
    root=await listing(client,params,seconds);features=[];beyond=False
    for row in root.findall('s:Contents',NS):
        item=feature(row.findtext('s:Key',namespaces=NS),int(row.findtext('s:Size',namespaces=NS)))
        day=item['properties']['datetime'][:10]
        if day>body['end']:beyond=True;break
        if day>=body['start']:features.append(item)
    next_body=None
    if not beyond and root.findtext('s:IsTruncated',namespaces=NS)=='true':
        cursor=root.findtext('s:NextContinuationToken',namespaces=NS)
        if not cursor or len(cursor)>4096:raise ValueError('Invalid continuation')
        next_body={**body,'cursor':cursor}
    elif not beyond and year<int(body['end'][:4]):next_body={**body,'year':year+1,'cursor':None}
    return {'features':features,'links':[{'rel':'next','href':ENDPOINT,'method':'POST','body':next_body}] if next_body else []}


async def canonical(identifier):
    name=identifier+'.nc';m=PATTERN.fullmatch(name)
    if not m:raise TransferError('not_found')
    key='data/'+m[1][:4]+'/'+name
    try:
        async with httpx.AsyncClient(follow_redirects=False,trust_env=False) as client:
            root=await listing(client,{'prefix':key,'max-keys':2},8)
        rows=[r for r in root.findall('s:Contents',NS) if r.findtext('s:Key',namespaces=NS)==key]
        if len(rows)!=1:raise TransferError('not_found')
        return feature(key,int(rows[0].findtext('s:Size',namespaces=NS)))
    except (httpx.HTTPError,ValueError,ET.ParseError,TypeError):raise TransferError('invalid_metadata') from None

"""A2 bounded, read-only two-scene preflight. No raster pixels or feasibility verdict."""
import asyncio
import json
from datetime import datetime, timezone
from time import monotonic
from urllib.parse import quote, urlsplit
import httpx
from .stac import STAC_URL
from .metadata import normalize
from .purpose_plan import purpose_plan
from .selection import footprint_metrics
from .grid_metadata import grid_metadata
from .sensor_catalog import CATALOG

VERSION='a2-conditions-2026-10-29.1'
MAX_REQUESTS=14
TOTAL_SECONDS=45
REQUEST_SECONDS=8
MAX_ITEM_BYTES=2_000_000
ASSET_HOSTS={'sentinel-cogs.s3.us-west-2.amazonaws.com','landsatlook.usgs.gov',
             'usgs-landsat.s3.us-west-2.amazonaws.com'}


def check(key,label,status,reason,action,evidence=None):
    return {'id':key,'label':label,'status':status,'reason':reason,'next_action':action,'evidence':evidence}


async def request_metadata(client,method,url,budget):
    seconds=min(REQUEST_SECONDS,TOTAL_SECONDS-(monotonic()-budget['started']))
    if seconds<=0 or budget['requests']>=MAX_REQUESTS:raise TimeoutError('budget')
    budget['requests']+=1
    async def fetch():
        async with client.stream(method,url,timeout=seconds) as r:
            data=None
            if method=='GET' and r.status_code==200:
                chunks=bytearray()
                async for chunk in r.aiter_bytes():
                    chunks.extend(chunk)
                    if len(chunks)>MAX_ITEM_BYTES:raise ValueError('Item exceeds size limit')
                data=json.loads(chunks)
            return r.status_code,dict(r.headers),data
    return await asyncio.wait_for(fetch(),seconds)


async def inspect_asset(client,asset,budget):
    url=asset.get('href','')
    evidence={'method':'HEAD','file_header_read':False,'pixel_read':False,'http_status':None}
    try:
        parts=urlsplit(url);port=parts.port
    except ValueError:
        return 'unknown','Asset URL 형식 오류: 접근하지 않았습니다.',evidence
    if (asset.get('requester_pays') or parts.scheme!='https' or parts.hostname not in ASSET_HOSTS
        or port not in (None,443) or parts.username or parts.password or parts.query or parts.fragment):
        return 'unknown','인증·비용·서명 URL 또는 연결 허용 범위 밖 Asset: 자동 접근하지 않았습니다.',evidence
    evidence['url']=url
    try:
        code,headers,_=await request_metadata(client,'HEAD',url,budget)
        evidence.update(http_status=code,content_type=headers.get('content-type'),content_length=headers.get('content-length'))
        if code==200 and headers.get('content-length')!='0' and any(v in headers.get('content-type','').lower() for v in ('tiff','jp2','octet-stream')):
            return 'pass','파일 URL의 HTTP HEAD 접근 응답 확인. 파일 내용·헤더·픽셀 무결성은 미검사입니다.',evidence
        if code in (401,403,404,410):return 'blocked',f'HTTP {code}: 현재 공개 접근 불가. 인증·비용 동의는 수행하지 않았습니다.',evidence
        return 'unknown',f'HTTP {code}: 리다이렉트·HEAD 미지원·내용 유형 등을 확인해야 합니다. 자동 추적/전체 다운로드는 하지 않았습니다.',evidence
    except (httpx.HTTPError,TimeoutError,ValueError):
        return 'unknown','네트워크 오류·시간/요청 상한으로 접근을 확인하지 못했습니다.',evidence


def captured(scene):
    try:
        t=datetime.fromisoformat(scene['datetime'].replace('Z','+00:00'))
        return t.astimezone(timezone.utc) if t.tzinfo else None
    except (TypeError,ValueError,AttributeError):return None


async def inspect_conditions(query):
    checks=[];scenes=[];raws=[];assets_out=[]
    budget={'started':monotonic(),'requests':0}
    refs=[query.scene_a,query.scene_b]
    same=refs[0]==refs[1]
    checks.append(check('identity','서로 다른 영상','blocked' if same else 'pass',
                        '동일 컬렉션·Item을 중복 선택했습니다.' if same else '서로 다른 컬렉션·Item 식별자입니다.','서로 다른 시점의 영상을 선택하세요.' if same else '촬영 시점도 확인하세요.'))
    async with httpx.AsyncClient(follow_redirects=False) as client:
        for i,ref in enumerate(refs):
            url=f'{STAC_URL}/collections/{ref.collection}/items/{quote(ref.id,safe="")}'
            code=None
            try:
                code,_,raw=await request_metadata(client,'GET',url,budget)
                if code!=200 or not isinstance(raw,dict) or raw.get('id')!=ref.id or raw.get('collection')!=ref.collection:raise ValueError('Invalid canonical Item')
                scene=normalize(raw);scene['purpose_plan']=purpose_plan(scene,query.purpose_type)
                scenes.append(scene);raws.append(raw)
                checks.append(check(f'item-{i}','영상 '+str(i+1)+' 원본 메타데이터','pass','고정된 STAC 제공처에서 Item을 다시 조회했습니다.','아래 개별 조건을 확인하세요.',{'url':url,'id':ref.id,'collection':ref.collection}))
            except (httpx.HTTPError,TimeoutError,ValueError,KeyError,TypeError,AttributeError):
                scenes.append(None);raws.append(None)
                checks.append(check(f'item-{i}','영상 '+str(i+1)+' 원본 메타데이터','unknown','원본 Item 조회·형식 검사에 실패했습니다. 검색 화면의 오래된 값으로 통과시키지 않습니다.','제공처 상태를 확인하고 다시 검사하세요.',{'http_status':code,'url':url}))
        pair=all(scenes)
        if pair:
            a,b=scenes
            known=all(s['processing_level'] and s['instruments'] for s in scenes)
            same_product=(a['collection']==b['collection'] and a['processing_level']==b['processing_level'] and sorted(a['instruments'])==sorted(b['instruments']))
            checks.append(check('product','동일 센서·제품','pass' if known and same_product else 'conditional' if known else 'unknown',
                '센서·제품 메타데이터 일치.' if known and same_product else '센서·제품 차이 또는 누락이 있어 직접 전후 비교 조건을 확정할 수 없습니다.',
                '플랫폼이 다르면 교차 보정·관측 조건도 검토하세요. 동일 제품만으로 픽셀 호환성을 보장하지 않습니다.',
                [{'collection':s['collection'],'platform':s['platform'],'instruments':s['instruments'],'product':s['processing_level']} for s in scenes]))
            times=[captured(s) for s in scenes]
            ordered=all(times) and times[0]<times[1]
            checks.append(check('dates','촬영일·전후 순서','pass' if ordered else 'blocked' if all(times) else 'unknown',
                '이전→이후 순서입니다.' if ordered else '촬영 시각이 없거나 동일/역전되었습니다.','영상 1을 이전, 영상 2를 이후로 선택하세요.',[s['datetime'] for s in scenes]))
            in_period=all(times) and all(query.start_date<=t.date()<=query.end_date for t in times)
            checks.append(check('period','검색 기간 포함','pass' if in_period else 'blocked' if all(times) else 'unknown',
                '두 촬영일이 지정 검색 기간에 포함됩니다.' if in_period else '촬영일이 검색 기간 밖이거나 미확인입니다.','검색 기간과 선택 영상을 확인하세요.'))
            aligned=query.reference_date and all(times) and times[0].date()<query.reference_date<=times[1].date()
            checks.append(check('reference','사건·변화 기준일','pass' if aligned else 'blocked' if query.reference_date and all(times) else 'unknown',
                '이전 촬영일 < 기준일 ≤ 이후 촬영일 (UTC 날짜).' if aligned else '기준일이 없거나 두 영상을 전후로 나누지 못합니다.',
                '기준일은 UTC 00:00 경계입니다. 이전 영상은 전날까지, 이후 영상은 기준일부터 선택하세요.',str(query.reference_date) if query.reference_date else None))
            metrics=footprint_metrics(query.bbox,a['geometry'],b['geometry'])
        else:
            for key,label in [('product','동일 센서·제품'),('dates','촬영일·전후 순서'),('period','검색 기간 포함'),('reference','사건·변화 기준일')]:
                checks.append(check(key,label,'unknown','원본 메타데이터 부족.','원본 조회를 다시 시도하세요.'))
            metrics=footprint_metrics(query.bbox,None,None)
        area=metrics['common_area_m2']
        checks.append(check('coverage','두 시점 공통 촬영 영역','unknown' if area is None else 'pass' if area>0 else 'blocked',
            'AOI와 두 footprint의 교집합입니다. 개별 중첩률·공통 영역은 유효 픽셀 비율이 아닙니다.',
            '공통 영역이 없으면 AOI/영상을 다시 선택하세요. 기하 조건 통과 후에도 픽셀 품질은 별도 검사해야 합니다.',metrics))
        for i,(scene,raw) in enumerate(zip(scenes,raws)):
            label='영상 '+str(i+1)
            if scene is None:
                for key in ('bands','quality','access','grid'):
                    checks.append(check(f'{key}-{i}',label+' '+{'bands':'필수 밴드·제품','quality':'품질 자료','access':'Asset 접근','grid':'격자'}[key],'unknown','원본 Item 조회 실패.','다시 검사하세요.'))
                continue
            plan=scene['purpose_plan']
            product=plan['product_status']
            checks.append(check(f'bands-{i}',label+' 필수 밴드·제품','blocked' if plan['missing_bands'] or product=='not_met' else 'unknown' if product=='unknown' else 'pass',
                '기존 목적 규칙에 필요한 제품 및 밴드 메타데이터 검사.','필요한 밴드와 제품 정보가 확인되는 다른 장면을 선택하세요.' if plan['missing_bands'] or product!='met' else '실제 파일 내용은 다음 단계에서 검사해야 합니다.',
                {'required_assets':plan['analysis_keys'],'missing_bands':plan['missing_bands'],'product_status':product}))
            by_key={a['key']:a for a in scene['download_assets']}
            # Reuse the profile selected by purpose_plan and its reviewed catalog.
            required_qa=CATALOG.get(plan['profile_id'],{}).get('quality_keys',[])
            qa=[k for k in required_qa if k in by_key]
            missing_qa=[k for k in required_qa if k not in by_key]
            checks.append(check(f'quality-{i}',label+' 품질 자료','blocked' if missing_qa else 'pass' if required_qa else 'unknown',
                '품질 Asset 메타데이터 검사입니다. 마스크를 읽거나 적용하지 않았습니다.',
                '필요한 품질 자료가 모두 있는 다른 장면을 선택하세요. 실제 마스크 해석·적용은 A3 범위입니다.' if missing_qa else '자료 존재는 품질 통과가 아닙니다.',
                {'required':required_qa,'present':qa,'missing':missing_qa}))
            keys=list(dict.fromkeys(plan['analysis_keys']+qa))
            for key in keys:
                asset=by_key[key]
                status,reason,evidence=await inspect_asset(client,asset,budget)
                checks.append(check(f'access-{i}-{key}',f'{label} {key} 접근',status,reason,'실패/미확인은 제공처 접근 정책을 확인하거나 다른 공개 장면으로 다시 검사하세요.',evidence))
                assets_out.append({'scene':i,'key':key,'grid':grid_metadata(raw,key)})
            if not keys:checks.append(check(f'access-{i}',label+' Asset 접근','unknown','검사할 필수 밴드 Asset이 없습니다.','필수 밴드가 제공된 장면을 선택하세요.'))
    grids=[a['grid'] for a in assets_out]
    complete=bool(grids) and all(g['crs'] and g['shape'] and g['transform'] for g in grids) and pair and all(s['purpose_plan']['analysis_keys'] for s in scenes)
    identical=complete and all(all(g[k]==grids[0][k] for k in ('crs','shape','transform')) for g in grids)
    checks.append(check('grid','CRS·해상도·격자','pass' if identical else 'conditional' if complete else 'unknown',
        '필수/품질 Asset의 CRS·shape·transform 메타데이터가 모두 일치합니다.' if identical else '밴드/시점 사이 격자 차이로 정합이 필요합니다.' if complete else '일부 CRS·shape·transform 정보가 누락/잘못되어 격자를 확정하지 못했습니다.',
        '누락값은 타일 이름/위치로 추정하지 않습니다. 격자 차이는 후속 정합이 필요하며 업샘플링이 실제 해상도 향상을 뜻하지 않습니다.',assets_out))
    checks.append(check('pixel-quality','픽셀 품질','unknown','A2는 픽셀·구름·NoData 마스크를 검사하지 않습니다. 기하 조건 및 HEAD 성공은 픽셀 품질 통과가 아닙니다.','Sentinel-2 L2A 두 날짜는 아래 A3 작은 AOI 픽셀 진단을 실행하고 별도 결과를 확인하세요.'))
    summary='blocked' if any(c['status']=='blocked' for c in checks) else 'unknown' if any(c['status']=='unknown' for c in checks if c['id']!='pixel-quality') else 'conditional'
    return {'version':VERSION,'checked_at':datetime.now(timezone.utc).isoformat(),'status':summary,
            'conclusion':'A2 조건 검사 결과입니다. 분석 가능 확정 판정은 보류합니다.',
            'checks':checks,'coverage':metrics,'assets':assets_out,'pixel_quality':'not_checked',
            'file_headers_read':False,'request_count':budget['requests'],
            'limits':{'max_requests':MAX_REQUESTS,'total_seconds':TOTAL_SECONDS,'request_seconds':REQUEST_SECONDS,'item_bytes':MAX_ITEM_BYTES},
            'input':query.model_dump(mode='json')}

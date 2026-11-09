"""Small, offline, sourced condition proposals; never searches imagery or guesses places."""
import calendar
from datetime import date
import json
import math
from pathlib import Path
import re


CATALOG = Path(__file__).parent / 'data' / 'regions.json'
DATE_TOKEN = re.compile(r'(?<!\d)([1-9]\d{3})(?:\s*년\s*|[-./])(\d{1,2})(?:\s*월(?:\s*(\d{1,2})\s*일)?|[-./](\d{1,2})(?!\d)|(?=$|[\s,]))')
RELATIVE = re.compile(r'최근|지난\s*(?:주|달|해|장마|호우)|이번\s*(?:주|달|장마)|작년|올해|오늘|어제|요즘', re.I)
SHORT_RANGE_END = re.compile(r'^\s*(?:[~–—]|부터)\s*(?:(\d{1,2})\s*[/\.\-]\s*(\d{1,2})|(\d{1,2})\s*월\s*(\d{1,2})\s*일)\s*(?:까지)?(?=$|\s|[.,!?]|[가-힣])')


def proposed_period(text):
    tokens = list(DATE_TOKEN.finditer(text))
    if RELATIVE.search(text):
        return {'status':'needs_confirmation','message':'상대 날짜는 자동 확정하지 않습니다. 연도·월 또는 시작일·종료일을 입력하세요.'}
    if not tokens:
        if re.search(r'\d+\s*[년월일]|\d{4}[-./]\d', text):
            return {'status':'needs_confirmation','message':'연도·월·일을 확인하세요. 월만 있으면 연도를 추가하세요.'}
        return {'status':'absent'}
    try:
        residual=DATE_TOKEN.sub('',text)
        values=[]
        for token in tokens:
            year,month,day1,day2=token.groups();year=int(year);month=int(month);day=day1 or day2
            first=date(year,month,int(day or 1))
            last=first if day else date(year,month,calendar.monthrange(year,month)[1])
            values.append((first,last))
        if len(values)>2:
            raise ValueError('날짜가 여러 개입니다. 검색할 한 기간을 직접 정해 주세요.')
        # A shortened range must not silently become the first single day/month.
        remainder=text[tokens[-1].end():]
        if re.match(r'\s*\d+(?:\s|$)',remainder):
            raise ValueError('일자 입력이 불완전합니다. 연도·월·일을 확인하세요.')
        short=None
        if len(values)==1 and re.search(r'부터|[~–—]',remainder):
            short=SHORT_RANGE_END.match(remainder)
            if not short or tokens[0].group(3) is None and tokens[0].group(4) is None:
                raise ValueError('범위의 끝 날짜에는 월·일을 적어 주세요.')
            year=values[0][0].year
            month=int(short.group(1) or short.group(3))
            day=int(short.group(2) or short.group(4))
            values.append((date(year,month,day),date(year,month,day)))
            if re.search(r'(?:[~–—]|부터)\s*\d{1,2}\s*[/\.\-]\s*\d{1,2}',remainder[short.end():]):
                raise ValueError('날짜 범위가 여러 개입니다. 검색할 한 기간을 직접 정해 주세요.')
            residual=residual.replace(short.group(),'',1)
        if re.search(r'\d+\s*[년월일]|\d{4}[-./]\d',residual):
            raise ValueError('날짜 일부가 불완전하거나 지원 형식이 아닙니다. 시작일·종료일을 완전하게 적어 주세요.')
        if len(values)==1 and re.search(r'(?:부터|[~–—])\s*\d{1,2}\s*(?:월|일)',remainder):
            raise ValueError('범위의 끝 날짜에도 연도·월·일을 적어 주세요.')
        if len(tokens)==2 and not re.search(r'부터|까지|[~–—]|\s-\s',text[tokens[0].end():tokens[1].start()]+remainder):
            raise ValueError('두 날짜가 검색 범위인지 확인해 주세요. 시작일부터 종료일까지로 적거나 폼을 수정하세요.')
        start,end=values[0][0],values[-1][1]
        if end<start or (end-start).days>366:
            raise ValueError('검색 기간은 이전→이후 순서이며 최대 366일입니다.')
        evidence=[m.group() for m in tokens]
        if len(tokens)==1 and len(values)==2:evidence.append(short.group().strip())
        return {'status':'resolved','start':str(start),'end':str(end),'timezone':'UTC','evidence':evidence}
    except (ValueError,OverflowError) as exc:
        return {'status':'needs_confirmation','message':str(exc) if len(str(exc))>50 or '검색' in str(exc) or '날짜' in str(exc) or '범위' in str(exc) else '존재하지 않는 날짜입니다. 월·일을 확인하세요.'}


def _contains(text, alias):
    return re.search(r'(?<![가-힣A-Za-z])'+re.escape(alias)+r'(?=$|[\s.,/·]|의|에서|으로|지역|일대|과|와|또는|및)',text) is not None


def load_catalog():
    return json.loads(CATALOG.read_text(encoding='utf-8'))


def extract_places(text):
    """Conservative strings only. Administrative geometry comes from another source."""
    try:catalog=load_catalog()
    except (OSError,ValueError,KeyError,TypeError):catalog={'ambiguous':{}}
    pattern=r'[가-힣]{2,}?(?:특별자치시|특별자치도|특별시|광역시|시|군|구|읍|면|동|도)(?=$|\s|의|에서|으로|일대|주변)'
    excluded={'도시','지표면','표면','장면','화면','수면','이번','비교'}
    hits=[(m.start(),m.end(),m.group()) for m in re.finditer(pattern,text) if m.group() not in excluded and not m.group().endswith('온도')]
    for alias in ('서울','광주','중구','충남','충북','경기','부산','대구','인천','대전','울산','세종','제주'):
        for m in re.finditer(re.escape(alias),text):
            if _contains(text[m.start():],alias) and not any(a<=m.start()<b for a,b,_ in hits):hits.append((m.start(),m.end(),alias))
    hits.sort();combined=[]
    for a,b,name in hits:
        if combined and not text[combined[-1][1]:a].strip():
            start,_,_=combined.pop();combined.append((start,b,text[start:b]))
        else:combined.append((a,b,name))
    return [{'text':v,'ambiguous':v in catalog.get('ambiguous',{})} for _,_,v in combined]


def _region(record, catalog):
    dms=record['extents_dms']
    if len(dms)!=4 or any(len(point)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in point)
                         or not 0<=point[1]<60 or not 0<=point[2]<60 for point in dms):
        raise ValueError('Invalid sourced extents')
    raw=[d+m/60+s/3600 for d,m,s in dms]
    bbox=[math.floor(v*1e6)/1e6 if i<2 else math.ceil(v*1e6)/1e6 for i,v in enumerate(raw)]
    w,s,e,n=bbox
    if not (-180<=w<e<=180 and -80<=s<n<=80):
        return {'status':'unsupported','message':'지명 화면 맞춤 범위 자료가 올바르지 않습니다. 기존 AOI를 유지합니다. 지도에서 직접 이동하세요.'}
    return {'status':'resolved','id':record['id'],'name':record['name'],'label':record['name']+' 지도 이동 참고',
            'view_bbox':bbox,'role':'camera_only','source':record['source'],'source_url':record['source_url'],
            'source_year':record['source_year'],'checked_on':catalog['checked_on'],'catalog_version':catalog['version'],'note':record['note'],
            'usage':record.get('usage'),'terms_url':record.get('terms_url'),'history_url':record.get('history_url')}


def proposed_region(text, selected_id=None):
    try:
        catalog=load_catalog();records=catalog['regions']
        # A finer named locality must not be replaced by the entire parent province.
        finer=re.search(r'(?:충남|충청남도)(?:의)?\s+([가-힣]+(?:시|군|구|읍|면|동)|천안|아산|서산|태안|당진|보령|공주|논산|부여|서천|홍성|예산|금산|청양|계룡)(?=$|\s|의|에서)',text)
        if finer and finer.group(1) not in ('도시',):
            return {'status':'unsupported','message':f'세부 지명 “{finer.group(1)}”의 검증된 범위가 현재 목록에 없습니다. 충남 전체로 바꾸지 않습니다. 지도·좌표로 지정하세요.'}
        matched=[r for r in records if any(_contains(text,a) for a in r['aliases'])]
        ambiguous=next((items for name,items in catalog['ambiguous'].items() if _contains(text,name)),None)
        if ambiguous and not matched:
            if selected_id in {r['id'] for r in ambiguous}:
                return {'status':'unsupported','message':'선택한 세부 행정구역의 검증된 좌표 자료가 아직 없습니다. 기존 AOI를 유지합니다. 지도에서 직접 지정하세요.'}
            return {'status':'ambiguous','message':'같은 이름의 행정구역이 있습니다. 어느 지역인지 선택해 주세요. 목록은 전체 지명 사전이 아닙니다.', 'candidates':ambiguous}
        if len(matched)>1:
            if selected_id:
                matched=[r for r in matched if r['id']==selected_id]
            else:
                return {'status':'ambiguous','message':'지도에서 볼 지역을 선택해 주세요. 여러 지역을 임의로 합치지 않습니다.',
                        'candidates':[{'id':r['id'],'name':r['name']} for r in matched]}
        if matched:
            if selected_id and selected_id!=matched[0]['id']:
                return {'status':'unsupported','message':'현재 문장에 없는 지역 선택입니다. 문장을 다시 확인하세요.'}
            return _region(matched[0],catalog)
        # Report an explicit but unsupported place; date-only/purpose-only text stays absent.
        if re.search(r'[가-힣]{2,}(?:특별시|광역시|특별자치도|[시군구읍면동])(?:의|에서|으로|\s|$)',text) or re.search(r'서울|경기|강원|충북|충청|전남|전북|경북|경남|제주|부산|대구|대전|인천|울산|세종|대한민국|미국|아틀란티스',text):
            mention=re.search(r'[가-힣]{2,}?(?:특별시|광역시|특별자치도|[시군구읍면동])(?=의|에서|으로|\s|$)',text)
            return {'status':'unsupported','mentioned_text':mention.group() if mention else None,'message':'지명 언급이 있지만 로컬 참고 목록에 없습니다. 존재 여부 판정이 아닙니다. 위치 확인 또는 수동 지도·좌표 지정을 사용하세요.'}
        return {'status':'absent'}
    except (OSError,ValueError,KeyError,TypeError):
        return {'status':'failed','message':'지명 자료를 읽거나 검증하지 못했습니다. 임의 좌표로 대체하지 않으며 기존 AOI를 유지합니다.'}


def propose_conditions(text, selected_id=None):
    period=proposed_period(text);region=proposed_region(text,selected_id)
    messages=[v['message'] for v in (period,region) if v.get('message')]
    event=bool(re.search(r'전후|전·후|before.*after',text,re.I))
    if event:messages.append('월 단위 검색 기간과 사건 전·후 비교 기간은 다릅니다. 기준 사건 날짜 또는 전·후 기간을 추가로 확인하세요. 사건 날짜는 자동 생성하지 않습니다.')
    statuses={period['status'],region['status']}
    status='partial' if event or messages else 'success'
    if 'failed' in statuses and 'resolved' not in statuses:status='failed'
    from .purposes import classify
    purpose,evidence=classify(text,None)
    places=extract_places(text)
    if places and not region.get('mentioned_text'):region['mentioned_text']=' / '.join(p['text'] for p in places)
    return {'status':status,'period':period,'region':region,'messages':messages,'event_reference_required':event,
            'extraction':{'purpose_type':purpose,'purpose_evidence':', '.join(evidence),'analysis_target':next(iter(re.findall(r'지표면\s*온도|지표온도',text)),None),
                          'temporal_mode':'change' if event else 'unspecified','places':places},
            'scope':'지명은 카메라 이동 전용. AOI는 사용자 지정·확정. 자동 검색·영상 처리·사건일 추정 없음.',
            'engine':{'mode':'rules','status':'succeeded','provider':None,'model':None}}

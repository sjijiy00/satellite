"""CMR granules → common STAC-shaped input. Geometry is reported coverage, not valid pixels."""
import asyncio
from urllib.parse import urlencode, parse_qs, urlsplit
import httpx
from .provider_registry import PROVIDERS, COLLECTION_REGISTRY
from .safe_urls import safe_url
from . import hls

ENDPOINT = PROVIDERS['nasa-cmr']['endpoint']
COLLECTION = 'viirs-vnp09ga-002'
COLLECTIONS = (COLLECTION, *hls.COLLECTIONS)


def initial(query, collection):
    params = {'collection_concept_id': COLLECTION_REGISTRY[collection]['remote_id'],
              'bounding_box': ','.join(map(str, query.bbox)),
              'temporal': f'{query.start_date}T00:00:00Z,{query.end_date}T23:59:59.999999Z',
              'page_size': 25, 'page_num': 1, 'sort_key': '-start_date'}
    return {'method': 'GET', 'url': ENDPOINT + '/granules.json?' + urlencode(params)}


def geometry(entry):
    polygons = []
    for group in entry.get('polygons', []):
        for ring in group:
            values = [float(v) for v in ring.split()]
            if len(values) < 8 or len(values) % 2:
                raise ValueError('Invalid CMR polygon')
            coordinates = [[values[i+1], values[i]] for i in range(0, len(values), 2)]
            if any(not (-180 <= x <= 180 and -90 <= y <= 90) for x,y in coordinates):
                raise ValueError('Invalid CMR coordinates')
            if coordinates[0] != coordinates[-1]: coordinates.append(coordinates[0])
            # Split/wrapped antimeridian polygons are not replaced by a global rectangle.
            if any(abs(a[0]-b[0]) > 180 for a,b in zip(coordinates, coordinates[1:])):
                return None
            polygons.append([coordinates])
    if polygons:
        return {'type': 'MultiPolygon', 'coordinates': polygons}
    # A bounding box remains metadata geometry; never manufacture pixel coverage.
    boxes = entry.get('boxes', [])
    for bounds in boxes:
        s,w,n,e = map(float, bounds.split())
        if -180 <= w < e <= 180 and -90 <= s < n <= 90:
            polygons.append([[[w,s],[e,s],[e,n],[w,n],[w,s]]])
    return {'type': 'MultiPolygon', 'coordinates': polygons} if polygons else None


def granule(entry, collection=None):
    if collection is None:
        collection = next((key for key in COLLECTIONS if COLLECTION_REGISTRY[key]['remote_id']==entry.get('collection_concept_id')), None)
    if collection not in COLLECTIONS or entry.get('collection_concept_id') != COLLECTION_REGISTRY[collection]['remote_id']:
        raise ValueError('CMR collection mismatch')
    if collection in hls.COLLECTIONS:
        return {'id':entry['id'],'collection':collection,'geometry':geometry(entry),
            'assets':hls.assets(entry,collection),'properties':hls.properties(entry,collection),
            'links':[{'rel':'self','href':ENDPOINT+'/granules.json?'+urlencode({'concept_id':entry['id'],'page_size':1})}]}
    assets = {}
    for i, link in enumerate(entry.get('links', [])):
        href = safe_url(link.get('href'), ('https', 's3'))
        if not href or link.get('inherited'):
            continue
        rel = link.get('rel', '')
        if rel.endswith('/data#') and href.lower().endswith(('.h5', '.hdf', '.nc')):
            assets[f'granule-{i}'] = {'href': href, 'type': 'application/x-hdf5', 'roles': ['data'],
                                       'title': link.get('title') or 'VNP09GA 원본 전체 granule'}
        elif rel.endswith('/browse#') and href.startswith('https:') and href.lower().endswith(('.jpg','.png')):
            assets[f'preview-{i}'] = {'href': href, 'type': 'image/jpeg' if href.lower().endswith('.jpg') else 'image/png', 'roles': ['thumbnail']}
    return {'id': entry['id'], 'collection': COLLECTION, 'geometry': geometry(entry), 'assets': assets,
            'properties': {'datetime': entry.get('time_start'), 'end_datetime': entry.get('time_end'),
                           'platform': 'suomi-npp', 'instruments': ['viirs'], 'processing:level': 'L2G',
                           'product:type': 'VNP09GA.002',
                           'app:native_resolution': 'VIIRS I 밴드 375 m / M 밴드 750 m (nadir; 스캔 위치에 따라 변화)',
                           'app:output_grid': 'VNP09GA 일별 SIN 500 m (I) / 1 km (M) · 원관측 상세도 향상 아님'},
            'links': [{'rel': 'self', 'href': ENDPOINT + '/concepts/' + entry['id'] + '.json'}]}


async def request_page(client, request, seconds):
    response = await asyncio.wait_for(client.get(request['url'], timeout=httpx.Timeout(seconds, connect=min(5, seconds))), seconds)
    response.raise_for_status()
    entries = response.json()['feed']['entry']
    if not isinstance(entries, list) or len(entries) > 1000:
        raise ValueError('Invalid CMR page')
    params = parse_qs(urlsplit(request['url']).query)
    concept=params['collection_concept_id'][0]
    collection=next((key for key in COLLECTIONS if COLLECTION_REGISTRY[key]['remote_id']==concept),None)
    if collection is None:raise ValueError('Unknown CMR collection')
    features = []
    for entry in entries:
        try:
            features.append(granule(entry, collection))
        except (ValueError, KeyError, TypeError):
            features.append({'id': entry.get('id'), 'collection': collection, 'assets': {'invalid': None}})
    page, size = int(params['page_num'][0]), int(params['page_size'][0])
    hits = int(response.headers['CMR-Hits']) if response.headers.get('CMR-Hits') else None
    more = page*size < hits if hits is not None else len(entries) == size
    links = []
    if more:
        params['page_num'] = [str(page+1)]
        links = [{'rel': 'next', 'href': ENDPOINT + '/granules.json?' + urlencode(params, doseq=True)}]
    return {'features': features, 'links': links}

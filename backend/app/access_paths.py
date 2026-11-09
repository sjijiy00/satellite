"""Group reviewed original product identities, without merging files or Items."""
from collections import defaultdict
import hashlib
import re
from .landsat_access import product_id
from .provider_registry import COLLECTION_REGISTRY


def identity(raw):
    p=raw.get('properties',{});collection=raw.get('collection');base=COLLECTION_REGISTRY.get(collection,{}).get('base_collection',collection)
    if collection in ('hls-l30-002','hls-s30-002') and p.get('app:hls'):
        return {'original_id':p['app:hls']['original_id'],'version':'2.0','family':collection}
    captured=str(p.get('datetime',''))[:10].replace('-','')
    if base=='landsat-c2-l2':
        product=product_id(raw)
        if not product:return None
        fields=product.split('_')
        if p.get('platform')!='landsat-'+str(int(fields[0][2:])) or captured!=fields[3] or str(p.get('landsat:collection_number'))!='02':return None
        return {'original_id':product,'version':'Collection 2 / '+fields[1]+' / processed '+fields[4],'family':base}
    if base=='sentinel-2-l2a':
        product=p.get('s2:product_uri','');match=re.fullmatch(r'(S2[ABC])_MSIL2A_(\d{8})T\d{6}_N(\d{4})_R\d{3}_T[A-Z0-9]{5}_\d{8}T\d{6}\.SAFE',product)
        if not match or p.get('platform')!='sentinel-2'+match[1][-1].lower() or captured!=match[2] or str(p.get('s2:processing_baseline','')).replace('.','')!=match[3]:return None
        return {'original_id':product,'version':'L2A baseline '+match[3],'family':base}
    return None


def group_paths(items):
    groups=defaultdict(list)
    for item in items:
        source=item.get('source_product')
        if source:groups[(source['family'],source['original_id'],source['version'],item.get('platform'))].append(item)
    for key,rows in groups.items():
        if len({r.get('provider_id') for r in rows})<2:continue
        paths=[{k:r.get(k) for k in ('provider_id','provider','collection','id','source_url')} for r in rows]
        for row in rows:row.update(access_group=hashlib.sha256(repr(key).encode()).hexdigest()[:20],access_paths=paths)

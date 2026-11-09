"""Isolated concurrent providers, existing bounded collection paging and a fair global result cap."""
import asyncio
from collections import deque
from datetime import datetime, timezone
from time import monotonic
from . import stac, copernicus, cmr, planetary, noaa_nodd
from .provider_registry import COLLECTION_REGISTRY, PROVIDERS
from .purposes import classify


async def search_providers(query, collections, prepare):
    purpose=query.purpose_type # natural-language purpose extraction belongs to AI only
    groups = {}
    for collection in collections:
        provider = COLLECTION_REGISTRY[collection]['provider_id']
        groups.setdefault(provider, []).append(collection)
    started = monotonic()
    async def run(provider, selected):
        def checked(raw):
            # Upstream filters are not trusted for temporal inclusion. Preserve unknown
            # legacy dates as unknown, but never admit explicitly out-of-period scenes.
            captured = (raw.get('properties') or {}).get('datetime')
            if captured:
                value = datetime.fromisoformat(captured.replace('Z', '+00:00'))
                if value.tzinfo is None: raise ValueError('Missing timezone')
                if not query.start_date <= value.astimezone(timezone.utc).date() <= query.end_date: return None
            elif provider != 'earth-search':
                raise ValueError('Missing acquisition date')
            item=prepare(raw)
            if item is not None and query.max_scene_cloud_cover is not None:
                cloud=item.get('scene_cloud_cover')
                if cloud is None or cloud>query.max_scene_cloud_cover:return None
            if item is not None and query.requested_resolution_m is not None:
                resolutions=item.get('resolution_m') or []
                if not resolutions or min(resolutions)>query.requested_resolution_m:return None
            return item
        runnable=[];excluded=[]
        for collection in selected:
            registration=COLLECTION_REGISTRY[collection];reason=None
            if registration.get('start') and str(query.end_date)<registration['start']:reason='outside_supported_period'
            if collection==noaa_nodd.COLLECTION and purpose!='vegetation':reason='purpose_not_supported'
            if reason:
                excluded.append({'provider_id':provider,'collection':collection,'status':'outside_scope','reason':reason,'complete':True,'requests':0,'returned':0,'fetched':0,'duplicates':0,'invalid':0,'filtered':0,'error':None,'last_datetime':None,'buffered_not_returned':0,'has_more':False})
            else:runnable.append(collection)
        result=await stac.search_collections(query,runnable,checked,
            adapter={'copernicus':copernicus,'nasa-cmr':cmr,'planetary-computer':planetary,'noaa-nodd':noaa_nodd}.get(provider),provider_id=provider,
            request_cap=None if provider=='earth-search' else PROVIDERS[provider]['max_requests']) if runnable else {'items':[],'collection_statuses':[],'search_budget':{'requests':0,'max_requests':PROVIDERS[provider]['max_requests']}}
        result['collection_statuses'].extend(excluded)
        return result
    results = await asyncio.gather(*(run(p,c) for p,c in groups.items()))
    # Keep one provider's abundance or outage from hiding another provider's search.
    queues = [deque(r['items']) for r in results]
    items = []
    while len(items) < query.max_items and any(queues):
        for queue in queues:
            if queue and len(items) < query.max_items: items.append(queue.popleft())
    statuses = [s for r in results for s in r['collection_statuses']]
    for status in statuses:
        count = sum(i.get('provider_id') == status['provider_id'] and i['collection'] == status['collection'] for i in items)
        removed = status['returned'] - count
        if removed:
            status.update(returned=count, buffered_not_returned=status['buffered_not_returned']+removed,
                          complete=False, has_more=True)
            if status['status'] not in ('failed','partial'): status.update(status='limited',reason='total_limit')
    failed = all(s['status'] == 'failed' for s in statuses)
    partial = any(s['status'] in ('failed','partial','not_started') for s in statuses)
    return {'items': items, 'collection_statuses': statuses,
            'outcome': 'outside_scope' if statuses and all(s['status']=='outside_scope' for s in statuses) else 'failed' if failed else 'partial' if partial else 'success' if items else 'empty' if all(s['complete'] for s in statuses) else 'partial',
            'truncated': any(not s['complete'] for s in statuses),
            'search_budget': {'requests': sum(r['search_budget']['requests'] for r in results),
                              'max_requests': sum(r['search_budget']['max_requests'] for r in results),
                              'seconds_limit': stac.SEARCH_SECONDS, 'request_seconds_limit': stac.REQUEST_SECONDS,
                              'elapsed_seconds': round(monotonic()-started, 2)},
            'provider_budgets': {p:r['search_budget'] for p,r in zip(groups, results)}}

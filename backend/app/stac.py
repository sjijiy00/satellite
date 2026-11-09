"""Bounded STAC paging with independent collection results and failure state."""
import asyncio
from collections import deque
from time import monotonic
from urllib.parse import urljoin, urlsplit
import httpx
from .safe_urls import safe_url

STAC_URL = 'https://earth-search.aws.element84.com/v1'
MAX_REQUESTS = 12
SEARCH_SECONDS = 45
REQUEST_SECONDS = 10
PAGE_SIZE = 25


class CatalogError(Exception):
    def __init__(self, message, status=502):
        self.message, self.status = message, status


async def request_page(client, request, seconds):
    response = await asyncio.wait_for(client.request(request['method'], request['url'],
        json=request.get('body') if request['method'] == 'POST' else None,
        headers=request.get('headers'), timeout=httpx.Timeout(seconds, connect=min(5, seconds))), seconds)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict) or not isinstance(data.get('features'), list) or len(data['features']) > 1000:
        raise ValueError('Invalid STAC page')
    return data


def next_request(data, original, current):
    link = next((x for x in data.get('links', []) if x.get('rel') == 'next'), None)
    if not link:
        return None
    url = urljoin(current['url'], link['href'])
    if not safe_url(url, ('https',)) or urlsplit(url).netloc != urlsplit(original['url']).netloc:
        raise ValueError('Unsupported pagination destination')
    method = link.get('method', 'GET').upper()
    if method not in ('GET', 'POST'):
        raise ValueError('Unsupported pagination method')
    body = (original.get('body', {}) | link.get('body', {})) if link.get('merge') else link.get('body')
    # Never replay upstream-supplied authorization/cookie headers.
    return {'url': url, 'method': method, 'body': body, 'headers': {}}


async def search_collections(query, collections, prepare, *, adapter=None, provider_id='earth-search', request_cap=None):
    started = monotonic()
    cap = MAX_REQUESTS if request_cap is None else request_cap
    states = []
    for collection in collections:
        initial = {'url': STAC_URL + '/search', 'method': 'POST', 'body': {
            'collections': [collection], 'bbox': list(query.bbox),
            'datetime': f'{query.start_date}T00:00:00Z/{query.end_date}T23:59:59.999999Z',
            'limit': PAGE_SIZE, 'sortby': [{'field': 'properties.datetime', 'direction': 'desc'}]}}
        if adapter:
            initial = adapter.initial(query, collection)
        states.append({'collection': collection, 'initial': initial, 'next': initial,
            'buffer': deque(), 'seen': set(), 'requests': 0, 'pages': 0, 'returned': 0,
            'fetched': 0, 'duplicates': 0, 'invalid': 0, 'filtered':0, 'error': None, 'error_code': None,
            'exhausted': False, 'last_datetime': None})
    items, requests, stop_reason = [], 0, None
    async with httpx.AsyncClient(follow_redirects=False) as client:
        while len(items) < query.max_items:
            active = False
            for state in states:
                if len(items) >= query.max_items:
                    break
                if not state['buffer'] and state['next'] and not state['error']:
                    remaining = SEARCH_SECONDS - (monotonic() - started)
                    if remaining <= 0 or requests >= cap:
                        stop_reason = 'time_limit' if remaining <= 0 else 'request_limit'
                    else:
                        active = True
                        current = state['next']
                        state['requests'] += 1
                        requests += 1
                        try:
                            page = await (adapter.request_page if adapter else request_page)(client, current, min(REQUEST_SECONDS, remaining))
                            state['pages'] += 1
                            for raw in page['features']:
                                try:
                                    if raw.get('collection') != state['collection'] or not isinstance(raw.get('id'), str):
                                        raise ValueError('Item identity mismatch')
                                    key = (provider_id, raw['collection'], raw['id'])
                                    if key in state['seen']:
                                        state['duplicates'] += 1
                                        continue
                                    item = prepare(raw)
                                    state['seen'].add(key)
                                    if item is None:
                                        state['filtered'] += 1
                                        continue
                                    state['buffer'].append(item)
                                    state['fetched'] += 1
                                    state['last_datetime'] = item.get('datetime')
                                except (KeyError, TypeError, ValueError, AttributeError):
                                    state['invalid'] += 1
                            state['next'] = next_request(page, state['initial'], current)
                            state['exhausted'] = state['next'] is None
                        except (httpx.TimeoutException, asyncio.TimeoutError):
                            state['error'], state['error_code'] = '제공처 응답 시간 초과', 'timeout'
                        except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError):
                            state['error'], state['error_code'] = '제공처 연결·응답 형식 또는 페이지 처리 실패', 'provider_error'
                if state['buffer']:
                    active = True
                    items.append(state['buffer'].popleft())
                    state['returned'] += 1
            if not active:
                break
    statuses = []
    for s in states:
        incomplete = bool(s['buffer']) or not s['exhausted'] or bool(s['invalid'])
        if s['error'] or s['invalid']:
            status = 'partial' if s['fetched'] else 'failed'
        elif incomplete:
            status = 'limited' if s['pages'] else 'not_started'
        else:
            status = 'success' if s['returned'] else 'empty'
        reason = s['error_code'] or ('invalid_metadata' if s['invalid'] else
                 ('total_limit' if len(items) >= query.max_items else stop_reason) if incomplete else 'exhausted')
        statuses.append({k: s[k] for k in ('collection', 'requests', 'returned', 'fetched', 'duplicates', 'invalid', 'filtered', 'error', 'last_datetime')} |
            {'provider_id': provider_id} |
            {'status': status, 'reason': reason, 'complete': not incomplete,
             'buffered_not_returned': len(s['buffer']),
             'has_more': True if s['buffer'] or (s['pages'] and s['next'] and not s['error']) else False if s['exhausted'] else None})
    failed = all(s['status'] == 'failed' for s in statuses)
    partial = any(s['status'] in ('failed', 'partial', 'not_started') for s in statuses)
    outcome = 'failed' if failed else 'partial' if partial else 'success' if items else 'empty' if all(s['complete'] for s in statuses) else 'partial'
    return {'items': items, 'collection_statuses': statuses, 'outcome': outcome,
            'truncated': any(not s['complete'] for s in statuses),
            'search_budget': {'requests': requests, 'max_requests': cap,
                'seconds_limit': SEARCH_SECONDS, 'request_seconds_limit': REQUEST_SECONDS,
                'elapsed_seconds': round(monotonic() - started, 2)}}

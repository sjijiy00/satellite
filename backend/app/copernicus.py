"""Anonymous CDSE STAC metadata only. No token acquisition, downloads or SAR processing."""
from urllib.parse import urlencode
from . import stac
from .provider_registry import PROVIDERS

ENDPOINT = PROVIDERS['copernicus']['endpoint']


def initial(query, collection):
    # Official GET Item Search, with next-link paging. No guessed OData path.
    params = {'collections': collection, 'bbox': ','.join(map(str, query.bbox)),
              'datetime': f'{query.start_date}T00:00:00Z/{query.end_date}T23:59:59.999999Z',
              'limit': stac.PAGE_SIZE, 'sortby': '-datetime'}
    return {'method': 'GET', 'url': ENDPOINT + '/search?' + urlencode(params)}


async def request_page(client, request, seconds):
    return await stac.request_page(client, request, seconds)

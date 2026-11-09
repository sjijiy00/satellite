"""Small, process-local preview cache/single-flight; never caches original files."""
from collections import OrderedDict
import asyncio
from tempfile import SpooledTemporaryFile
import time
from .provider_transfer import Payload,TransferError

LIMIT=16*1024**2
TTL=60
cache=OrderedDict()
pending={}


async def read(key,factory,validate):
    now=time.monotonic()
    for k in list(cache):
        if cache[k][0]<now:cache.pop(k,None)
    if key not in cache:
        task=pending.get(key)
        if task is None:
            if len(pending)>=2:raise TransferError('operator_busy')
            async def receive():
                payload,generation=await factory()
                try:content,media=validate(payload)
                finally:payload.close()
                while cache and sum(len(v[1]) for v in cache.values())+len(content)>LIMIT:cache.popitem(last=False)
                cache[key]=(time.monotonic()+TTL,content,media,generation)
                return cache[key]
            task=asyncio.create_task(receive());pending[key]=task
            def finish(completed):
                if pending.get(key) is completed:pending.pop(key,None)
                if not completed.cancelled():completed.exception() # retrieve even if all subscribers cancelled
            task.add_done_callback(finish)
        value=await asyncio.shield(task)
    else:cache.move_to_end(key);value=cache[key]
    _,content,media,generation=value
    file=SpooledTemporaryFile(max_size=8*1024**2);file.write(content);file.seek(0)
    return Payload(file,len(content),media,True,200),generation

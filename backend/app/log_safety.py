"""Keep OAuth codes and media receipts out of uvicorn's request-target logs."""
import logging


class AccessFilter(logging.Filter):
    def filter(self,record):
        if isinstance(record.args,tuple) and len(record.args)==5:
            values=list(record.args);target=values[2]
            if isinstance(target,str):
                path=target.split('?',1)[0]
                if path=='/auth/earthdata/callback':values[2]=path+'?<redacted>'
                elif path.startswith(('/media/previews/','/media/downloads/')):
                    values[2]='/media/<redacted>'
                record.args=tuple(values)
        return True


class ProviderHTTPFilter(logging.Filter):
    def filter(self,record):
        # httpx INFO includes full signed download URLs; httpcore DEBUG may include
        # Authorization headers. Never stringify their original message/arguments.
        record.msg='Provider HTTP diagnostic details omitted';record.args=()
        if record.exc_info:record.exc_info=None;record.exc_text=None
        return True


def install():
    logger=logging.getLogger('uvicorn.access')
    if not any(isinstance(f,AccessFilter) for f in logger.filters):logger.addFilter(AccessFilter())
    for name in ('httpx','httpcore','httpcore.connection','httpcore.http11','httpcore.http2','httpcore.proxy','httpcore.socks','httpcore.pool'):
        upstream=logging.getLogger(name)
        if not any(isinstance(f,ProviderHTTPFilter) for f in upstream.filters):upstream.addFilter(ProviderHTTPFilter())

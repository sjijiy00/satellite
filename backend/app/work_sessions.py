"""Local browser ownership for plans/jobs, separate from provider authentication.

Signed HttpOnly cookie; key and existing jobs die on server restart. No user
credentials, no query parameters, no browser storage, no public account system.
"""
import hashlib
import hmac
import os
import re
import secrets
import time
from fastapi import HTTPException
from .public_site import public_origin

COOKIE='satellite_work_session'
from .processing_repository import session_key
KEY=session_key()
TTL=7*24*3600


def identity(request,create=False):
    raw=request.cookies.get(COOKIE,'')
    if re.fullmatch(r'[a-f0-9]{32}\.\d{10}\.[a-f0-9]{64}',raw):
        payload,signature=raw.rsplit('.',1)
        if hmac.compare_digest(signature,hmac.new(KEY,payload.encode(),hashlib.sha256).hexdigest()) and int(payload.split('.')[1])>time.time():
            return payload.split('.')[0],raw
    if not create:return None,None
    identifier=secrets.token_hex(16);payload=f'{identifier}.{int(time.time())+TTL}'
    return identifier,payload+'.'+hmac.new(KEY,payload.encode(),hashlib.sha256).hexdigest()


def protect(request):
    origin=request.headers.get('origin')
    allowed={str(request.base_url).rstrip('/'),os.getenv('OPERATOR_PUBLIC_ORIGIN','http://127.0.0.1:3000').rstrip('/')}
    if public_origin():allowed.add(public_origin())
    if origin and origin not in allowed:raise HTTPException(403,'다른 사이트에서 작업을 변경할 수 없습니다.')


def require_owner(request,value):
    identifier,_=identity(request)
    if not identifier or value.get('owner')!=identifier:raise HTTPException(404,'현재 세션의 작업이 없거나 만료되었습니다.')


def attach(response,request,cookie):
    response.set_cookie(COOKIE,cookie,max_age=TTL,httponly=True,samesite='strict',secure=request.url.scheme=='https',path='/')
    return response

"""Opt-in, server-only OpenAI extraction. No tools, geocoding, imagery or execution."""
import asyncio
import calendar
from collections import OrderedDict, deque
from datetime import date
import hashlib
import json
import math
import os
import re
import time
import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from typing import Literal
from .ai_conditions import Extraction,PROMPT,conditions as _conditions

lock=asyncio.Lock()
cache=OrderedDict()
recent=deque()
stats={'requests':0,'succeeded':0,'failed':0,'cancelled':0,'cache_hits':0,'input_tokens':0,'output_tokens':0,'unknown_usage_calls':0,'last_status':'not_called'}

QUOTA_CODES={'insufficient_quota','credit_balance_exhausted','organization_spend_limit_exceeded','project_spend_limit_exceeded','organization_usage_limit_exceeded'}
PUBLIC_ERROR_CODES=QUOTA_CODES|{'rate_limit_exceeded','slow_down','server_is_overloaded','invalid_api_key','model_not_found'}

class ProviderError(RuntimeError):
    def __init__(self,status,code=None,retry_after=None):
        self.status=status
        self.code=code if isinstance(code,str) and code in PUBLIC_ERROR_CODES else None
        self.retry_after=int(retry_after) if isinstance(retry_after,str) and retry_after.isascii() and retry_after.isdigit() and len(retry_after)<=4 and 0<int(retry_after)<=3600 else None

def provider_failure(status,raw,retry_after=None):
    # Preserve only recognized codes, never provider messages, headers or keys.
    try:
        error=json.loads(raw).get('error',{})
        code=error.get('code') or error.get('type')
    except (ValueError,AttributeError,TypeError):code=None
    return ProviderError(status,code,retry_after)


def config():
    def bounded(name,default,low,high):
        try:value=int(os.getenv(name,str(default)))
        except ValueError:return default
        return max(low,min(high,value))
    provider=os.getenv('AI_NL_PROVIDER','').strip()
    model=os.getenv('AI_NL_MODEL','').strip()
    enabled=os.getenv('AI_NL_ENABLED','')=='1'
    valid_model=bool(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,99}',model))
    ready=enabled and provider=='openai' and valid_model and bool(os.getenv('OPENAI_API_KEY','').strip())
    missing=[]
    if not enabled:missing.append('AI_NL_ENABLED')
    if provider!='openai':missing.append('AI_NL_PROVIDER')
    if not valid_model:missing.append('AI_NL_MODEL')
    if not os.getenv('OPENAI_API_KEY','').strip():missing.append('OPENAI_API_KEY')
    return {'missing_settings':missing,'ready':ready,'provider':'openai' if provider=='openai' else None,'model':model if valid_model else None,
            'message':'입력을 마치면 OpenAI에 문장을 전송합니다. 자동 해석은 사용량·비용이 발생할 수 있습니다.' if ready else
            'AI 미연결: 서버 AI_NL_ENABLED, AI_NL_PROVIDER, AI_NL_MODEL, OPENAI_API_KEY 설정이 필요합니다. 규칙 대체 해석 없이 직접 조건을 입력할 수 있습니다.',
            'limits':{'timeout_seconds':bounded('AI_NL_TIMEOUT_SECONDS',12,10,90),'max_input_chars':2000,
                      'max_output_tokens':bounded('AI_NL_MAX_OUTPUT_TOKENS',2000,1000,8000),
                      'requests_per_minute':bounded('AI_NL_REQUESTS_PER_MINUTE',6,1,20),
                      'requests_per_process':bounded('AI_NL_REQUESTS_PER_PROCESS',100,1,1000),'concurrency':1,'cache_seconds':600}}


def public_status():
    def price(name):
        try:
            value=float(os.getenv(name,''))
            return value if math.isfinite(value) and value>=0 else None
        except ValueError:return None
    ip,op=price('AI_NL_INPUT_USD_PER_MILLION'),price('AI_NL_OUTPUT_USD_PER_MILLION')
    cost=None if ip is None or op is None else (stats['input_tokens']*ip+stats['output_tokens']*op)/1_000_000
    return {**config(),'usage':{**stats,'estimated_usd_reported_tokens':cost,'billing_note':'프로세스 내 보고된 토큰만 집계. 실제 청구는 제공처에서 확인. 취소·네트워크 실패는 청구량 미확인일 수 있음.'}}


async def _send(payload,key):
    # Fixed official origin. Neither user input nor AI output can choose URLs/headers.
    async with httpx.AsyncClient(timeout=config()['limits']['timeout_seconds'],follow_redirects=False,trust_env=False) as client:
        async with client.stream('POST','https://api.openai.com/v1/responses',headers={'Authorization':'Bearer '+key},json=payload) as response:
            raw=bytearray()
            async for chunk in response.aiter_bytes():
                raw.extend(chunk)
                if len(raw)>65536:
                    if response.status_code!=200:raise ProviderError(response.status_code)
                    raise ValueError('response_limit')
            if response.status_code!=200:raise provider_failure(response.status_code,raw,response.headers.get('retry-after'))
            return json.loads(raw)


def _failure(code,message,diagnostic=None):
    return {'status':'failed','period':{'status':'absent'},'region':{'status':'absent'},'messages':[message],
            'event_reference_required':False,'scope':'실패한 AI 응답은 적용하지 않음',
            'engine':{'mode':'ai','status':code,'provider':config()['provider'],'model':config()['model'],'usage':public_status()['usage'],**({'diagnostic':diagnostic} if diagnostic else {})}}


async def propose_with_ai(text,selected_id=None):
    cfg=config()
    if not cfg['ready']:return _failure('not_configured',cfg['message'])
    key=hashlib.sha256(('detail-flow-1\0'+cfg['model']+'\0'+text).encode()).hexdigest()
    saved=cache.get(key)
    if saved and time.monotonic()-saved[0]<600:
        try:result=_conditions(saved[1],text,selected_id)
        except ValueError:return _failure('invalid_response','AI 응답 필드 검증 실패. 기존 조건을 유지합니다.')
        stats['cache_hits']+=1
        result['engine']={'mode':'ai','status':'cached','provider':'openai','model':cfg['model'],'usage':public_status()['usage']}
        return result
    while recent and time.monotonic()-recent[0]>60:recent.popleft()
    limits=cfg['limits']
    if len(recent)>=limits['requests_per_minute'] or stats['requests']>=limits['requests_per_process']:return _failure('limited',f"앱 AI 호출 상한(분당 {limits['requests_per_minute']}회·프로세스당 {limits['requests_per_process']}회)에 도달했습니다. 기존 조건을 유지합니다.")
    if lock.locked():return _failure('busy','다른 AI 해석 중입니다. 완료 후 다시 요청하세요.')
    async with lock:
        recent.append(time.monotonic());stats['requests']+=1;stats['last_status']='running'
        payload={'model':cfg['model'],'store':False,'max_output_tokens':limits['max_output_tokens'],'instructions':PROMPT,'input':text,
                 'text':{'format':{'type':'json_schema','name':'analysis_request','strict':True,'schema':Extraction.model_json_schema()}}}
        if cfg['model']=='gpt-5.6-luna':payload['reasoning']={'effort':'none'}
        usage_known=False
        try:
            async with asyncio.timeout(limits['timeout_seconds']):body=await _send(payload,os.environ['OPENAI_API_KEY'])
            usage=body.get('usage') or {}
            for field in ('input_tokens','output_tokens'):
                if type(usage.get(field)) is int and 0<=usage[field]<=100000:stats[field]+=usage[field]
            usage_known=all(type(usage.get(f)) is int for f in ('input_tokens','output_tokens'))
            if body.get('status')!='completed':raise ValueError('incomplete response')
            content=[c for item in body.get('output',[]) if item.get('type')=='message' for c in item.get('content',[])]
            if any(c.get('type')=='refusal' for c in content):raise ValueError('refusal')
            chunks=[c['text'] for c in content if c.get('type')=='output_text']
            if len(chunks)!=1:raise ValueError('missing output')
            extracted=Extraction.model_validate_json(chunks[0]);result=_conditions(extracted,text,selected_id)
            cache[key]=(time.monotonic(),extracted)
            if len(cache)>128:cache.popitem(last=False)
            stats['succeeded']+=1;stats['last_status']='succeeded'
            result['engine']={'mode':'ai','status':'succeeded','provider':'openai','model':cfg['model'],'usage':public_status()['usage']}
            return result
        except asyncio.CancelledError:
            stats['cancelled']+=1;stats['last_status']='cancelled';raise
        except (TimeoutError,httpx.TimeoutException):
            stats['failed']+=1;stats['last_status']='timeout'
            return _failure('timeout',f"AI 응답 시간 상한 {limits['timeout_seconds']}초를 초과했습니다. 기존 조건을 유지합니다.")
        except (ValueError,ValidationError,KeyError,TypeError,AttributeError):
            stats['failed']+=1;stats['last_status']='invalid_response'
            return _failure('invalid_response','AI 응답이 누락되었거나 허용 스키마/명시 날짜/원문 근거에 맞지 않습니다. 기존 조건을 유지합니다.')
        except ProviderError as error:
            stats['failed']+=1
            code='authentication_failed' if error.status in (401,403) else 'quota_exceeded' if error.status==429 and error.code in QUOTA_CODES else 'limited' if error.status==429 else 'request_rejected' if error.status==400 else 'provider_unavailable'
            stats['last_status']=code
            message={'authentication_failed':'OpenAI가 인증·모델 접근을 거부했습니다. 기존 서버 설정·계정 권한을 확인하세요.',
                'quota_exceeded':'OpenAI API 크레딧·조직/프로젝트 예산 또는 할당량에 도달했습니다. 운영자가 API Billing·Limits를 확인해야 합니다. 반복 재시도로 해결되지 않습니다. 직접 입력은 계속 사용할 수 있습니다.',
                'limited':'OpenAI 요청 제한(HTTP 429)입니다. 잠시 후 명시적으로 재시도하세요.' if error.code in ('rate_limit_exceeded','slow_down') else 'OpenAI 한도 응답(HTTP 429)입니다. 세부 원인은 미확인입니다. API 크레딧·프로젝트 한도와 요청 제한을 확인하세요.',
                'request_rejected':'OpenAI가 모델·구조화 요청을 거부했습니다. 서버의 기존 모델 지원 여부를 확인하세요.',
                'provider_unavailable':'OpenAI 서비스가 정상 응답하지 않았습니다. 재시도 또는 직접 입력을 선택하세요.'}[code]
            if error.code=='credit_balance_exhausted':message='OpenAI API 선불 크레딧이 소진되었습니다. 운영자가 API Billing에서 크레딧을 충전해야 합니다. 반복 재시도로 해결되지 않습니다. 직접 입력은 AI 없이 계속 사용할 수 있습니다.'
            if error.retry_after:message+=f' 제공처 대기 안내: 최소 {error.retry_after}초.'
            return _failure(code,message,{'http_status':error.status,'error_code':error.code,'retry_after_seconds':error.retry_after})
        except (httpx.HTTPError,RuntimeError):
            stats['failed']+=1;stats['last_status']='provider_error'
            return _failure('provider_error','OpenAI 연결/인증/요청에 실패했습니다. 서버 설정·제공처 사용량을 확인하세요. 기존 조건을 유지합니다.')
        finally:
            if not usage_known:stats['unknown_usage_calls']+=1

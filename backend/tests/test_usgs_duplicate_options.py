"""Synthetic M2M options: no external credentials or requests."""
import asyncio
import pytest
from app import operator_adapters as adapters
from app.provider_transfer import TransferError

@pytest.mark.parametrize('variant,expected',[
    ('identical',None),('different_identity','operator_file_unavailable'),
    ('checksum_conflict','product_mismatch'),('size_conflict','product_mismatch'),
    ('missing_identity','operator_invalid_response'),('unavailable','operator_file_unavailable'),
])
def test_repeated_band_under_multiple_bundles(monkeypatch,variant,expected):
    product='LC08_L2SP_115035_20260711_20260720_02_T1';filename=product+'_QA_PIXEL.TIF'
    first={'entityId':'TEST_ONLY_FILE','id':'TEST_ONLY_PRODUCT','displayId':filename,'available':True,'checksum':'TEST_ONLY_A','filesize':1024}
    second={**first}
    if variant=='different_identity':second['entityId']='TEST_ONLY_OTHER'
    if variant=='checksum_conflict':second['checksum']='TEST_ONLY_B'
    if variant=='size_conflict':second['filesize']=2048
    if variant=='missing_identity':second.pop('entityId')
    if variant=='unavailable':first['available']=second['available']=False
    requests=[]
    async def fake(method,body,token):
        if method=='scene-metadata':return {'displayId':product,'entityId':'TEST_ONLY_SCENE'}
        if method=='download-options':return [{'secondaryDownloads':[first]},{'secondaryDownloads':[{**first,'checksum':None,'filesize':None}]},{'secondaryDownloads':[second]}]
        if method=='download-request':
            requests.append(body)
            return {'availableDownloads':[{'url':'https://landsatlook.usgs.gov/data/collection02/'+filename}]}
        raise AssertionError(method)
    monkeypatch.setattr(adapters,'m2m',fake)
    if expected:
        with pytest.raises(TransferError,match=expected):asyncio.run(adapters.exact_display_scene(product,filename,'TEST_ONLY'))
        assert not requests
    else:
        result=asyncio.run(adapters.exact_display_scene(product,filename,'TEST_ONLY'))
        assert result['filename']==filename
        assert len(requests)==1 and requests[0]['downloads']==[{'entityId':'TEST_ONLY_FILE','productId':'TEST_ONLY_PRODUCT'}]

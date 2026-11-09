"""Private bounded artifacts, atomic publication, reopen verification and TTL."""
from pathlib import Path
import hashlib
import io
import json
import re
import shutil
import time
import zipfile
import os
from datetime import datetime, timezone
import numpy as np
import rasterio
from rasterio.io import MemoryFile
from .pixel_policy import QualityError

ROOT=Path(__file__).resolve().parent.parent/'.private/processing'
ZIP_LIMIT=16*1024**2
UNCOMPRESSED_LIMIT=32*1024**2
def setting(name,default,minimum,maximum):
    try:value=int(os.getenv(name,str(default)))
    except ValueError:raise RuntimeError(name+': 정수 설정이 필요합니다.') from None
    if not minimum<=value<=maximum:raise RuntimeError(name+': 로컬 보관 설정 상한을 확인하세요.')
    return value

DISK_LIMIT=setting('PROCESSING_STORAGE_MIB',1024,64,8192)*1024**2
TTL=setting('PROCESSING_RETENTION_SECONDS',7*86400,60,30*86400)

def safe_value(value,*,include_maps=False):
    if isinstance(value,dict):
        return {k:safe_value(v,include_maps=include_maps) for k,v in value.items() if not re.search(r'token|password|secret|authorization|cookie|artifact_base64',k,re.I) and (include_maps or k!='png_base64')}
    if isinstance(value,list):return [safe_value(v,include_maps=include_maps) for v in value]
    if isinstance(value,str) and (re.search(r'https?://\S*\?',value) or re.search(r'Bearer\s',value,re.I)):
        raise QualityError('서명/인증 문자열이 포함된 산출물은 게시하지 않습니다.')
    return value

def folder(identifier):
    if not re.fullmatch('[a-f0-9]{32}',identifier):raise QualityError('안전한 작업 식별자가 아닙니다.')
    return ROOT/identifier

def cleanup(active=()):
    if not ROOT.exists():return
    for p in ROOT.iterdir():
        if p.is_dir() and not p.is_symlink() and p.name not in active and re.fullmatch(r'[a-f0-9]{32}(?:\.tmp)?',p.name) and time.time()-p.stat().st_mtime>TTL:
            try:shutil.rmtree(p)
            except PermissionError:pass # A bounded download may still have the file open on Windows.

def discard(identifier):
    p=folder(identifier)
    for target in (p,p.with_name(p.name+'.tmp')):
        if target.exists() and not target.is_symlink():
            try:shutil.rmtree(target)
            except PermissionError:pass

def tiff_bytes(array,grid,nodata,names,unit='1'):
    if array.ndim==2:array=array[None]
    with MemoryFile() as memory:
        with memory.open(driver='GTiff',height=grid['height'],width=grid['width'],count=len(array),
            dtype=array.dtype,crs=grid['crs'],transform=grid['transform'],nodata=nodata,compress='deflate') as dst:
            dst.write(array)
            for i,name in enumerate(names,1):dst.set_band_description(i,name);dst.update_tags(i,unit=unit[i-1] if isinstance(unit,list) else unit)
        return memory.read()

def unpack_artifact(content):
    if len(content)>ZIP_LIMIT:raise QualityError('ZIP 출력 상한 초과')
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        if len(z.infolist())>24 or sum(f.file_size for f in z.infolist())>UNCOMPRESSED_LIMIT:
            raise QualityError('ZIP 해제 크기 상한 초과')
        files={}
        for f in z.infolist():
            if not re.fullmatch(r'[A-Za-z0-9_-]+\.(tif|json)',f.filename) or f.filename in files:
                raise QualityError('잘못된 ZIP 파일 경로/중복 이름')
            files[f.filename]=z.read(f)
        return files

def publish(identifier,files,manifest,required,specs=None):
    destination=folder(identifier);temporary=destination.with_name(destination.name+'.tmp')
    if destination.exists():raise QualityError('같은 작업의 산출물을 덮어쓰지 않습니다.')
    ROOT.mkdir(parents=True,exist_ok=True)
    usage=sum(f.stat().st_size for f in ROOT.rglob('*') if f.is_file())
    size=sum(len(b) for b in files.values())
    if usage+size*3>DISK_LIMIT or shutil.disk_usage(ROOT).free<size*3+32*1024**2:
        raise QualityError('산출물 저장 공간/사용량 상한. 만료 파일 정리 후 AOI를 줄여 주세요.')
    if not set(required)-{'manifest.json'}<=files.keys():raise QualityError('필수 실제 산출물이 누락됐습니다.')
    temporary.mkdir(exist_ok=False)
    try:
        evidence={};reference=None
        for name,data in files.items():
            if not re.fullmatch(r'[A-Za-z0-9_-]+\.(tif|json)',name):raise QualityError('안전한 산출물 이름이 아닙니다.')
            path=temporary/name;path.write_bytes(data)
            if name.endswith('.tif'):
                with rasterio.open(path) as ds:
                    if not ds.crs or ds.nodata is None or ds.count<1:raise QualityError('GeoTIFF CRS/NoData/밴드 검증 실패')
                    spec=(specs or {}).get(name)
                    if spec:
                        if ds.count!=spec['bands'] or any(t!=spec['dtype'] for t in ds.dtypes) or ds.nodata!=spec['nodata']:
                            raise QualityError(name+': GeoTIFF 밴드 수/자료형/NoData가 서버 산출물 계약과 다릅니다.')
                        if any(ds.tags(i).get('unit')!=(spec['units'][i-1] if 'units' in spec else spec['unit']) for i in range(1,ds.count+1)):
                            raise QualityError(name+': GeoTIFF 단위가 서버 산출물 계약과 다릅니다.')
                    current=(ds.crs.to_wkt(),ds.transform,ds.width,ds.height)
                    expected=manifest.get('grid',{})
                    if (ds.width,ds.height)!=(expected.get('width'),expected.get('height')):
                        raise QualityError('GeoTIFF 크기와 계획 격자가 다릅니다.')
                    if rasterio.crs.CRS.from_user_input(expected.get('crs'))!=ds.crs or not np.allclose(list(ds.transform)[:6],expected.get('transform',[]),atol=1e-8,rtol=0):
                        raise QualityError('GeoTIFF CRS/transform과 계획 격자가 다릅니다.')
                    if reference is not None and current!=reference:raise QualityError('산출물의 범위/격자가 서로 다릅니다.')
                    reference=current
                    pixels=ds.read()
                    if not np.isfinite(pixels).all():raise QualityError('GeoTIFF에 NaN/Inf가 있습니다.')
                    if name=='valid_mask.tif' and (ds.count!=1 or ds.dtypes[0]!='uint8' or not np.isin(pixels,[0,1]).all()):
                        raise QualityError('유효 마스크 형식이 잘못됐습니다.')
                    if name=='exclusion_mask.tif' and not np.isin(pixels,[0,1,2,3]).all():raise QualityError('제외 마스크 형식이 잘못됐습니다.')
                    evidence[name]={'bytes':path.stat().st_size,
                        'width':ds.width,'height':ds.height,'bands':ds.count,'dtype':ds.dtypes,'nodata':ds.nodata,
                        'crs':ds.crs.to_wkt(),'transform':list(ds.transform)[:6],'descriptions':ds.descriptions,
                        'units':[ds.tags(i).get('unit','미제공') for i in range(1,ds.count+1)],'reopened':True}
                # Never rewrite legacy engine files after their own manifest
                # hashes have been created. Hash the final on-disk bytes.
                with rasterio.open(path) as reopened:
                    if reopened.count!=evidence[name]['bands']:raise QualityError('GeoTIFF 최종 재열기 실패')
                evidence[name].update(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size)
            else:
                safe_value(json.loads(data))
                evidence[name]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size}
        if not reference:raise QualityError('실제 GeoTIFF가 없는 작업은 성공으로 게시하지 않습니다.')
        from .processing_record import completed_record
        record=completed_record(manifest,evidence)
        manifest=safe_value({**manifest,'files':evidence,'execution_record':record,'verified_after_disk_write':True})
        (temporary/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,allow_nan=False,indent=2),encoding='utf8')
        zip_path=temporary/'result.zip'
        with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
            for path in sorted(temporary.iterdir()):
                if path!=zip_path:z.write(path,path.name)
        if zip_path.stat().st_size>ZIP_LIMIT:raise QualityError('ZIP 16 MiB 출력 상한 초과. AOI를 줄여 주세요.')
        with zipfile.ZipFile(zip_path) as z:
            if z.testzip() is not None:raise QualityError('ZIP 무결성 검사 실패')
        content=zip_path.read_bytes()
        receipt={'filename':'processing-'+identifier+'.zip','bytes':len(content),'sha256':hashlib.sha256(content).hexdigest(),
                 'files':list(evidence)+['manifest.json'],'expires_in_seconds':TTL,
                 'created_at':datetime.fromtimestamp(zip_path.stat().st_mtime,timezone.utc).isoformat(),
                 'expires_at':datetime.fromtimestamp(zip_path.stat().st_mtime+TTL,timezone.utc).isoformat(),
                 'execution_record':record}
        temporary.rename(destination)
        return receipt
    except BaseException:
        if temporary.exists():shutil.rmtree(temporary)
        raise

def verified_download(identifier,receipt):
    path=folder(identifier)/'result.zip'
    if not path.is_file() or time.time()-path.stat().st_mtime>TTL:raise QualityError('산출물이 만료되었거나 파일이 없습니다.')
    if path.stat().st_size!=receipt['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest()!=receipt['sha256']:
        raise QualityError('저장 파일의 크기/해시가 변경되어 다운로드를 중단합니다.')
    return path

def retention(identifier,receipt):
    """Poll-safe presence/size check. Download rechecks the full hash separately."""
    if not receipt:return {'state':'not_created','remaining_seconds':0,'expires_at':None}
    path=folder(identifier)/'result.zip'
    if not path.is_file():
        expiry=receipt.get('expires_at')
        expired=expiry and datetime.fromisoformat(expiry).timestamp()<=time.time()
        return {'state':'expired' if expired else 'missing','remaining_seconds':0,'expires_at':expiry}
    stat=path.stat();remaining=max(0,int(stat.st_mtime+TTL-time.time()))
    state='expired' if remaining<=0 else 'available' if stat.st_size==receipt['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest()==receipt['sha256'] else 'changed'
    return {'state':state,'remaining_seconds':remaining,
            'expires_at':datetime.fromtimestamp(stat.st_mtime+TTL,timezone.utc).isoformat()}

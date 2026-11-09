"""Canonical product adapters and bounded pixel calculations; no fixture fallback."""
from datetime import datetime,timezone
import json
import numpy as np
from rasterio.warp import Resampling
from shapely.geometry import shape,box
import shapely
from pyproj import Transformer
from . import media_access,planetary,artifact_store
from .product_policy import profile_for,asset_policy,VARIABLES,THERMAL,QA_VERSION,VERSION,SOURCES,SOURCE_VERSIONS,CHECKED_ON
from .pixel_policy import QualityError
from .pixel_raster import read_native,warp,area_weights as native_area_weights,project_footprint,map_preview,grid_info
from .processing_raster import processing_grid
from .range_reader import public_cog
from .band_math import index,FORMULAS
from .landsat_temperature import pixel_quality,kelvin_celsius,thermal_valid
from .processing_raster import SINGLE_METHODS,TILE_EDGE
from rasterio.transform import Affine
from contextlib import nullcontext


def area_weights(geometry,g):
    # Preserve the exact fractional-cell algorithm without allocating hundreds
    # of thousands of temporary Shapely cell geometries at once.
    if g['height']*g['width']<=150000:return native_area_weights(geometry,g)
    weights=np.zeros((g['height'],g['width']),dtype='float64')
    for top in range(0,g['height'],TILE_EDGE):
        for left in range(0,g['width'],TILE_EDGE):
            h=min(TILE_EDGE,g['height']-top);w=min(TILE_EDGE,g['width']-left)
            tile={**g,'height':h,'width':w,'transform':g['transform']*Affine.translation(left,top)}
            weights[top:top+h,left:left+w]=native_area_weights(geometry,tile)
    return weights

async def prepare(query):
    method=query.method_id;profile=profile_for(query.scenes[0].model_dump(),method)
    payload={'bbox':list(query.roi.bbox),'roi':query.roi.model_dump(),'grid_resolution_m':profile['resolution_m'],
        'method_id':method,'roi_fingerprint':query.roi.fingerprint(),'processing_input':query.model_dump(mode='json'),'scenes':[]}
    grid,_=processing_grid(payload) # reject area/cell limits before network
    dates=[]
    for i,ref in enumerate(query.scenes):
        raw=await media_access.canonical(ref.model_dump());p=raw.get('properties') or {};assets=raw.get('assets') or {}
        if raw.get('id')!=ref.id or raw.get('collection')!=ref.collection:raise QualityError('canonical Item 식별자/컬렉션 불일치')
        level=p.get('s2:product_type') or p.get('landsat:processing_level') or p.get('landsat:correction') or p.get('processing:level')
        if p.get('platform') not in profile['platforms'] or level not in (['L2SP'] if method in THERMAL else profile['levels']):raise QualityError('허용 플랫폼/제품 처리 수준 불일치. L2SR을 ST로 처리하지 않습니다.')
        if profile['profile_id']=='pc_landsat' and str(p.get('landsat:collection_number'))!='02':raise QualityError('Landsat Collection 2 버전 확인 필요')
        try:
            dt=datetime.fromisoformat(p['datetime'].replace('Z','+00:00'))
            if dt.tzinfo is None:raise ValueError()
            dt=dt.astimezone(timezone.utc)
        except (ValueError,KeyError,AttributeError):raise QualityError('촬영 UTC 시각 미확인') from None
        if not query.start_date<=dt.date()<=query.end_date:raise QualityError('허용 기간 밖 촬영 장면입니다.')
        dates.append(dt)
        scene={'id':ref.id,'collection':ref.collection,'provider_id':ref.provider_id,'datetime':dt.isoformat(),
            'geometry':raw.get('geometry'),'platform':p['platform'],'processing_level':level,'processing_baseline':p.get('s2:processing_baseline'),
            'boa_offset_applied':p.get('earthsearch:boa_offset_applied'),'profile':profile,'assets':{},
            'source_url':('https://earth-search.aws.element84.com/v1' if profile['profile_id']=='es_s2' else planetary.ENDPOINT)+'/collections/'+('landsat-c2-l2' if profile['profile_id']=='pc_landsat' else ref.collection)+'/items/'+ref.id}
        if project_footprint(scene['geometry'],grid).area<=0:raise QualityError('선택 장면이 확정 AOI와 겹치지 않습니다.')
        for key in profile['required_keys']:
            if key not in ref.asset_keys:raise QualityError('필수 밴드/QA 선택 누락: '+key)
            a=assets.get(key)
            if not a or a.get('storage:requester_pays') or not a.get('type','').startswith('image/tiff'):raise QualityError(key+': 실제 공개 COG/필수 QA Asset 미확인')
            if key in profile['bands'].values():
                spectral=a.get('eo:bands') or []
                if len(spectral)!=1 or spectral[0].get('common_name')!=key:raise QualityError(key+': 실제 스펙트럼 밴드 식별 메타데이터가 다릅니다.')
            url=a.get('href','')
            if profile['profile_id']=='es_s2':
                if not public_cog(url):raise QualityError('허용된 공개 S2 COG 경로가 아닙니다.')
            else:planetary.storage(ref.collection,url)
            scene['assets'][key]={**asset_policy(key,profile,a,p),'url':url,'path':f'scene{i}-{key}.tif'}
        payload['scenes'].append(scene)
    if len(dates)==2:
        a,b=payload['scenes']
        if method in ('thermal_gapfill','thermal_ml'):
            if not 0<abs((dates[1].date()-dates[0].date()).days)<=31:raise QualityError('서로 다른 UTC 촬영일, 31일 이내만 보충 가능합니다.')
        elif dates[0].date()>=dates[1].date():raise QualityError('서로 다른 UTC 촬영일의 이전→이후 순서가 필요합니다.')
        if a['platform']!=b['platform'] or a['processing_level']!=b['processing_level'] or a['processing_baseline']!=b['processing_baseline']:raise QualityError('동일 플랫폼·제품 처리 수준·S2 기준선이 필요합니다.')
        if method not in ('thermal_gapfill','thermal_ml') and query.reference_date and not dates[0].date()<query.reference_date<=dates[1].date():raise QualityError('사건/기준일 전후 조건과 선택 날짜가 다릅니다.')
    large=grid['aoi'].area>50e6 or grid['width']*grid['height']>150000
    if large:
        payload.update(bounded_tiling=True,execution_seconds=255,transfer_budget_bytes=256*1024**2)
    return payload,{'tile_count':processing_grid(payload)[1] if large else 1,'width':grid['width'],'height':grid['height'],'resolution_m':profile['resolution_m'],
                    'aoi_area_m2':grid['aoi'].area,'maximum_aoi_km2':25 if method=='thermal_ml' else 200 if method in SINGLE_METHODS else 50,
                    'maximum_pixels':100000 if method=='thermal_ml' else 600000 if method in SINGLE_METHODS else 150000,
                    'maximum_transfer_bytes':256*1024**2 if large else 64*1024**2,'maximum_seconds':255 if large else 75,
                    'tile_failure_policy':'abort entire job; no partial success; no AOI reduction','maximum_output_bytes':artifact_store.ZIP_LIMIT}

def read_scene(scene,g,opener):
    """QA first, native masks before continuous reprojection, exactly one scale."""
    profile=scene['profile'];s2=profile['profile_id']=='es_s2';keys=profile['required_keys'];headers=[];native={}
    for key in keys:
        a=scene['assets'][key];dn,mask,t,crs,header=read_native(a['path'],a,g,opener,profile=profile)
        native[key]=(dn,mask,t,crs);headers.append({'key':key,**header,'applied_scale':a['scale'],'applied_offset':a['offset']})
    qa_key='scl' if s2 else 'qa_pixel';q,qmask,qt,qcrs=native[qa_key]
    if s2:good=qmask&np.isin(q,[4,5,6]);samples=qmask&(q!=0)
    else:
        r,rm,rt,rc=native['qa_radsat'];r=warp(r,rt,rc,q.shape,qt,qcrs,Resampling.nearest)
        good=qmask&pixel_quality(q,r);samples=qmask&((q&1)==0)
    dest_shape=(g['height'],g['width']);valid=np.ones(dest_shape,dtype=bool);observed=np.ones(dest_shape,dtype=bool);bands={}
    for variable,key in profile['bands'].items():
        if key not in keys or key in profile['qa']:continue
        dn,mask,t,crs=native[key];a=scene['assets'][key]
        qgood=warp(good.astype('uint8'),qt,qcrs,dn.shape,t,crs,Resampling.nearest)>0
        qsamples=warp(samples.astype('uint8'),qt,qcrs,dn.shape,t,crs,Resampling.nearest)>0
        raw_valid=mask&np.isfinite(dn)&(dn!=a['nodata'] if a['nodata'] is not None else True)
        if variable=='thermal':raw_valid&=dn>=293
        native_good=raw_valid&qgood
        numeric=kelvin_celsius(dn)[0] if variable=='thermal' else dn.astype('float64')*a['scale']+a['offset']
        numeric[~native_good]=np.nan
        bands[variable]=warp(numeric,t,crs,dest_shape,g['transform'],g['crs'],Resampling.average,np.nan)
        valid&=warp(native_good.astype('float32'),t,crs,dest_shape,g['transform'],g['crs'],Resampling.average)>=.999
        observed&=warp((raw_valid&qsamples).astype('float32'),t,crs,dest_shape,g['transform'],g['crs'],Resampling.average)>=.999
    for key in ('qa','cdist'):
        if key not in native:continue
        dn,mask,t,crs=native[key];a=scene['assets'][key]
        values=dn.astype('float64')*a['scale']+a['offset'];values[~mask]=np.nan
        # Conservative ancillary aggregation: max uncertainty, min cloud distance.
        bands[key]=warp(values,t,crs,dest_shape,g['transform'],g['crs'],Resampling.max if key=='qa' else Resampling.min,np.nan)
        valid&=warp(mask.astype('float32'),t,crs,dest_shape,g['transform'],g['crs'],Resampling.average)>=.999
    qdest=warp(q,qt,qcrs,dest_shape,g['transform'],g['crs'],Resampling.nearest)
    return bands,valid,observed,headers,qdest

def display(values,mask,g,scenes,label,unit='1'):
    rgba=np.zeros((*mask.shape,4),dtype='uint8')
    legend=None
    if np.any(mask):
        lo,hi=np.percentile(values[mask],[2,98]);fraction=np.clip((values-lo)/max(hi-lo,1e-6),0,1)
        top_fraction=float(np.clip((hi-lo)/max(hi-lo,1e-6),0,1))
        high_color='#{:02x}{:02x}{:02x}'.format(int(top_fraction*230),int((1-top_fraction)*150+40),int((1-top_fraction)*200))
        legend={'minimum':float(lo),'maximum':float(hi),'unit':unit,'percentiles':[2,98],
                'scope':'per_layer_valid_pixels','low_color':'#00bec8','high_color':high_color}
        fraction=np.nan_to_num(fraction)
        rgba[:,:,0]=(fraction*230).astype('uint8');rgba[:,:,1]=((1-fraction)*150+40).astype('uint8');rgba[:,:,2]=((1-fraction)*200).astype('uint8');rgba[:,:,3]=np.where(mask,170,0)
    result=map_preview(rgba,g,label,[s['id'] for s in scenes])
    result['legend']=legend
    return result


def read_tiled_scene(scene,g,opener):
    """One output grid, nonoverlapping cores, one-cell read halo.

    Only existing single-date kernels use this path. A failed core aborts the
    job; neither missing pixels nor a provider failure become valid zeroes.
    """
    height,width=g['height'],g['width'];bands={};headers=[]
    valid=np.zeros((height,width),dtype=bool);observed=valid.copy();qa=None;tiles=[]
    footprint=project_footprint(scene['geometry'],g)
    for top in range(0,height,TILE_EDGE):
        for left in range(0,width,TILE_EDGE):
            h=min(TILE_EDGE,height-top);w=min(TILE_EDGE,width-left)
            y=max(0,top-1);x=max(0,left-1);bottom=min(height,top+h+1);right=min(width,left+w+1)
            tile={**g,'height':bottom-y,'width':right-x,'transform':g['transform']*Affine.translation(x,y)}
            t=g['transform']*Affine.translation(left,top)
            if not footprint.intersects(box(t.c,t.f-h*abs(t.e),t.c+w*t.a,t.f)):
                tiles.append({'row':top,'column':left,'height':h,'width':w,'state':'unobserved_or_outside_roi','observed_cells':0,'valid_cells':0})
                continue
            budget=opener.tile_window() if hasattr(opener,'tile_window') else nullcontext()
            try:
                with budget:b,v,o,hs,q=read_scene(scene,tile,opener)
            except QualityError:
                raise QualityError(f'타일 ({top},{left}) 원본/QA 읽기 실패. 전체 작업을 보류하며 부분 결과를 성공으로 게시하지 않습니다.') from None
            core=np.s_[top:top+h,left:left+w];inner=np.s_[top-y:top-y+h,left-x:left-x+w]
            for key,values in b.items():
                if key not in bands:bands[key]=np.full((height,width),np.nan,dtype=values.dtype)
                bands[key][core]=values[inner]
            valid[core]=v[inner];observed[core]=o[inner]
            if qa is None:qa=np.zeros((height,width),dtype=q.dtype)
            qa[core]=q[inner]
            if not headers:headers=hs
            tiles.append({'row':top,'column':left,'height':h,'width':w,'state':'read','observed_cells':int(o[inner].sum()),'valid_cells':int(v[inner].sum())})
    if qa is None:raise QualityError('확정 AOI에서 실제 관측 타일이 없습니다. 품질·수치는 미확인입니다.')
    return bands,valid,observed,headers,qa,tiles

def execute(payload,identifier,opener=None):
    from .analysis_catalog import METHODS
    method=payload['method_id'];input=payload['processing_input'];g,_=processing_grid(payload);weights=area_weights(g['aoi'],g);inside=weights>0
    raw=[];valids=[];observations=[];records=[];files={};options=input.get('qa_options',{})
    tile_records=[];cloud_masks=[]
    for s in payload['scenes']:
        if payload.get('bounded_tiling'):
            bands,valid,observed,headers,qa,tiles=read_tiled_scene(s,g,opener);tile_records.extend(tiles)
        else:bands,valid,observed,headers,qa=read_scene(s,g,opener)
        foot=area_weights(project_footprint(s['geometry'],g),g)>0
        cloud_masks.append(inside&foot&((qa&30)!=0)&((qa&33)==0))
        observed&=inside&foot;valid&=observed
        excluded={'band_nodata_or_unobserved':float(weights[inside&~observed].sum())}
        if s['profile']['profile_id']=='es_s2':
            for name,codes in [('cloud_cirrus',[8,9,10]),('cloud_shadow',[3]),('snow',[11]),('saturated',[1]),('dark_or_unclassified',[2,7])]:excluded[name]=float(weights[inside&np.isin(qa,codes)].sum())
        else:
            for name,bits in [('cloud_dilated_cirrus',[1,2,3]),('cloud_shadow',[4]),('snow',[5]),('fill',[0])]:
                flagged=np.zeros(qa.shape,dtype=bool)
                for bit in bits:flagged|=(qa&(1<<bit))!=0
                excluded[name]=float(weights[inside&flagged].sum())
        excluded['base_qa_or_required_data']=float(weights[observed&~valid].sum())
        if method in THERMAL:
            quality=thermal_valid(bands['qa'],bands['cdist'],options)
            if method in ('thermal_gapfill','thermal_ml'):
                # Include actual observations rejected by the explicit cloud
                # proximity policy, but not unrelated ST NoData/uncertainty.
                cloud_masks[-1]|=observed&((qa&33)==0)&np.isfinite(bands['cdist'])&(bands['cdist']>=0)&(bands['cdist']<options['minimum_cloud_distance_km'])
            excluded['st_uncertainty']=float(weights[valid&(~np.isfinite(bands['qa'])|(bands['qa']<0)|(bands['qa']>options['maximum_uncertainty_k']))].sum())
            excluded['cloud_distance']=float(weights[valid&(~np.isfinite(bands['cdist'])|(bands['cdist']<options['minimum_cloud_distance_km']))].sum())
            excluded['uncertainty_or_cloud_proximity']=float(weights[valid&~quality].sum());valid&=quality
            values=bands['thermal'];valid&=np.isfinite(values)&(values>0)
        else:values,valid=index(method,bands,valid)
        excluded['qa_nodata_numeric']=float(weights[inside&~valid].sum())
        records.append({'id':s['id'],'collection':s['collection'],'provider_id':s['provider_id'],'datetime':s['datetime'],'status':'checked','error':None,
            'valid_area_m2':float(weights[valid].sum()),'valid_in_common_area_m2':None,'valid_percent_aoi':float(weights[valid].sum()/weights.sum()*100),
            'exclusions_m2':excluded,'headers':headers,'radiometry':[{'key':key,'status':'confirmed_documented_metadata','scale':a['scale'],'offset':a['offset'],'source':a['calibration_source']} for key,a in s['assets'].items()]})
        raw.append((values,bands));valids.append(valid);observations.append(observed)
    if method in ('thermal_gapfill','thermal_ml'):
        from .thermal_gapfill import publish
        return publish(payload,identifier,opener,g,weights,raw,valids,observations,cloud_masks,records,tile_records)
    valid=np.logical_and.reduce(valids);observed=np.logical_and.reduce(observations)
    if not np.any(valid):
        from .processing_failure import ProcessingBlocked
        # Only reached after every required scene/tile has actually been read.
        # Keep failed analysis metrics null; checked QA evidence is separate.
        raise ProcessingBlocked('AOI의 ST/필수 밴드가 미관측·NoData입니다. 분석 평균은 미확인입니다.' if not np.any(observed) else '관측은 있으나 QA/수치 조건을 통과한 공통 유효 픽셀이 없습니다. 분석 파일/평균을 0으로 만들지 않습니다.', {
            'code':'no_valid_pixels' if np.any(observed) else 'no_observations',
            'qa':{'status':'checked_no_valid','aoi_area_m2':float(weights.sum()),
                  'observed_area_m2':float(weights[observed].sum()),'valid_area_m2':0.,
                  'qa_policy_version':QA_VERSION,'qa_options':options,
                  'scenes':[{key:r[key] for key in ('id','datetime','valid_area_m2','exclusions_m2')} for r in records]}})
    def tiff(name,values,names,unit='1',mask=valid):
        arr=np.asarray(values);arr=arr if arr.ndim==3 else arr[None]
        files[name]=artifact_store.tiff_bytes(np.where(mask,arr,-9999).astype('float32'),g,-9999,names,unit)
    def summary(values,mask):
        denominator=float(weights[mask].sum())
        return {'valid_area_m2':denominator,'mean':float(np.sum(values[mask]*weights[mask])/denominator) if denominator else None,
            'minimum':float(values[mask].min()) if denominator else None,'maximum':float(values[mask].max()) if denominator else None}
    stats={};threshold=input.get('threshold');sensitivity=None
    if method in THERMAL:
        kelvin=raw[0][0];celsius=kelvin-273.15;bands=raw[0][1]
        tiff('temperature.tif',[kelvin,celsius],['surface_temperature_kelvin','surface_temperature_celsius'],['K','degC'])
        tiff('temperature_quality.tif',[bands['qa'],bands['cdist']],['ST_uncertainty','distance_to_cloud'],['K','km'],mask=observed&np.isfinite(bands['qa'])&np.isfinite(bands['cdist']))
        stats={'kelvin':summary(kelvin,valid),'celsius':summary(celsius,valid)}
        if method=='hotspots':
            hot=np.where(valid,np.where(celsius>threshold,2,1),0).astype('uint8');files['hotspots.tif']=artifact_store.tiff_bytes(hot,g,0,['0_invalid_1_not_above_2_above_user_threshold'])
            stats['hot_area_m2']=float(weights[valid&(celsius>threshold)].sum())
        if method=='temperature_comparison':
            project=Transformer.from_crs(4326,g['crs'],always_xy=True).transform;stats['regions']=[]
            for label,r in zip(input['comparison_labels'],input['comparison_regions']):
                geom=shape(r['geometry']) if r['mode']=='polygon' else box(*r['bbox'])
                projected=shapely.transform(geom.segmentize(.001),project,interleaved=False);regional=area_weights(projected.intersection(g['aoi']),g)
                w=regional*valid;area=float(w.sum())
                if area<=0:raise QualityError('비교 영역에 유효 온도 픽셀이 없습니다. 영역 평균은 미확인입니다.')
                stats['regions'].append({'label':label,'confirmed_area_m2':float(regional.sum()),'valid_area_m2':area,'valid_percent':area/float(regional.sum())*100,'mean_celsius':float(np.sum(celsius[valid]*w[valid])/area)})
            stats['mean_difference_celsius_first_minus_second']=stats['regions'][0]['mean_celsius']-stats['regions'][1]['mean_celsius']
        preview=celsius;label='실제 지표면 온도 (섭씨) · 기온 아님 · 원열관측 100m / 제품 격자 30m'
    else:
        values=[r[0] for r in raw];preview=values[-1];label='실제 '+method.upper()+' · 지수/수역 후보이며 확정 분류 아님'
        if len(values)==2:
            difference=values[1]-values[0];tiff('mndwi_change.tif',[*values,difference],['MNDWI_before','MNDWI_after','MNDWI_after_minus_before']);preview=difference
            before=values[0]>threshold;after=values[1]>threshold
            codes=np.where(valid,1+before.astype('uint8')+2*after.astype('uint8'),0).astype('uint8')
            # 1 nonwater,2 loss,3 gain,4 persistent candidate; all on common validity.
            files['water_change.tif']=artifact_store.tiff_bytes(codes,g,0,['0_invalid_1_nonwater_2_loss_3_gain_4_persistent_water_candidate'])
            stats.update(before=summary(values[0],valid),after=summary(values[1],valid),difference=summary(difference,valid),candidate_gain_area_m2=float(weights[codes==3].sum()),candidate_loss_area_m2=float(weights[codes==2].sum()))
        else:
            tiff(method+'.tif',preview,[method.upper()]);stats=summary(preview,valid)
            if method=='mndwi':files['water_candidates.tif']=artifact_store.tiff_bytes(np.where(valid,np.where(preview>threshold,2,1),0).astype('uint8'),g,0,['0_invalid_1_other_2_water_candidate'])
        if method.startswith('mndwi'):
            sensitivity=[{'threshold':float(t),'candidate_area_m2_by_date':[float(weights[valid&(v>t)].sum()) for v in values]} for t in [max(-1,threshold-.05),threshold,min(1,threshold+.05)]]
    files['valid_mask.tif']=artifact_store.tiff_bytes(valid.astype('uint8'),g,0,['1_valid_0_invalid'])
    exclusion=np.where(inside,np.where(~observed,1,np.where(valid,3,2)),0).astype('uint8')
    files['exclusion_mask.tif']=artifact_store.tiff_bytes(exclusion,g,0,['0_outside_1_unobserved_2_qa_nodata_numeric_3_valid'])
    total=float(weights.sum());valid_area=float(weights[valid].sum());observed_area=float(weights[observed].sum())
    quality_maps=[]
    for scene,mask,record in zip(payload['scenes'],valids,records):
        rgba=np.zeros((*mask.shape,4),dtype='uint8');rgba[inside&~mask]=[238,126,54,145];rgba[inside&mask]=[13,160,113,110]
        quality_maps.append(map_preview(rgba,g,'실제 제품 QA/NoData/수치 유효·제외 마스크 · 구름 복원 아님',[scene['id']]))
        record['valid_in_common_area_m2']=float(weights[mask&observed].sum())
    report={'status':'checked','analysis_completed':True,'analysis_label':METHODS[method]['label'],'version':VERSION,'checked_at':datetime.now(timezone.utc).isoformat(),
        'scenes':records,'grid':grid_info(g),'aoi_area_m2':total,'common_observed_area_m2':observed_area,'common_valid_area_m2':valid_area,
        'common_valid_percent_aoi':valid_area/total*100,'common_valid_percent_observed':valid_area/observed_area*100 if observed_area else None,
        'unobserved_area_m2':float(weights[inside&~observed].sum()),'quality_or_numeric_excluded_area_m2':float(weights[observed&~valid].sum()),'common_excluded_area_m2':observed_area-valid_area,
        'statistics':stats,'threshold':threshold,'threshold_basis':input.get('threshold_basis'),'threshold_sensitivity':sensitivity,
        'output_summary':{'sources':[{'id':s['id'],'collection':s['collection'],'datetime':s['datetime']} for s in payload['scenes']],
            'crs':g['crs'],'resolution_m':abs(g['transform'].a),'width':g['width'],'height':g['height'],
            'units':['K','degC'] if method in THERMAL else ['1'],
            'formula':FORMULAS.get(method,'Kelvin=raw_ST_DN*0.00341802+149; Celsius=Kelvin-273.15'),
            'qa_policy_version':QA_VERSION,'statistics_scope':input['roi']['mode']+'; confirmed user AOI, not a gazetteer administrative boundary'},
        'tiling':{'enabled':bool(payload.get('bounded_tiling')),'one_global_grid':True,'core_overlap_cells':0,'read_halo_cells':1,'tiles':tile_records,'failure_policy':'whole_job_failed_no_partial_artifact'},
        'qa_policy':{'version':QA_VERSION,'s2_accepted_scl':[4,5,6],'landsat_excluded_bits':[0,1,2,3,4,5],'landsat_confidence':'medium/high excluded; any RADSAT excluded',
            'thermal_options':options,'note':'운영 QA 기준이며 보편적 과학 적합성 판정이 아닙니다. 세부 제외 사유는 겹칠 수 있어 합산하지 않습니다. 마스킹은 구름 아래 값을 복원하지 않습니다.'},
        'conclusion':'실제 관측 기반 지수/지표면 온도입니다. 침수/토지피복 확정·기온·구름 복원 결과가 아닙니다.',
        'map_layers':{'quality':quality_maps,'analysis':display(preview,valid,g,payload['scenes'],label,'degC' if method in THERMAL else '1')},
        'transfer':{'bytes':getattr(opener,'bytes',0),'requests':getattr(opener,'requests',0),'files':getattr(opener,'info',{})}}
    manifest={'version':VERSION,'input':input,'roi_fingerprint':payload['roi_fingerprint'],'grid':grid_info(g),'sources':payload['scenes'],
        'product_sources':SOURCES,'source_versions':SOURCE_VERSIONS,'checked_on':CHECKED_ON,'qa_policy_version':QA_VERSION,
        'formula':FORMULAS.get(method,'Kelvin=raw_ST_DN*0.00341802+149; Celsius=Kelvin-273.15; exactly once, no additional atmospheric correction'),
        'resampling':{'continuous':'average after native QA/NoData removal; valid fraction >=0.999','categorical':'nearest','ST_uncertainty':'max','cloud_distance':'min'},
        'mask_encoding':{'0':'outside ROI','1':'unobserved','2':'QA/NoData/numerically excluded','3':'valid'},'record':report}
    return {'status':'succeeded','result':artifact_store.safe_value(report,include_maps=True),
            'artifact':artifact_store.publish(identifier,files,manifest,METHODS[method]['artifacts'],METHODS[method]['artifact_specs'])}

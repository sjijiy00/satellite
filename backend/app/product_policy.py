"""Reviewed product matrix. No generated bands, calibration or provider grants."""
import math
from .pixel_policy import QualityError
from .change_analysis import calibration_for_change

VERSION='products-2026-11-03.1'
QA_VERSION='product-qa-2026-11-03.1'
CHECKED_ON='2026-11-03'
SOURCE_VERSIONS={'landsat_guide':'LSDS-1619 v6.0, May 2024','s2':'L2A; processing baseline/offset flag revalidated per canonical Item','formulas':'NASA portal definitions checked 2026-11-03'}
SOURCES={
 's2':'https://sentiwiki.copernicus.eu/web/s2-products',
 's2_bands':'https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S2L2A.html',
 'landsat_scale':'https://www.usgs.gov/faqs/how-do-i-use-a-scale-factor-landsat-level-2-science-products',
 'landsat_qa':'https://www.usgs.gov/landsat-missions/landsat-collection-2-quality-assessment-bands',
 'landsat_st':'https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature',
 'landsat_guide':'https://d9-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/s3fs-public/media/files/LSDS-1619_Landsat8-9-Collection2-Level2-Science-Product-Guide-v6.pdf',
 'ndvi':'https://science.data.nasa.gov/disasters/data-gallery/landsat-ndvi',
 'mndwi':'https://science.data.nasa.gov/disasters/data-gallery/landsat-mndwi',
 'ndbi':'https://gis.earthdata.nasa.gov/portal/rest/services/nasa_lp_daac/HLSL30_v2_Service/ImageServer/rasterFunctionInfos',
}
PROFILES={
 'es_s2':dict(provider_id='earth-search',collection='sentinel-2-l2a',levels=['S2MSI2A','L2A'],platforms=['sentinel-2a','sentinel-2b','sentinel-2c'],
    bands={'red':'red','nir':'nir','green':'green','swir16':'swir16'},qa=['scl'],resolution_m=20,native_resolution='MSI red/NIR/green 10 m; SWIR1/SCL 20 m',product='Sentinel-2 L2A',sources=['s2','s2_bands']),
 'pc_landsat':dict(provider_id='planetary-computer',collection='pc-landsat-c2-l2',levels=['L2SR','L2SP'],platforms=['landsat-8','landsat-9'],
    bands={'red':'red','nir':'nir08','green':'green','swir16':'swir16','thermal':'lwir11'},qa=['qa_pixel','qa_radsat'],resolution_m=30,
    native_resolution='OLI/OLI-2 30 m; TIRS/TIRS-2 thermal observation 100 m; ST output 30 m',product='Landsat 8/9 Collection 2 Level 2',sources=['landsat_scale','landsat_qa','landsat_st','landsat_guide']),
}
VARIABLES={'ndvi':['red','nir'],'mndwi':['green','swir16'],'mndwi_change':['green','swir16'],'ndbi':['swir16','nir'],
 'surface_temperature':['thermal'],'hotspots':['thermal'],'temperature_comparison':['thermal']}
VARIABLES['thermal_gapfill']=['thermal']
VARIABLES['thermal_ml']=['thermal']
THERMAL={'surface_temperature','hotspots','temperature_comparison','thermal_gapfill','thermal_ml'}
PRODUCT_METHODS=set(VARIABLES)

def products(method):
    names=['pc_landsat'] if method in THERMAL else ['es_s2','pc_landsat']
    return [{**PROFILES[n],'levels':['L2SP'] if method in THERMAL else PROFILES[n]['levels'],'profile_id':n,'required_keys':[PROFILES[n]['bands'][v] for v in VARIABLES[method]]+PROFILES[n]['qa']+(['qa','cdist'] if method in THERMAL else []),
             'checked_on':CHECKED_ON,'policy_version':VERSION} for n in names]

def profile_for(reference,method):
    p=next((p for p in products(method) if p['provider_id']==reference['provider_id'] and p['collection']==reference['collection']),None)
    if not p:raise QualityError('검증된 목적·제공처·제품 allowlist에 없습니다. HLS/VIIRS/SAR/PC S2 픽셀 처리는 미지원입니다.')
    return p

def asset_policy(key,profile,raw_asset,properties):
    """Only documented calibration; disagreement/missing metadata fails closed."""
    records=raw_asset.get('raster:bands') or []
    if len(records)!=1:raise QualityError(key+': 단일 밴드 NoData/보정 메타데이터가 없습니다.')
    record=records[0];nodata=record.get('nodata')
    if profile['profile_id']=='es_s2':
        expected_dtype='uint8' if key=='scl' else 'uint16';res=20 if key in ('scl','swir16') else 10
        if nodata!=0:raise QualityError('S2 NoData=0 메타데이터가 필요합니다.')
        if key!='scl' and not calibration_for_change(record,{'processing_baseline':properties.get('s2:processing_baseline'),'boa_offset_applied':properties.get('earthsearch:boa_offset_applied')}):
            raise QualityError('S2 기준선/이미 적용된 offset/scale이 상충하거나 미확인입니다.')
        scale,offset=(1.,0.) if key=='scl' else (record['scale'],record['offset'])
    else:
        expected_dtype='int16' if key in ('qa','cdist') else 'uint16';res=30
        expected_nodata={'qa_pixel':1,'qa_radsat':None,'qa':-9999,'cdist':-9999}.get(key,0)
        if nodata!=expected_nodata:raise QualityError(key+': 공식 NoData 메타데이터 불일치')
        if key in ('qa_pixel','qa_radsat'):scale,offset=1.,0.
        else:
            scale,offset=(.00341802,149.) if key=='lwir11' else (.01,0.) if key in ('qa','cdist') else (.0000275,-.2)
            if not math.isclose(record.get('scale',math.nan),scale,abs_tol=1e-10,rel_tol=0) or not math.isclose(record.get('offset',0),offset,abs_tol=1e-10,rel_tol=0):
                raise QualityError(key+': USGS scale/offset 누락 또는 상충. 보정을 추정하지 않습니다.')
    if record.get('data_type')!=expected_dtype:raise QualityError(key+': 문서화된 자료형과 STAC 밴드 자료형이 다릅니다.')
    return {'nodata':nodata,'dtype':expected_dtype,'resolutions':[res],'scale':scale,'offset':offset,
            'zero_valid':key=='qa_radsat','bitmask_fill':1 if key=='qa_pixel' else None,
            'calibration_source':SOURCES['s2'] if profile['profile_id']=='es_s2' else SOURCES['landsat_qa'] if key in ('qa_pixel','qa_radsat') else SOURCES['landsat_scale']}

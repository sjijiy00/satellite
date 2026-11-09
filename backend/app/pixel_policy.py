"""Versioned A3 operational policy, not a universal scientific suitability rule."""
VERSION='s2-l2a-qa-2026-10-29.1'
LIMITS={'aoi_km2':25,'grid_pixels':100_000,'source_window_pixels':1_000_000,
        'file_bytes':2_000_000_000,'transfer_bytes':64*1024*1024,'range_requests':128,
        'worker_seconds':60,'request_seconds':8,'concurrent_jobs':1,'resolution_m':20}
SCL_LABELS={0:'NoData',1:'포화·결함',2:'지형 그림자/어두운 영역',3:'구름 그림자',4:'식생',5:'비식생',
            6:'수역',7:'분류불명',8:'중간 확률 구름',9:'높은 확률 구름',10:'권운',11:'눈·얼음'}
POLICY={'version':VERSION,'accepted_scl':[4,5,6],
        'excluded_scl':{str(k):v for k,v in SCL_LABELS.items() if k not in (4,5,6)},
        'note':'식생·수역·도시 목적 모두 구름/그림자/NoData/눈/분류불명을 보수적으로 제외합니다. 식생·비식생·물은 유효 관측 분류이며 목적 대상의 확정 분류가 아닙니다. 눈 분석에는 이 정책을 사용하지 않습니다.',
        'scl_resampling':'nearest; 범주를 보존하며 20 m SCL을 세밀한 관측으로 바꾸지 않습니다.',
        'reflectance_resampling':'average; 원본 NoData와 SCL 제외 픽셀을 먼저 마스킹합니다. 기여 원본의 유효 비율 0.999 이상인 출력 셀만 채택합니다. 10 m를 공통 20 m로 집계하며 업샘플링을 해상도 향상으로 해석하지 않습니다.',
        'area_method':'AOI 중심 LAEA 등적 격자 셀과 AOI/footprint 교집합 면적을 가중치로 사용. 경계 셀은 부분 면적; 분류 경계는 20 m 격자 근사.',
        'sources':[
            'https://sentiwiki.copernicus.eu/web/s2-products',
            'https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S2L2A.html',
            'https://custom-scripts.sentinel-hub.com/custom-scripts/sentinel-2/scene-classification/',
            'https://github.com/Element84/earth-search/issues/71'],
        'checked_on':'2026-10-29'}


class QualityError(Exception):
    pass

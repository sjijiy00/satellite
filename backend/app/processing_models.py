"""Explicit processing inputs; browser acquisition receipts are never evidence."""
from datetime import date
import hashlib
import json
from typing import Literal,Annotated
from pydantic import BaseModel,ConfigDict,Field,model_validator
from shapely.geometry import shape
from .models import SearchRequest,SearchItemReference
from .analysis_catalog import BY_ID,METHODS,QA_VERSION
from .admin_boundaries import REGISTRY,load_boundary
from .product_policy import PRODUCT_METHODS,QA_VERSION as PRODUCT_QA,profile_for,THERMAL

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)

class ROI(Strict):
    confirmed:Literal[True]
    mode:Literal['bbox','polygon']
    bbox:tuple[float,float,float,float]
    source:Literal['manual_bbox','manual_polygon','registered_boundary']
    boundary_id:str|None=Field(default=None,max_length=80)
    geometry:dict|None=None
    boundary_metadata:dict|None=None

    @model_validator(mode='after')
    def validate_roi(self):
        SearchRequest(bbox=self.bbox,start_date=date(2025,1,1),end_date=date(2025,1,1))
        if self.mode=='bbox':
            if self.source!='manual_bbox' or self.geometry or self.boundary_id or self.boundary_metadata:
                raise ValueError('bbox 범위와 확정 행정경계 polygon은 별개입니다.')
        else:
            if self.source=='registered_boundary':
                name=next((name for name,v in REGISTRY.items() if v['stem']==self.boundary_id),None)
                if not name:raise ValueError('등록된 경계 ID가 아닙니다.')
                metadata,feature,g=load_boundary(name)
                self.geometry=feature['geometry']
                self.boundary_metadata={k:metadata.get(k) for k in ('name','code','year','source','source_url','terms','crs','original_crs','geojson_sha256')}
            elif self.source=='manual_polygon' and self.geometry:
                if self.boundary_metadata is not None:raise ValueError('수동 polygon을 공식 경계로 표시하지 않습니다.')
                if len(json.dumps(self.geometry))>300000:raise ValueError('폴리곤 크기 상한입니다.')
                try:g=shape(self.geometry)
                except Exception:raise ValueError('GeoJSON Polygon 형식을 확인하세요.') from None
            else:raise ValueError('폴리곤의 명시 출처가 필요합니다.')
            if not g.is_valid or g.is_empty or g.has_z or g.geom_type not in ('Polygon','MultiPolygon'):
                raise ValueError('유효한 Polygon/MultiPolygon이 필요합니다.')
            if not all(abs(a-b)<1e-7 for a,b in zip(g.bounds,self.bbox)):
                raise ValueError('확정 polygon 외접 범위와 bbox가 다릅니다.')
        return self

    def fingerprint(self):
        return hashlib.sha256(json.dumps(self.model_dump(),sort_keys=True,separators=(',',':')).encode()).hexdigest()

class SceneInput(SearchItemReference):
    model_config=ConfigDict(extra='forbid')
    asset_keys:list[Annotated[str,Field(min_length=1,max_length=80,pattern=r'^[A-Za-z0-9_.-]+$')]]=Field(min_length=1,max_length=8)

class ProcessingRequest(Strict):
    purpose_type:Literal['vegetation','flood','urban','thermal']
    analysis_id:str=Field(max_length=80)
    method_id:str=Field(max_length=80)
    roi:ROI
    start_date:date
    end_date:date
    scenes:list[SceneInput]=Field(min_length=1,max_length=4)
    reference_date:date|None=None
    comparison_regions:list[ROI]=Field(default_factory=list,max_length=2)
    threshold:float|None=None
    threshold_basis:str|None=Field(default=None,min_length=1,max_length=300)
    qa_options:dict[str,float]=Field(default_factory=dict)
    comparison_labels:tuple[str,str]|None=None
    qa_policy_version:str=Field(max_length=80)

    @model_validator(mode='after')
    def coherent(self):
        SearchRequest(bbox=self.roi.bbox,start_date=self.start_date,end_date=self.end_date)
        if self.analysis_id not in BY_ID or BY_ID[self.analysis_id]['domain']!=self.purpose_type:
            raise ValueError('목적과 세부 분석이 일치하지 않습니다.')
        from .analysis_catalog import execution
        if self.method_id not in execution(BY_ID[self.analysis_id])['method_ids']:
            raise ValueError('선택 분석의 실제 실행 엔진이 없습니다.')
        m=METHODS[self.method_id]
        if self.roi.mode=='polygon' and not m['spatial']['polygon']:
            raise ValueError('이 기존 엔진의 polygon 클리핑은 미검증입니다. bbox 처리와 혼동하지 않습니다.')
        if self.qa_policy_version!=(PRODUCT_QA if self.method_id in PRODUCT_METHODS else QA_VERSION):raise ValueError('지원 QA 정책 버전을 명시하세요.')
        if not m['minimum_scenes']<=len(self.scenes)<=m['maximum_scenes']:
            raise ValueError('이 처리의 입력 장면 개수 조건을 확인하세요.')
        if len({(s.provider_id,s.collection,s.id) for s in self.scenes})!=len(self.scenes):
            raise ValueError('서로 다른 canonical Item이 필요합니다.')
        if any(s.provider_id not in m['providers'] or s.collection not in m['collections'] for s in self.scenes):
            raise ValueError(m['unsupported_reason'])
        if (self.end_date-self.start_date).days>m['temporal']['maximum_days']:
            raise ValueError('이 처리의 허용 기간 상한을 초과했습니다.')
        if self.reference_date and not self.start_date<=self.reference_date<=self.end_date:
            raise ValueError('기준일은 허용 기간 안이어야 합니다.')
        if self.method_id in PRODUCT_METHODS:
            try:
                for s in self.scenes:profile_for(s.model_dump(),self.method_id)
            except Exception as e:
                from .pixel_policy import QualityError
                if isinstance(e,QualityError):raise ValueError(str(e)) from None
                raise
            if len({(s.provider_id,s.collection) for s in self.scenes})!=1:raise ValueError('동일 제공처·제품의 시점만 비교합니다.')
            needs=self.method_id in ('mndwi','mndwi_change','hotspots')
            if needs and (self.threshold is None or not self.threshold_basis):raise ValueError('임계값과 사용자가 확인한 근거가 필요합니다. 보편적 임계값을 생성하지 않습니다.')
            if self.threshold is not None and (not needs or not (-100<=self.threshold<=100 if self.method_id=='hotspots' else -1<=self.threshold<=1)):raise ValueError('분석별 임계값/단위를 확인하세요.')
            if self.threshold_basis and not needs:raise ValueError('이 분석은 임계값을 사용하지 않습니다.')
            if self.method_id in THERMAL:
                options={'maximum_uncertainty_k':2.,'minimum_cloud_distance_km':1.,**self.qa_options}
                if set(options)!={'maximum_uncertainty_k','minimum_cloud_distance_km'} or not .1<=options['maximum_uncertainty_k']<=20 or not 0<=options['minimum_cloud_distance_km']<=10:raise ValueError('명시한 ST 품질 정책 범위를 확인하세요.')
                self.qa_options=options
            elif self.qa_options:raise ValueError('다른 제품의 QA 정책을 섞지 않습니다.')
            if self.method_id=='temperature_comparison':
                if len(self.comparison_regions)!=2 or not self.comparison_labels or any(not x.strip() or len(x)>80 for x in self.comparison_labels):raise ValueError('비교 영역 두 개와 각 영역 이름을 명시 확인하세요.')
                def geom(r):
                    from shapely.geometry import box
                    return shape(r.geometry) if r.mode=='polygon' else box(*r.bbox)
                a,b=map(geom,self.comparison_regions);roi=geom(self.roi)
                if not roi.covers(a) or not roi.covers(b) or a.intersection(b).area>1e-12:raise ValueError('서로 겹치지 않으며 처리 AOI 안에 있는 비교 영역이 필요합니다.')
            elif self.comparison_regions or self.comparison_labels:raise ValueError('이 분석은 비교 영역을 사용하지 않습니다.')
        elif self.threshold is not None or self.comparison_regions or self.threshold_basis or self.qa_options or self.comparison_labels:
            raise ValueError('현재 엔진에 없는 임계값/비교 영역을 실행 조건으로 무시하지 않습니다.')
        return self

class ProcessingStart(Strict):
    plan_id:str=Field(pattern=r'^[a-f0-9]{32}$')
    confirmation_digest:str=Field(pattern=r'^[a-f0-9]{64}$')
    idempotency_key:str=Field(pattern=r'^[A-Za-z0-9_-]{8,80}$')

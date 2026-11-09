from datetime import date, datetime
from enum import StrEnum
import math
from pydantic import BaseModel, Field, model_validator
import json
from typing import Literal
from .provider_registry import COLLECTION_REGISTRY
from .analysis_catalog import AnalysisId, BY_ID


class Purpose(StrEnum):
    vegetation = 'vegetation'
    flood = 'flood'
    urban = 'urban'
    thermal = 'thermal'


COLLECTIONS = tuple(COLLECTION_REGISTRY)


class PurposeRequest(BaseModel):
    purpose: str = Field(default='', max_length=2000)
    purpose_type: Purpose | None = None
    target_size_m: float | None = Field(default=None, gt=0, le=100000, allow_inf_nan=False)
    observation_need: Literal['unspecified', 'clear_day', 'all_weather', 'night'] = 'unspecified'
    temporal_mode: Literal['unspecified', 'single', 'change'] = 'unspecified'
    detail_intent: AnalysisId | None = None
    requested_resolution_m: float | None = Field(default=None,gt=0,le=100000,allow_inf_nan=False)

    @model_validator(mode='after')
    def consistent_detail(self):
        if self.detail_intent and self.purpose_type and BY_ID[self.detail_intent]['domain']!=self.purpose_type:
            raise ValueError('큰 분석 분야와 세부 의도가 다릅니다. 적용할 분야/의도를 확인하세요.')
        return self


class SearchRequest(PurposeRequest):
    max_scene_cloud_cover: float | None = Field(default=None,ge=0,le=100,allow_inf_nan=False)
    requested_reference_date: date | None = None
    analysis_target: str | None = Field(default=None,max_length=120)
    recommendation_id: Literal['s2_msi','landsat_oli','landsat_tirs','s1_csar','viirs_sr','pc_s2_msi','pc_landsat_oli','pc_landsat_tirs','noaa_viirs_ndvi','hls_l30','hls_s30'] | None = None
    bbox: tuple[float, float, float, float]
    start_date: date
    end_date: date
    collections: list[str] | None = None
    max_items: int = Field(default=50, ge=1, le=100)

    @model_validator(mode='after')
    def validate_search(self):
        """Bound the query; antimeridian-crossing AOIs are intentionally unsupported."""
        w, s, e, n = self.bbox
        if not all(math.isfinite(v) for v in self.bbox):
            raise ValueError('좌표는 유한한 숫자여야 합니다.')
        if not (-180 <= w < e <= 180 and -80 <= s < n <= 80):
            raise ValueError('서경도 < 동경도, 남위도 < 북위도이어야 합니다. 위도 범위는 -80~80입니다.')
        if e - w > 5 or n - s > 5:
            raise ValueError('조회 영역은 가로·세로 각각 5도 이하여야 합니다.')
        if self.start_date > self.end_date:
            raise ValueError('시작일은 종료일보다 늦을 수 없습니다.')
        if (self.end_date - self.start_date).days > 366:
            raise ValueError('조회 기간은 최대 366일입니다.')
        if self.collections is not None and (not self.collections or any(c not in COLLECTIONS for c in self.collections)):
            raise ValueError('지원 컬렉션을 하나 이상 선택하세요.')
        return self


class SelectionRequest(BaseModel):
    bbox: tuple[float, float, float, float]
    geometry_a: dict | None = None
    geometry_b: dict | None = None

    @model_validator(mode='after')
    def validate_bounds(self):
        SearchRequest(bbox=self.bbox, start_date=date(2025, 1, 1), end_date=date(2025, 1, 1))
        if len(json.dumps([self.geometry_a, self.geometry_b])) > 300_000:
            raise ValueError('촬영 범위 데이터가 너무 큽니다.')
        return self


class ItemReference(BaseModel):
    collection: Literal['sentinel-2-l2a', 'landsat-c2-l2']
    id: str = Field(min_length=1, max_length=250, pattern=r'^[A-Za-z0-9][A-Za-z0-9_.:-]*$')


class ConditionsRequest(SearchRequest):
    purpose_type: Purpose
    scene_a: ItemReference
    scene_b: ItemReference
    reference_date: date | None = None

    @model_validator(mode='after')
    def reference_in_period(self):
        if self.reference_date and not self.start_date <= self.reference_date <= self.end_date:
            raise ValueError('기준일은 검색 기간 안에 있어야 합니다.')
        return self


class PixelQualityRequest(ConditionsRequest):
    purpose_type: Literal['vegetation','flood','urban']
    minimum_valid_percent: float = Field(default=70, ge=0, le=100, allow_inf_nan=False)

    @model_validator(mode='after')
    def s2_only(self):
        if any(ref.collection!='sentinel-2-l2a' for ref in (self.scene_a,self.scene_b)):
            raise ValueError('A3는 Sentinel-2 L2A 두 날짜만 지원합니다.')
        if self.scene_a==self.scene_b:raise ValueError('서로 다른 날짜의 두 Item을 선택하세요.')
        return self


class ChangeRequest(PixelQualityRequest):
    purpose_type: Literal['vegetation']


class SearchItemReference(BaseModel):
    # Interpretation context only. Processing endpoints retain restricted ItemReference.
    collection: Literal['sentinel-2-l2a','landsat-c2-l2','sentinel-1-grd','viirs-vnp09ga-002','pc-sentinel-2-l2a','pc-landsat-c2-l2','noaa-viirs-ndvi-cdr','hls-l30-002','hls-s30-002']
    id: str = Field(min_length=1, max_length=250, pattern=r'^[A-Za-z0-9][A-Za-z0-9_.:-]*$')
    provider_id: Literal['earth-search','copernicus','nasa-cmr','planetary-computer','noaa-nodd'] | None = None

    @model_validator(mode='after')
    def provider_matches_collection(self):
        if self.provider_id and self.provider_id != COLLECTION_REGISTRY[self.collection]['provider_id']:
            raise ValueError('제공처와 등록 컬렉션이 일치하지 않습니다.')
        return self


class InterpretRequest(PurposeRequest):
    interpretation_mode: Literal['rules','ai'] = 'ai' # legacy rules requests resolve through AI, never fallback
    resolve_conditions: bool = False
    condition_region_id: str | None = Field(default=None, max_length=80)
    followup: str = Field(default='', max_length=2000)
    bbox: tuple[float, float, float, float] | None = None
    start_date: date | None = None
    end_date: date | None = None
    selected_scene: 'SearchItemReference | None' = None
    selected_datetime: datetime | None = None
    reference_date: date | None = None
    allow_date_change: bool = False

    @model_validator(mode='after')
    def validate_context(self):
        if self.bbox is not None and self.start_date and self.end_date:
            SearchRequest(bbox=self.bbox, start_date=self.start_date, end_date=self.end_date)
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError('시작일은 종료일보다 늦을 수 없습니다.')
        return self


class CompositePlanRequest(SearchRequest):
    purpose_type: Literal['vegetation']
    temporal_mode: Literal['single'] = 'single'
    scene_refs: list[ItemReference] = Field(min_length=1, max_length=4)
    target_scene: ItemReference
    allow_date_change: bool = False

    @model_validator(mode='after')
    def validate_plan(self):
        if self.target_scene not in self.scene_refs or len(set((s.collection,s.id) for s in self.scene_refs)) != len(self.scene_refs):
            raise ValueError('기준 장면은 후보에 포함되어야 하고 중복 Item은 허용하지 않습니다.')
        if any(s.collection!='sentinel-2-l2a' for s in self.scene_refs):
            raise ValueError('첫 합성은 Sentinel-2 L2A만 지원합니다.')
        if (self.end_date-self.start_date).days>31:
            raise ValueError('합성 계획 기간은 최대 31일입니다. 기간을 좁혀 주세요.')
        return self


class CompositeStartRequest(BaseModel):
    plan_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    confirmation_digest: str = Field(pattern=r'^[a-f0-9]{64}$')

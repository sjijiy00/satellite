# A4 완료와 후속 개발 계획

기준일: 2026-10-29. A1·목적별 추천·A2·A3에 이어 A4 식생 NDVI 두 날짜 변화를 구현했다. A2 메타데이터 검사와 A3 품질 진단은 별도 버튼으로 유지한다. A4는 보정이 확인된 Sentinel-2 L2A만 실제 NDVI와 ZIP 내보내기를 제공한다. A5는 별도 요청 시 착수한다. 최신 실행 근거는 TEST_REPORT.md를 따른다.

| 단계 | 구현 범위 | 완료 기준 / 주요 검증 |
|---|---|---|
| A2 | 전후 기준일/기간, 동일 센서·제품, 필수/품질 밴드, 실제 Asset 접근, 취득일과 CRS·해상도·격자 확인. AOI∩두 footprint 교집합을 각 장면 AOI 중첩과 별도로 계산. 항목별 통과/조건부/미확인/불가, 이유와 다음 행동 제공 | 누락 CRS는 추정하지 않고 null. 파일 헤더를 읽으면 URL의 인증정보를 제외한 출처·방법을 기록. 기하 통과를 픽셀 통과로 표시하지 않음. 중복·역전·공통 영역 없음·접근 실패 테스트 |
| A3 | 접근 가능한 Sentinel-2 L2A 두 날짜, 작은 AOI의 실제 band/SCL window 읽기. 제공처 최신 scale/offset·NoData 확인. AOI 면적·픽셀·파일 크기·시간·동시 작업 상한. 버전 명시 SCL 정책, 구름·그림자·NoData·눈·분류불명 처리. 범주 보존 재표본화와 단일 공통 격자 | 고정 소형 래스터 기대값 + 실제 영상 재현. 개별/공통 유효 면적, AOI 전체 및 공통 촬영 영역 각각의 비율. 적절한 투영/측지 면적. 파일 실패/null과 실제 0% 구별. 운영 임계값은 설정 가능 기준으로 표시 |
| A4 | 동일 센서 수역 또는 식생 변화 하나. 검증된 공통 유효 픽셀만 지수 계산. 전후·차이·면적·제외 영역·마스크, GeoTIFF와 JSON 내보내기 | QGIS 호환 CRS/NoData/밴드. 원본 Item/Asset·취득시각·처리버전·마스크·격자·scale/offset 기록, 비밀키·서명 URL 인증정보 제외. 0 분모·NaN/Inf·잘못된 scale·역전·중복·다른 격자·전부 구름 테스트. 수역 변화 후보를 침수 확정으로 표현하지 않음 |
| A5 독립 | 공식 자료와 실제 API에서 접근 가능한 Sentinel-1 컬렉션·제품·Asset 확인 후 연결. SAR 편파·궤도 방향·모드 등을 광학과 별도 모델로 취급 | 실제 검색·메타데이터·Asset 접근 확인까지만 검증. 인증·비용·자격증명·새 지속 접근이 필요하면 해당 단계 중지 및 필요한 조치 보고. 전처리·침수·광학 융합은 포함하지 않음 |

A1의 `/selection-overlap`은 선택 실수를 안내하는 양의 면적 공통 footprint 존재 검사뿐이다. 면적·비율, 실제 Asset 접근, 래스터 검사, 분석 가능 판정은 A2/A3 구현으로 오인하지 않는다.

A2는 `backend/app/analysis_conditions.py`, `grid_metadata.py`, 기존 `selection.py`/`evaluation.py` 및 `frontend/src/components/AnalysisConditions.tsx`에 구현했다. A3는 `pixel_quality.py`, `pixel_raster.py`, `pixel_policy.py`, `range_reader.py`, `pixel_worker.py`, `PixelQuality.tsx`에 구현했다. A4는 `change_analysis.py`, `ChangeAnalysis.tsx`와 기존 A3 파이프라인 연결로 구현했다. 공개 S2 COG에서 보정 메타데이터 상충은 분석 보류로 남긴다. A5 `providers/`는 아직 만들지 않았다.

## 2026-10-29 지도 탐색 1차 연결과 후속 범위

기존 Next.js·MapLibre·FastAPI 구조를 유지하고, 이미 검색한 실제 STAC Item을 UTC 날짜별로 묶는 화면 모델을 추가했다. 날짜·결과 카드·지도 촬영 범위·선택 상세는 하나의 상태를 사용한다. 같은 AOI 지도에서 두 비교 영상 범위를 강조한다. 실제 A3 SCL/NoData 검사 또는 A4 NDVI 계산이 끝났을 때만 각각의 지도 화면 미리보기 레이어를 활성화한다. 원본 thumbnail과 정량 래스터는 별도로 설명한다. 날짜가 없거나 사용자 확정 기간 밖인 Item은 자동으로 기간을 바꾸지 않고 별도 안내한다.

후속 HLS 검색/GIBS 미리보기는 [어댑터 설계](HLS_ADAPTER_DESIGN.md)에만 기록했다. S30/L30의 30 m 제품, GIBS 표시용 타일, 원본 파일 접근을 각각 별도 상태로 검증한 뒤에만 추가한다. HLS 장애가 기존 STAC 성공 결과를 숨기지 않아야 한다. A5 Sentinel-1 검색도 미착수다. 3D·음성·실시간 추적·새 구름 복원 엔진은 이번 지도 탐색 범위에 포함하지 않았다.

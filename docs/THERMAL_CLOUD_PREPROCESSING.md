# Landsat 구름 결측 전처리

2026-11-05 추가. `surface_temperature` 세부 분석에서 `thermal_gapfill`을 명시 선택하면 실행합니다. 기존 단일 날짜 온도 분석과 Sentinel-2 식생 합성/ML은 그대로 유지합니다.

## 화면에서 실행

1. Planetary Computer Landsat L2SP 제품으로 같은 지역의 두 날짜를 검색합니다.
2. 분석 준비·실행에서 **지표면 온도 분포**를 확정합니다.
3. **전처리 · 구름 제거 → 다른 날짜의 맑은 관측으로 구름·그림자·구름 인접 빈 곳 채우기**를 선택합니다.
4. 영상 1에 대상 날짜, 영상 2에 보충 날짜를 선택합니다. 동일 Landsat 플랫폼·L2SP, 서로 다른 UTC 날짜, 31일 이내입니다. 검색 기간도 31일 이내여야 합니다. 보충 날짜는 대상보다 이전이어도 됩니다.
5. 공통 처리 계획 검사 → 입력·산출물 확인 → 확인한 계획 실행 → 결과 ZIP과 연구 기록 JSON을 저장합니다.

## 계산 범위

대상 날짜의 QA 통과 온도는 바꾸지 않습니다. 대상 QA_PIXEL의 dilated cloud/cirrus/cloud/shadow 비트(1–4) 또는 실제 관측 중 사용자가 정한 최소 구름 거리 미달 픽셀만 보충 후보입니다. fill/snow 비트는 제외합니다. 불확실성만 초과한 값, 구름 표시 없는 일반 NoData를 임의로 채우지 않습니다.

보충 영상은 기존 QA_PIXEL·QA_RADSAT·NoData·ST_QA·ST_CDIST 기준을 모두 통과해야 합니다. 원래 픽셀에서 QA를 적용한 뒤 공통 격자로 정렬합니다. 연속값 average/유효 비율 0.999 이상, QA nearest, 불확실성 max, 구름 거리 min을 사용합니다. 두 영상 모두 유효하지 않으면 결측으로 유지합니다. 전체 유효 값이 없으면 실패하며 가짜 0 온도 파일을 만들지 않습니다.

이는 **다른 날짜의 관측 선택**입니다. 구름 아래 대상 날짜의 온도를 예측하거나 복원하지 않습니다. 날씨·계절·지표 상태가 날짜 사이에 달라질 수 있으므로 합성 지도를 대상 날짜의 온도 분포·기간 평균·고온 비교 입력으로 자동 연결하지 않습니다. 두 영역의 통계는 날짜와 공간 범위가 다르며 변화량 비교가 아닙니다. 범용 ML 구름 제거는 추가하지 않았습니다.

최대 200 km²·600,000셀·36타일의 기존 제한 격자를 사용합니다. 작은 작업은 입력 64 MiB/75초, 큰 작업은 256 MiB/255초, ZIP은 16 MiB 상한입니다. 실패한 타일을 성공으로 게시하거나 AOI를 자동 축소하지 않습니다.

## 저장 파일

| 파일 | 내용 |
|---|---|
| target_temperature.tif | 대상 날짜 유효 온도, Kelvin/섭씨 |
| filled_only.tif | 실제 채운 다른 날짜 온도만, Kelvin/섭씨 |
| multi_date_temperature.tif | 대상 관측 + 다른 날짜 보충; 단일 날짜 복원 아님 |
| pixel_status.tif | 0 결측/바깥, 1 대상 관측, 2 다른 날짜 보충 |
| source_index.tif / source_date.tif | 원본 Item 인덱스 / UTC epoch 일수 |
| valid_mask.tif / exclusion_mask.tif | 합성 후 유효 영역 / 제외 상태 |
| manifest.json | 입력, 날짜, 보정·QA·출처·파일 검증·실행 기록 |

float 온도 NoData는 -9999, 날짜 NoData는 -2147483648입니다. 원관측 면적·보충 면적·남은 결측·보충 후 유효율을 따로 표시하며, 보충 0이면 효과가 없었다고 표시합니다. 연구 기록 JSON에도 이 구분과 날짜별 통계를 보존합니다.

## 검증과 출처

`test_thermal_gapfill.py`는 테스트 전용 실제 TIFF로 원관측 보존, 구름·그림자·인접 픽셀 보충, 두 날짜 구름/보충 QA 탈락/일반 NoData/불확실성 단독 탈락의 미해결 유지, 출처 날짜, 저장 파일 재열기, 같은 플랫폼·서로 다른 날짜를 검증합니다.

별도 실제 공개 검색·Range 읽기·브라우저 ZIP/연구 기록 저장을 Las Vegas 2025-07-19 대상 / 07-03 보충으로 확인합니다. 이 표본의 결측은 불확실성 초과여서 구름 보충 면적은 0입니다. 실제 구름 영역 개선율이나 지상 참값 정확도를 검증했다고 주장하지 않습니다. 상세 실행 결과는 TEST_REPORT 및 `test-results/cloud-preprocessing-20261105/`에 기록합니다.

[USGS 지표면 온도 제품](https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature)과 [QA 비트 정의](https://www.usgs.gov/landsat-missions/landsat-collection-2-quality-assessment-bands)를 제품 보정·QA의 근거로 사용합니다. 날짜 간 보충 정책은 앱의 제한된 선택 정책이며 USGS가 보증하는 복원 알고리즘이 아닙니다.

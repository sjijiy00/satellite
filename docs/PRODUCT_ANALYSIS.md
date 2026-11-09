# 현재 제품 분석 범위 — 2026-11-04 통합 개선

기존 제품 allowlist·공식 scale/offset·QA 버전·수치 커널은 그대로 재사용합니다. 단일 시점 `ndvi/mndwi/ndbi/surface_temperature/hotspots/temperature_comparison`만 제한된 큰 AOI 경로(최대200km²·600,000셀·36타일)로 확장했습니다. 고정 격자 core/halo·개별 타일/총 요청·전송·시간·디스크·ZIP 상한을 검사하며 일부 실패는 전체 실패입니다. 실제 공개 S2B79.6km²/9타일 파일 검증과 S2/Landsat 고정 TIFF의 단일/타일 기대값 비교를 구분합니다. 온도 대형 실연결·최대 상한/도시 전체 성능은 미검증입니다.

전후 변화50km²/150,000셀·관측 합성/제한 ML25km²는 유지합니다. 계산8종의 현재 fixture와 실제 소형/대형 NDVI·QGIS 근거는 최신 TEST_REPORT, 자원/영속 보관/재현은 [RESEARCH_WORKFLOW](RESEARCH_WORKFLOW.md)를 따릅니다. 아래의 ZIP/작업15분·메모리만 보관·대형 전혀 미지원 문구는 이전 제품 단계 기록입니다. HLS/VIIRS/SAR/PC S2 픽셀 미지원·침수/피복 분류 미지원은 여전히 유효합니다.

---

# 제품별 실제 기초 분석 (products-2)

확인일 **2026-11-03**, 정책 `products-2026-11-03.1`, QA `product-qa-2026-11-03.1`. 1단계 조사와 2단계 공통 처리 기반을 확장했다. 실제 통과/실패·명령·파일 근거는 [TEST_REPORT](../TEST_REPORT.md)를 따른다.

## 목적·제품 적합성 표

`product_policy.py`와 `analysis_catalog.py`가 API로 반환하는 실행 계약이다. 추천·검색·접근·AOI 품질·실행 지원·작업 성공은 별개다.

| 사용자 작업 / method | Earth Search S2 L2A | PC Landsat 8/9 C2 L2 | 필수 조건/결과 |
|---|---|---|---|
| 식생지수 / `ndvi` | B04 red·B08 nir·SCL | SR_B4 red·SR_B5 nir08·QA_PIXEL/RADSAT | 한 날짜. NDVI·마스크·manifest·실제 지도 |
| 식생 변화 / `ndvi_change` | 기존 동일 플랫폼·기준선 두 날짜 엔진 | 미지원 | 앞→뒤 날짜·기간·기존 QA. 전후/차이3밴드·공통 유효 마스크 |
| 광학 수역 후보 / `mndwi` | B03 green·B11 swir16·SCL | SR_B3 green·SR_B6 swir16·QA_PIXEL/RADSAT | 명시 임계값/근거. 지수·후보 마스크·민감도 |
| 수역 후보 변화 / `mndwi_change` | 위 밴드, 동일 플랫폼/수준/기준선 | 위 밴드, 동일 플랫폼/수준 | 두 UTC 날짜·공통 유효 픽셀. 지수 전후/차이·유지/증가/감소 후보 |
| 도시 지수 / `ndbi` | B11 swir16·B08 nir·SCL | SR_B6 swir16·SR_B5 nir08·QA_PIXEL/RADSAT | 한 날짜. 지수·마스크. 나지/시가지 혼동, 분류 아님 |
| 지표면 온도 / `surface_temperature` | 열밴드 없음 | **L2SP만**: ST_B10 lwir11·qa_pixel·qa_radsat·ST_QA qa·ST_CDIST cdist | 한 날짜. Kelvin/섭씨2밴드·불확실성/구름거리·마스크 |
| 고온 지역 / `hotspots` | 미지원 | 위 ST 입력 | 사용자 섭씨 기준/근거. 온도·기준 초과 마스크 |
| 도시/주변 온도 비교 / `temperature_comparison` | 미지원 | 위 ST 입력 | 같은 관측/QA, AOI 안의 비중첩 확정 영역2개·이름. 면적 가중 평균·차이·유효 분모 |

HLS·NOAA VIIRS·SAR·PC S2는 새 실행 allowlist에 없다. 실제 PC S2 표본은 밴드별 보정 메타데이터가 없었고 검증된 XML 보정 어댑터를 추가하지 않아 차단한다. HLS30m를 S2 원본10m/온도 제품으로, NOAA 격자를 유효 픽셀로, SAR GRD를 보정된 후방산란/침수 자료로 처리하지 않는다. ES Landsat requester-pays·USGS/NASA/CDSE 인증은 PC 익명 SAS와 별개다.

침수 확정·토지피복 변화 분류는 계속 미지원이다. 사건 기준·호환 관측/검증·SAR 보정/지형/편파/궤도/모드, 분류 체계·독립 정답 검증 엔진이 없다. 물 증가를 침수로, NDBI를 피복 분류로 바꾸는 버튼과 생성형 픽셀 보충은 없다.

## 공식 근거·버전

아래 공식 문서를 2026-11-03 확인했다. URL·확인일·문서/정책 버전, 실제 Item 기준선·밴드/보정·헤더·촬영일을 manifest에 남긴다.

- [Copernicus S2 제품](https://sentiwiki.copernicus.eu/web/s2-products), [L2A 밴드/SCL](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S2L2A.html): quantification과 밴드 offset을 적용한다. ES canonical baseline·`earthsearch:boa_offset_applied`·scale/offset이 맞아야 한다. 날짜로 offset을 추정하지 않는다. NoData DN0을 먼저 제외한다. red/NIR/green10m, SWIR1/SCL20m를 공통20m로 맞추며 상세도를 만들어내지 않는다.
- [USGS 보정식](https://www.usgs.gov/faqs/how-do-i-use-a-scale-factor-landsat-level-2-science-products): C2 SR=`DN×0.0000275−0.2`, ST=`DN×0.00341802+149` Kelvin, 섭씨=Kelvin−273.15. raw 정수 DN에서 정확히 한 번 적용한다. 이미 L2인 제품에 대기 보정을 반복하지 않는다.
- [USGS LSDS-1619 v6.0, May2024](https://d9-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/s3fs-public/media/files/LSDS-1619_Landsat8-9-Collection2-Level2-Science-Product-Guide-v6.pdf), [QA](https://www.usgs.gov/landsat-missions/landsat-collection-2-quality-assessment-bands), [ST 제한](https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature): SR/ST fill0, QA_PIXEL fill bit0, ST 품질 중간 자료 fill−9999를 구분한다. 불확실성과 구름 거리 계수는0.01K·0.01km다. QA의 정수0은 결측이 아니다.
- [USGS TIRS](https://www.usgs.gov/landsat-missions/landsat-8): 열관측100m와 ST 제품30m 출력 격자를 구별한다. 구름 주변 오차·방사율/ASTER 보조자료 결측이 남는다.
- [NASA NDVI](https://science.data.nasa.gov/disasters/data-gallery/landsat-ndvi), [MNDWI](https://science.data.nasa.gov/disasters/data-gallery/landsat-mndwi), [LP DAAC 지수 정의](https://gis.earthdata.nasa.gov/portal/rest/services/nasa_lp_daac/HLSL30_v2_Service/ImageServer/rasterFunctionInfos): NDVI=(NIR−Red)/(NIR+Red), MNDWI=(Green−SWIR1)/(Green+SWIR1), NDBI=(SWIR1−NIR)/(SWIR1+NIR). 마지막 자료는 식의 근거이며 HLS 엔진 활성화 근거가 아니다.

정규화 차이는 기존 NDVI 수치 커널을 재사용한다. QA 제외 뒤 유한·비음수 반사도와 분모>1e−6을 요구한다. 음의 반사도/0분모/NaN을 실제0으로 바꾸지 않고 제외 면적을 기록하는 보수적 정책이다.

## QA·사용자 기준

- S2는 기존 SCL4/5/6만 허용한다. Landsat은 fill/팽창구름/권운/구름/그림자/눈 비트0–5, confidence값2/3, 모든 RADSAT 플래그를 보수적으로 제외한다. 물 비트7 자체는 제외하지 않는다.
- 실제 PC QA_PIXEL의 STAC fill1/헤더 NoData 태그 없음은 문서화된 bit0으로 검사한다. 반사도/ST/중간 QA의 헤더 검사에 이 예외를 적용하지 않는다.
- 온도 QA 제안 운영값 ST_QA≤2K·CDIST≥1km는 화면에서 수정하고 계획에서 명시 확인한다. 보편적 정확도/최적 임계값이 아니다. 원래 품질 값도 파일로 출력하며 검증을 위해 기준을 몰래 낮추지 않는다. 구름/그림자/NoData·수치·불확실성/근접 사유의 면적은 겹칠 수 있어 합산하지 않는다.
- MNDWI 기준은 미지정으로 시작한다. 사용자 값(−1~1)/근거가 있어야 `지수>기준` 후보를 만든다. 기준±0.05(−1~1에서 제한)의 면적 민감도는 앱의 비교 간격이며 정확도 보장이 아니다. 고온도 사용자 섭씨 기준/근거가 없으면 실행하지 않는다.
- 비교 영역은 사용자 입력/확인이 필요하고 AOI 안에서 겹치면 안 된다. 같은 온도/QA·면적 가중치로 영역별 확정 면적·유효 면적·평균을 구한다. 행정경계 통계나 열섬 원인을 자동 확정하지 않는다.

## 입력·저장·한도

서버가 선택 canonical Item/Asset을 재조회하고 EO 밴드 식별·제품 버전/수준/플랫폼·UTC 날짜·NoData·자료형·보정·실제 헤더/격자를 검사한다. 브라우저에 받은 TIFF/수신 기록을 서버 계산 입력이나 증거로 쓰지 않는다. 원본은 보존하고 수집만 종료하는 경로도 유지한다.

기존 공개 COG/PC 서버 익명 SAS·목적지/HTTPS/DNS 검사·리다이렉트 거절·64MiB/128요청·작업 시간·ZIP16MiB·TTL15분·단일 worker 계약을 재사용한다. SAS는 메모리에서만 쓰고 unsigned Item/Asset 식별만 출력한다. 미리보기·HEAD200은 래스터 읽기 성공이 아니다.

새 지수/ST는 50km²/150,000셀 이내 제한 window, 제품별20/30m 고정 격자다. QA는 nearest, 연속값은 native QA/NoData 제외 후 average(유효 기여율0.999), ST 불확실성 max/구름 거리 min이다. 도시 전체 분산 처리·임의 출력 격자는 추가하지 않았다.

GeoTIFF·valid_mask·exclusion_mask·manifest·기존 지도용 실제 PNG를 제공한다. 제외코드0=ROI밖/1=미관측/2=QA·NoData·수치 제외/3=유효. 물 후보/고온 코드0=invalid/1=유효 비후보/2=후보, 물 변화0=invalid/1=지속 비후보/2=감소/3=증가/4=지속 후보다. AOI 전체·실제 관측·QA/수치 제외·유효 면적을 구분한다. 온도 품질 파일은 가능한 관측 범위의 원래 품질 값을 보존한다.

저장 후 CRS/transform/크기/밴드/자료형/단위/NoData·전체 배열 읽기·해시를 확인하고 binary ZIP을 제한 전송한다. 브라우저 전체 수신/해시/저장 파일 재열기와 QGIS/ArcGIS GUI 검증은 별개다.

## 화면 순서

수집→세부 분석 확인→공통 패널의 제품/원해상도/출력 격자·필수 QA 확인→필요 기준/영역 입력→계획 검사→확인 체크→실행→succeeded/실제 지도·통계→ZIP 다운로드 순서다. 온도는 기존 기본3밴드 외 `qa`·`cdist` 선택이 필요할 수 있다. 사용자 밴드는 자동 덮어쓰지 않는다.

조건/기준은 같은 Workspace 설정/snapshot에 보관한다. 변경 시 이전 계획·확인·레이어를 무효화하고 늦은 응답을 폐기한다. 새로고침은 GET 상태만 조회하며 검색/다운로드/분석/AI를 자동 실행하지 않는다. 실제 한국 해안 ST 실패와 별도 네바다 육상 표본 성공은 TEST_REPORT에 구분한다. 모든 AOI/날짜에 유효 ST가 있다는 뜻은 아니다. 키·인증 플래그·비용 동의·유료 AI·배포/push 변경은 없다.

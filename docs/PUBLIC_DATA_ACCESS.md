# 로그인 없는 공개 자료 경로 (2026-11-02)

## 2026-11-03: Earth Search Landsat의 별도 PC 미리보기

Earth Search `landsat-c2-l2`의 requester-pays S3 Asset과 USGS LandsatLook의 로그인 리다이렉트는 공개 다운로드가 아니다. 실제 표본 `LC09_L2SP_116035_20250723_02_T1`의 USGS 경로는 HTTP302로 `ers.cr.usgs.gov`를 가리켰다. 로그인 리다이렉트는 따라가지 않으며 NASA 인증을 보내지 않는다.

기존 Planetary Computer 공개 컬렉션의 canonical Item을 조회해 **전체 제품 ID(처리일 포함), 플랫폼, 촬영 UTC 시각, 처리 수준, Collection 02, scene ID**를 모두 대조한다. PC Item의 짧은 ID만 같다는 이유로 대응시키지 않는다. 실제 Asset 경로에서 확인한 전체 제품 ID가 다르거나 누락되면 실패를 유지한다. 캐시도 전체 제품 ID를 포함해 같은 짧은 ID의 처리 버전 변경을 구분한다. 이는 미리보기 대응 검증이며 밴드 파일의 바이트 동일성을 주장하지 않는다.

검증된 대응에 한해 PC가 제공한 실제 이미지 Asset을 기존 서버 공개 전송 경로로 받아 형식·크기를 검사한다. 화면에는 `Planetary Computer 제공 미리보기`와 원래 선택 장면/원본 권한이 별개임을 표시한다. 서버 미리보기 ticket은 원래 장면과 사용자 세션에 묶인다. PC source Item과 제품 일치 근거, USGS302·목적지 호스트·requester-pays 등은 접힌 상세 정보에서 확인한다. 원래 선택, 밴드, 다운로드 ticket, 확보 상태, 픽셀 QA를 바꾸지 않는다.

PC 후보 없음/불일치/이미지 없음/장애는 원래 실패에 추가 표시한다. 사용자가 `PC Landsat에서 검색`을 누를 때만 같은 목적·AOI·UTC 기간으로 기존 검색을 다시 실행하며 PC 컬렉션을 명시한다. 자동 원본 다운로드나 인증/비용 승인은 없다. 실제 성공 표본은 전체 제품 `LC09_L2SP_116035_20250723_20250726_02_T1`의 PC PNG이며 원본 밴드 다운로드 성공을 의미하지 않는다.

### 검증 범위와 사용자 장면의 별도 재현 절차

**사용자가 처음 선택한 카드의 Item ID는 미확인이다. 표본의 성공을 사용자 장면 또는 모든 Landsat 장면의 해결로 일반화하지 않는다.** 수정 로직은 제품별로 대조하며, 실제 사용자 장면은 아래 절차가 끝날 때까지 미검증으로 남긴다. Item ID를 환경 파일에 넣거나 인증정보를 공유할 필요는 없다.

| 대상 | 미리보기 | 원본 |
|---|---|---|
| 표본 `LC09_L2SP_116035_20250723_02_T1` | PC 동일 제품 확인·전체 PNG 수신·디코딩·실제 브라우저 표시 검증됨 | Earth Search requester-pays / USGS302 로그인 제한 유지, 실제 원본 다운로드 미실행 |
| 사용자가 처음 선택한 장면 | Item ID 미확인, 미검증 | 미검증. 표본의 제한/권한을 그대로 단정하지 않음 |
| 그 밖의 Landsat 장면 | 장면별 대응/접근 검사 필요 | Asset별 별도 확인 필요 |

1. 실제 Item ID가 확인되면 **제공처 `earth-search` + 컬렉션 `landsat-c2-l2` + 공개 Item ID**를 함께 기록한다. 당시 목적·AOI bbox(서/남/동/북)·UTC 시작/종료일·선택 밴드도 보존한다. Item ID만으로 전체 처리 제품이나 권한을 추정하지 않는다.
2. 수집 페이지에서 같은 조건을 직접 입력하고 Earth Search Landsat로 명시 검색한다. 결과의 날짜/페이지를 확인해 **해당 ID의 카드**를 선택한다. 목록/선택 상세의 ID가 목표 ID인지 확인한다. 다른 표본 또는 첫 번째 결과로 대신 검증하지 않는다. 결과가 없거나 조회 상한 때문에 해당 장면을 찾지 못했다면 이를 기록하고 목표 장면 검증을 중단한다.
3. `날짜별 실제 영상`의 미리보기를 확인하고 `미리보기 출처·접근 상세`를 연다. canonical Item과 실제 Asset에서 검증한 전체 제품 ID·처리일·플랫폼·UTC 촬영 시각·처리 수준·버전을 대조한다. PC 대응이 확인되지 않으면 원래 실패를 유지하며 PC 이미지 성공으로 쓰지 않는다.
4. 미리보기의 상태·출처·HTTP 상태·전체 수신 바이트·형식·디코딩 크기를 구분해 기록한다. 이미지가 실제로 표시되는지도 확인한다. 이미지 없음/로그인/잘못된 형식/제공처 장애는 각각 실패 또는 미지원으로 남긴다. HTTP200만으로 성공 판정하지 않는다. 필요하면 `미리보기 이미지 저장`을 명시 클릭해 실제 파일을 확인하되 원본 밴드 확보로 기록하지 않는다.
5. 같은 ES 장면과 선택 밴드가 유지되는지 확인한 뒤 `선택 원본 접근 확인`을 별도로 실행한다. 이 확인은 전체 다운로드가 아니다. USGS 로그인/비용 동의가 필요하면 멈추고 제한을 기록한다. 원본 저장을 실제 실행하지 않았다면 항상 미실행으로 남긴다. PC 공개 원본을 원할 때만 `PC Landsat에서 검색`을 눌러 같은 조건을 유지한 별도 PC 결과를 확인한다.
6. 사용자 장면의 검증 기록은 표본 기록에 덮어쓰지 않고 별도 사례로 TEST_REPORT에 추가한다. 공개 식별자·검증 시각·상태 코드·허용된 목적지 **호스트만**·바이트/형식/크기·선택 보존 여부만 기록한다. 토큰·서명 query·전체 리다이렉트 URL·쿠키·원문 응답/HAR는 출력하거나 첨부하지 않는다.

기존 `frontend/tests/landsat-preview.spec.ts`의 opt-in LIVE 사례는 위 고정 표본을 검사한다. 해당 테스트 통과는 사용자 장면 검증이 아니다. 다른 장면을 자동화할 때는 목표 ID뿐 아니라 검색 AOI/기간, 그 ID 카드의 명시 선택까지 맞춰 별도 사례를 실행해야 한다. 현재의 제품 일치·미리보기/원본 분리 게이트는 그대로 유지한다.

공식 메타데이터: [PC Landsat C2 L2 컬렉션](https://planetarycomputer.microsoft.com/api/stac/v1/collections/landsat-c2-l2), [PC SAS 접근 방식](https://planetarycomputer.microsoft.com/docs/concepts/sas/). 기존 공개 전송의 허용 호스트/리다이렉트 검사, 이미지 최대8MiB, 시간·동시성·캐시 상한과 SAS 서버 갱신을 그대로 사용한다. API 응답·링크 목록·로그에는 SAS나 자격증명을 넣지 않는다. 실제 PNG 검증과 SAS 갱신 fixture 검증은 최신 TEST_REPORT에서 구분한다.

이번 구현은 기존 목적 규칙·AOI·UTC 기간·장면/밴드 선택·media API를 확장한다. 운영자 인증을 활성화하지 않으며 새 계정·키·AI 호출이 필요하지 않다. 실제 테스트의 최신 명령/결과는 [TEST_REPORT](../TEST_REPORT.md)를 따른다.

## 연결한 제품과 접근

| 앱 컬렉션 | 플랫폼·탑재체·제품 | 검색 | 미리보기 | 원본 | 앱 픽셀 처리 |
|---|---|---|---|---|---|
| sentinel-2-l2a | Sentinel-2 A/B/C · MSI L2A · Earth Search | 기존 공개 STAC | 실제 Item 이미지, 접근/디코딩 확인 후 | 공개 HTTPS Asset, 파일별 확인 | 기존 작은 AOI A3/A4 조건 유지 |
| landsat-c2-l2 | Landsat 8/9 OLI/TIRS · C2 L2 · Earth Search | 기존 공개 STAC | USGS 접근 제한과 구분, 정확한 PC 제품 대응/이미지 검증 시에만 별도 PC 출처 표시 | S3 requester-pays는 비활성 유지 | 미지원 |
| pc-sentinel-2-l2a | Sentinel-2 A/B/C · MSI L2A · Planetary Computer | 공개 STAC | Item의 실제 rendered_preview PNG | 계정 없는 단기 SAS를 서버에서 발급, 허용 Azure Asset만 전송 | 미지원, Earth Search 엔진으로 조용히 전환하지 않음 |
| pc-landsat-c2-l2 | Landsat 8/9 OLI/OLI-2·TIRS/TIRS-2 · C2 L2 | 공개 STAC, 더 오래된 Landsat는 제외 | Item의 실제 rendered_preview PNG | 계정 없는 단기 SAS, 선택 원본 파일 | 미지원 |
| noaa-viirs-ndvi-cdr | NOAA-20/JPSS-1 · VIIRS · 일별 NDVI CDR v1, JP113C1 filename v001 | 실제 공개 S3 객체 목록 | 미제공, NetCDF를 이미지로 취급하지 않음 | 공개 HTTPS NetCDF 전체 파일 | QA·NDVI 재계산/클리핑·합성·ML 미지원 |
| sentinel-1-grd | Sentinel-1 C-SAR GRD · CDSE | 기존 공개 STAC | Asset/인증별 상태 | 기존 인증 경로 별도, 이번에 활성화 안 함 | SAR 전처리·침수 분석 미지원 |
| viirs-vnp09ga-002 | Suomi NPP VIIRS VNP09GA.002 · NASA CMR | 기존 공개 CMR | 공개 browse 경로 | Earthdata/DAAC 인증 별도 | QA·NDVI 미지원 |

등록부는 **5개 제공처 / 7개 내부 컬렉션**이다. 플랫폼·센서·제품·원격 컬렉션·Item·Asset은 분리되며 컬렉션별 original_access/preview_access/pixel_processing도 구분한다. 추천은 기존 purpose_plan의 공통 규칙과 검증된 sensor_catalog를 재사용한다. PC는 기존 센서 사양을 복제해 별도 과학적 추천 규칙을 만들지 않는다. Sentinel-2는 직접 열적외선 제품이 아니며, NOAA NDVI CDR는 광역 식생 참고용이다.

## NOAA 범위와 과학적 의미

- 한국 AOI는 전 지구 일별 **제품 격자**에 포함된다. 객체 목록에는 실제 swath/맑은 픽셀 경계가 없으므로 AOI 중첩 수치를 촬영 성공·유효 관측률로 표현하지 않는다.
- 연결 범위는 실제 목록에서 확인한 **2023년 이후 NOAA-20 JP113C1 v001**이다. 전체 AVHRR/VIIRS CDR 역사나 NOAA-21, VJ109GA/VJ209GA, 야간조명·산불 제품을 연결했다고 주장하지 않는다. 범위 밖은 검색 0건과 다른 `outside_scope` 상태로 표시한다.
- 출력은 전 지구 경위도 0.05° 격자(남북 약5.56km, 동서 거리는 위도에 따라 달라짐). VIIRS 원관측 375/750m나 S2 10m 상세도와 동등하지 않다. 일별 파생 제품은 한 순간의 촬영이 아니다.
- 파일명 v001과 파일 내부 `product_version=v2r0`는 서로 다른 메타데이터다. 실제 2025-07-20 파일에서 플랫폼 NOAA-20/센서 VIIRS, NDVI·QA int16 7200×3600과 약0.05° 변환을 확인했다. NASA VNP09GA.002 버전과 혼동하지 않는다.
- NetCDF/HDF 드라이버는 설치되어 있으나 이 서비스는 제한된 원격 AOI 미리보기 생성기를 구현하지 않았다. 약64MB 전체 NetCDF를 자동 읽어 8MiB 미리보기 상한을 우회하지 않는다. 정확한 미제공 상태와 명시 원본 다운로드만 제공한다.

## 검색·정체성·실패

새 어댑터 planetary.py/noaa_nodd.py는 기존 bounded paging 엔진을 사용한다. PC 최대4회, NOAA 최대4회, 기존 Earth Search12/CDSE4/CMR4회, 요청10초·검색45초, 페이지25개·전체 반환 최대100개(기본50). 각 제공처를 따로 조회해 한 곳의 실패가 다른 결과를 숨기지 않는다. 페이지/전역 상한과 미조회 범위, 0건·오류·기간/목적 범위 밖을 표시한다. NOAA 객체 목록은 연도/날짜 prefix·continuation token으로 조회하고 실제 파일명·크기·기간을 검증한다. 테스트 fixture를 서비스 실패의 대체 자료로 쓰지 않는다.

중복 키는 제공처+내부 컬렉션+Item이다. 다른 제공처의 동일 원천 제품은 전체 Landsat product ID(처리 날짜·수준·컬렉션 포함) 또는 전체 S2 SAFE ID/처리 baseline, 플랫폼·촬영 날짜를 모두 확인한 때만 접근 경로를 묶는다. Item을 삭제/합치거나 다른 제품을 같은 파일로 표현하지 않는다. 파일 바이트·밴드 처리의 동등성은 별도다. 원천 ID가 없으면 묶지 않는다.

## SAS·전송·캐시

- PC 공식 `/api/sas/v1/token/{account}/{container}`를 **키·로그인 없이** 서버에서 호출한다. 알려진 계정/컨테이너만 허용하며 임의 URL 서명 API는 없다. expiry와 se, 서명 존재·읽기 권한을 검증하고 만료60초 전 재발급, 401/403이면 같은 Asset에 한 번만 재발급한다. 발급 경합은 계정/컨테이너별 잠금으로 합친다. 실제 서비스는 spr를 생략하지만 전송은 항상 HTTPS로 제한한다.
- SAS는 프로세스 메모리에만 보관한다. 브라우저·응답·링크 목록·manifest·문서·로그에는 unsigned 원본 경로 또는 방문자별 same-origin receipt만 사용한다. PC rendered_preview는 공식 Item이 제공한 경로·Item/collection 파라미터를 다시 확인한다.
- canonical Item/실제 NOAA 객체를 서버에서 다시 조회하고 Asset key로 해석한다. 호스트·컨테이너/경로·공인 DNS·매 리다이렉트를 검사한다. 새 공개 전송은 최초 호스트/컨테이너 밖 리다이렉트를 차단한다. Authorization 헤더는 이 두 어댑터에서 사용하지 않는다.
- 기존 미리보기8MiB/16MP 디코딩, 원본256MiB, 외부 전송35초, 검사60초, 클라이언트 스트림120초·동시2 제한을 유지한다. 사용자별512MiB/시간과 새 공개 제공처별512MiB/시간 상한. 같은 원본 동시 전송은 busy로 막는다.
- 공개 미리보기는 기존 검증 캐시를 분리된 public 키로 재사용:16MiB/60초/동시2·요청 합치기. 원본은 자동 수신/영속 캐시하지 않는다. 클릭 때 제한된 임시 spool로 전체 수신 후 응답하고 닫으면 제거한다. 접근 확인은 GET 앞1024바이트와 형식 확인이며 **다운로드 완료가 아니다**.
- 현재 미디어 세션·receipt·캐시·한도는 단일 worker 프로세스 기준이다. 다중 worker/공개 규모 운영의 공유 제한·캐시·영수증 저장소는 후속 과제다. 무료 공개 데이터라도 자체 호스팅·전송·클라우드 연산 비용까지 무료라는 뜻은 아니다.

## 공식 출처·이용 조건 (2026-11-02 확인)

- [PC 공식 SAS 설명](https://planetarycomputer.microsoft.com/docs/concepts/sas/), [공식 Data Authentication OpenAPI](https://planetarycomputer.microsoft.com/api/sas/v1/openapi.json): anonymous read SAS. STAC/SAS 실제 요청과 PNG/TIFF 내용도 확인했다.
- [PC Landsat collection](https://planetarycomputer.microsoft.com/api/stac/v1/collections/landsat-c2-l2), [PC S2 collection](https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-2-l2a): 컬렉션 license 문자열은 proprietary지만 각각 USGS Public Domain/Copernicus Sentinel terms 링크를 제공한다. 문자열만으로 모든 PC 자료의 재제공 권한을 일반화하지 않는다. [PC 이용 조건](https://planetarycomputer.microsoft.com/terms)과 개별 제품의 원출처 조건도 적용된다.
- [USGS Landsat 무료 공개 안내](https://www.usgs.gov/faqs/how-do-i-search-and-download-landsat-collection-2-data-products), [USGS data policy](https://www.usgs.gov/core-science-systems/hdds/data-policy): PC의 해당 원본 제품만 사용한다. requester-pays S3를 USGS/PC 인증으로 우회하지 않는다.
- [Sentinel 데이터 조건](https://dataspace.copernicus.eu/terms-and-conditions): Sentinel 데이터의 free/full/open 사용과 웹 포털의 다른 콘텐츠 권한은 별개다. 제품 출처·변형 여부를 유지한다.
- [NOAA NODD 공식 목록](https://www.noaa.gov/nodd/datasets), [NOAA terrestrial CDR 공개 버킷/조건](https://registry.opendata.aws/noaa-cdr-terrestrial/), [NCEI NDVI CDR](https://www.ncei.noaa.gov/products/climate-data-records/normalized-difference-vegetation-index), [Use Agreement](https://www.ncei.noaa.gov/pub/data/sds/cdr/CDRs/Normalized_Difference_Vegetation_Index/UseAgreement_01B-20b.pdf): 공개·비독점·제한 없는 자료 사용, 출처 표기 권장, NOAA 보증/제휴로 표현 금지. 자료 라이선스가 별도 알고리즘 소프트웨어 전체의 라이선스인 것은 아니다. VIIRS DOI10.25921/gakh-st76.

## 미연결/제한 제품의 다음 경로

검색 결과의 접힌 추가 제공처 안내는 현재 AOI/기간 장면을 확인했다는 뜻이 아니다. 실제 확인 전 다운로드 버튼은 만들지 않는다.

| 필요한 자료 | 다음 제공처·제품 | 사용자가 후속 준비할 인증/제약 |
|---|---|---|
| Landsat의 다른 공식 경로/큰 파일 | USGS M2M / EarthExplorer C2 L2 | USGS 계정·M2M 권한·Application Token, 계정 쿼터. 기존 OPERATOR_USGS_* 서버 설정 문서 참조 |
| SAR 전천후 관측 원본 | CDSE Sentinel-1 GRD / NASA ASF | CDSE access/refresh 또는 Earthdata/ASF 승인. 계정/EULA·전처리 별도. 기존 OPERATOR_CDSE_* 설정 문서 참조 |
| Suomi NPP VNP09GA.002 원본 | NASA Earthdata / LP DAAC | 해당 DAAC에 유효한 OAuth 또는 운영자 User Token, 승인/EULA 확인. 기존 EARTHDATA_* / OPERATOR_NASA_* 서버 설정 참조 |
| 추가 열·기상 제품 | EUMETSAT Data Store / GK2A AMI | EUMETSAT consumer key/secret·제품 라이선스/시야, GK2A 활용 신청·authKey 필요. 둘 다 이번 검색 미연결 |
| 고해상도 상용 영상 | Planet 제품 계약 | 공식 계정/API key 또는 지원 OAuth·별도 구매/다운로드·재제공 계약. 이번에 계정/유료 API 활성화 안 함 |

GOES ABI는 한국 상세 관측 대안으로 추천하지 않는다. NOAA-21, GK2A, Himawari 등을 이름만 등록해 검색 지원으로 표시하지 않는다. 토큰은 채팅/프런트에 입력하지 않고, 필요한 제공처를 결정한 후 서버 전용 설정으로 준비한다.

## 화면 확인 순서

1. 목적·AOI·UTC 기간을 지정하고 확정한다. 예: bbox126.7,36.4,126.71,36.41, 2025-07-20~26. 작은 AOI는 연결 검사일 뿐 모든 제품의 상세 분석 보장이 아니다.
2. PC Landsat 열환경 / PC S2 식생 / NOAA NDVI 식생 카드를 선택하거나 같은 수동 컬렉션을 선택한다. 최종 검색 조건을 확인하고 검색한다.
3. 제공처별 성공/0건/실패/제한을 보고 장면을 선택한다. PC는 실제 PNG 표시, NOAA는 정확한 미리보기 미제공·NetCDF 안내를 확인한다.
4. 기존 밴드 패널에서 파일을 선택하고 `선택 원본 접근 확인`을 누른다. 이때 전체 파일을 내려받지 않는다.
5. `원본 다운로드`를 명시적으로 누른다. 원본 전체 파일·미리보기 이미지 저장·AOI QA/처리 결과를 구별한다. 기존 A2~A4는 Earth Search S2 조건에서만 사용한다.

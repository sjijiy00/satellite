# 다중 제공처 실제 검색 — 2026-10-30

기존 Next.js·MapLibre·FastAPI와 결정론적 추천 규칙을 확장했다. 목적·확정 AOI·UTC 기간을 한 번 입력하고 명시 검색하면 연결 제공처의 실제 결과·부분 실패·접근 경로를 같은 화면에서 확인한다. OpenAI는 기존 선택형 자연어 구조화에만 사용하며 추천/위성 검색에 호출하지 않는다. 기존 사용자 `.env`는 변경하지 않는다.

## 이번에 연결된 범위

| 제공처 | 플랫폼 / 탑재체 | 제품 / 앱 컬렉션 | 추천 목적 | 앱 처리 |
|---|---|---|---|---|
| Element 84 Earth Search (기존 유지) | Sentinel-2 A/B/C / MSI | L2A / `sentinel-2-l2a` | 식생·도시, 맑은 시기 홍수 보완 | 기존 작은 AOI A3, 제한된 식생 A4·관측 합성·국소 ML 조건 유지 |
| Earth Search (기존 유지) | Landsat 8/9 / OLI·OLI-2, TIRS·TIRS-2 | C2 L2 / `landsat-c2-l2` | 식생·도시·홍수 광학 보완, L2SP 열환경 | 기존 A2 메타데이터 검사; 래스터 처리 없음 |
| Copernicus Data Space (신규) | Sentinel-1 A/B/C / C-SAR | Level-1 GRD·GRD COG / `sentinel-1-grd` | 홍수의 SAR 관측 후보 | 검색·메타데이터만. SAR 보정·지형 처리·침수 면적·A3/A4·합성·ML 없음 |
| NASA CMR / LP DAAC (신규) | Suomi NPP / VIIRS | `VNP09GA.002` / `viirs-vnp09ga-002` | 광역 식생 일별 반사도, 조건부 참고 | granule 검색·HDF5 접근 안내만. 밴드 픽셀·QA·NDVI·합성·ML 없음 |

NOAA는 기관명이며 위성명으로 사용하지 않는다. `VNP09GA`를 NOAA-20/21 제품으로 표시하지 않는다. 원관측 VIIRS I/M 대역 nadir 375/750 m와 제품의 SIN 500 m/1 km 출력을 구별한다. 일별 제품은 한 순간 촬영이 아니고 Sentinel-2 10 m 상세 관측의 동등 대안이 아니다. 제품 구성·밴드·QF 근거는 [NASA VIIRS 제품표](https://viirsland.gsfc.nasa.gov/Products/NASA/ReflectanceESDR.html)와 [V2 User Guide](https://lpdaac.usgs.gov/documents/1657/VNP09_User_Guide_V2.pdf)를 따른다.

Sentinel-1은 SAR GRD 디지털 값이다. 광학 MNDWI/반사도나 지표온도와 다른 관측량이며 스펙클·관측모드·편파·궤도·보정·지형 영향 검토가 필요하다. 장면의 `sar:instrument_mode`, `sar:polarizations`, `sat:orbit_state/relative_orbit`, 제품 유형/수준, 제공된 해상도/격자 메타데이터를 보존한다. 미제공은 null이며 10 m 격자를 10 m 유효 해상도로 바꾸지 않는다. [공식 GRD 제품 설명](https://sentiwiki.copernicus.eu/web/s1-products)을 참고한다.

## 모델과 API

- `provider_registry.py`: 제공처, 플랫폼, 탑재체, 제품, 앱 컬렉션, 원격 collection/concept ID를 별도 엔터티로 등록한다. 제품별 검색/원본 접근/픽셀 처리 상태를 독립 저장한다. `sensor_catalog.py`의 검토된 사양과 `purpose_plan.py`의 목적 요구를 재사용하며 별도 추천 엔진을 만들지 않았다.
- 실제 장면은 `provider_id + collection + id`로 식별한다. 원격 컬렉션과 제품 ID·실제 탑재체 메타데이터·Asset은 별도 필드다. 프런트 `sceneKey`는 이전 fixture/옛 응답의 2요소 키도 읽지만 신규 응답은 제공처를 포함한다.
- `POST /search`: 기존 요청과 함께 신규 컬렉션/추천 `s1_csar`, `viirs_sr` 지원. AOI·기간은 모든 어댑터에 그대로 전달한다. 명시된 기간 밖 자료는 서버에서 다시 제외하며 기간/목적을 확장하지 않는다. 추천 카드를 선택하지 않으면 목적에 허용된 연결 제품들을 검색한다. 직접 선택 검색의 미적합 참고 자료는 적합 후보로 보증하지 않는다.
- 공통 Scene에 `provider_id`, `sensor_ids`, `product_id`, `remote_collection`, `product_type`, `end_datetime`, `native_resolution`, `output_grid`, `sar`, `support`를 추가했다. 다운로드 Asset에는 `authentication_required`, `access_verified=false`를 추가한다. 실제 접근 검증을 실행하지 않은 검색 링크를 확인 완료라고 표시하지 않는다.
- `source=live-stac`은 기존 호환 값이다. 새 `endpoints`와 각 Scene/상태의 `provider_id`를 보고 STAC/CMR를 구별한다. CMR의 CMR concept Item 링크도 원본 Item으로 연다.
- `GET /catalog`: 등록/검토된 제품과 **앱 내 미연결** 후보를 분리해 반환한다. `GET /catalog/discover/{earth-search|copernicus|nasa-cmr}`: 공식 컬렉션을 다시 발견한다. 무키·읽기 전용, 최대 3요청/15초. CMR는 VIIRS 컬렉션 범위, 페이지 크기 25. 새 컬렉션은 `review_required=true`이며 자동 추천/연결/저장하지 않는다. 다음 제품은 공식 사양·범위·권한·정규화/fixture/live 검토 후 등록한다.
- 신규 제품은 해석 문맥에서 선택할 수 있으나 픽셀 처리용 `ItemReference`는 기존 Earth Search 제품으로 제한한다. 프런트도 A2와 S2 처리 버튼을 제한한다. CMR/SAR에 가짜 QA·분석 레이어를 생성하지 않는다.

Copernicus는 [공식 현재 STAC](https://documentation.dataspace.copernicus.eu/APIs/STAC.html)의 `https://stac.dataspace.copernicus.eu/v1/search` GET과 `sentinel-1-grd`를 사용한다. NASA는 [CMR API](https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html)의 `granules.json`, 등록 concept `C2631841556-LPCLOUD`를 사용한다. CMR polygon은 문서의 위도/경도 순서를 GeoJSON 경도/위도로 변환한다. 날짜변경선을 감싼 모호한 기하는 임의 전지구 사각형으로 바꾸지 않고 미확인으로 둔다. 기하는 granule 메타데이터 범위이며 유효 관측 픽셀이나 현재 AOI 구름량이 아니다.

## 검색 상한과 실패

| 제공처 | 최대 요청 | 페이지 크기 | 어댑터별 반환 확보 상한 | 시간 |
|---|---:|---:|---:|---|
| Earth Search | 12 | 25 | 요청의 max_items (최대 100) | 제공처별 전체 45초 / 회당 10초 |
| Copernicus STAC | 4 | 25 | 위와 같음 | 위와 같음 |
| NASA CMR | 4 | 25 | 위와 같음 | 위와 같음 |

제공처는 독립 병렬 실행한다. 전체 최대 20회(선택한 제공처에 따라 감소), 최종 응답은 모든 제공처의 결과를 번갈아 `max_items`까지 제한한다. 한 곳의 시간 초과/0건이 다른 곳의 결과를 숨기지 않는다. 전역 한도로 확보했지만 미반환한 후보도 `buffered_not_returned`, `complete=false`, `reason=total_limit`로 남긴다. `collection_statuses`는 제공처·컬렉션별 success/empty/partial/failed/limited/not_started, 요청·중복·형식 오류·필터 제외·남은 페이지를 표시한다. 재시도·백그라운드 자동 검색은 없고, 상한 이후 남은 범위는 사용자가 기간/AOI/제품을 좁혀 다시 명시 검색한다. 전체 카탈로그의 전수/최적 순위가 아니다.

## 인증 조사와 실제 읽기 전용 확인

아래 실제 응답은 2026-10-30 검증 환경, 작은 국내 AOI `126.7,36.4,126.71,36.41`, UTC 2025-07-20~26 기준이다. 원본 전체 파일 다운로드·인증 토큰 발급·유료 호출은 하지 않았다. 리다이렉트 주소와 서명 query는 기록하지 않았다.

| 제공처/제품 | 메타데이터 검색 | 미리보기 | 원본 다운로드 | 앱 내부 픽셀 |
|---|---|---|---|---|
| Earth Search S2 | 무키; 검색/원본 Item 200 | 무키 HEAD 200 | 공개 HTTPS Asset HEAD 200. 링크별 확인 필요 | 기존 공개 COG만 S2 조건/상한을 통과할 때 가능 |
| Earth Search Landsat | 무키; 검색/원본 Item 200 | 검증 장면 미제공 | 검증 장면은 S3/요청자 비용 경로. 직접 공개 링크 없음; AWS 계정/비용 동의 필요 | 미지원. 공개라는 이유로 비용/래스터 처리 허용 추정 안 함 |
| Copernicus S1 | STAC 무키; 검색/원본 Item 200. OData 목록과 다운로드는 별개 | 표본의 공개 미리보기 301→206 범위 응답. 모든 미리보기 보장 아님 | OData ZIP HEAD 405, 무인증 GET Range 401. 계정 Bearer 토큰 필요 | 미지원. 인증만으로 SAR 처리가 구현되지 않음 |
| CMR VNP09GA.002 | CMR 무키; granule 검색/원본 concept 200 | 공개 browse 303→206 범위 응답. 서명 redirect는 저장하지 않음 | 원본 무인증 GET 302→Earthdata Login 401. HEAD의 303만으로 다운로드 허용 판단 안 함 | 미지원. Earthdata 원본·HDF5/QF 처리 연결 필요 |
| NOAA NODD GOES-19 ABI L2 LSTF | 공개 S3 LIST 200; 앱 검색 미연결 | 조회 제품에 별도 이미지 제공 경로 미검증 | NetCDF 객체 HEAD 200; 무키 공개. 전체 수신/디코딩은 미실행 | 앱 내 미지원. 클라우드 계산/전송 과금은 별개 |
| 기상청 GK2A | 무키 dataList 요청 401; 활용신청/authKey 필요 | 공식 영상 API도 authKey 안내; 이번 실제 이미지 미검증 | 공식 data API authKey 필요; 다운로드 미실행 | 앱 내 미지원 |

Copernicus 원본 인증 조건은 [OData Product Download](https://documentation.dataspace.copernicus.eu/APIs/OData.html), NASA 다운로드 조건은 [LP DAAC Earthdata 안내](https://lpdaac.usgs.gov/documents/2052/Getting_Started_with_Earthdata_Search.pdf)를 따른다. 표본 HEAD는 파일 무결성/전송 성공 보증이 아니다. NASA나 CDSE의 파일 링크가 있다는 사실만으로 무인증 직접 다운로드 버튼을 만들지 않는다.

## 후보와 다음 연결 순서

1. **NOAA-20 VIIRS VJ109GA**, NOAA-21 관련 제품: NASA CMR에서 각 버전·보유기간/파일형식/QA를 다시 확인하고 검토된 계열부터 추가. 현재 등록 후보이며 실제 검색에는 `VNP09GA.002`만 사용한다. [NASA VIIRS 제품표](https://viirsland.gsfc.nasa.gov/Products/NASA/ReflectanceESDR.html).
2. **NASA HLS S30/L30**, Copernicus **Sentinel-3 SLSTR LST**: 광학 조화/온도 제품은 변수·격자·QA가 다르다. [기존 HLS 설계](HLS_ADAPTER_DESIGN.md)를 재사용하고 별도 검토/테스트 후 연결한다. 현재 앱 내 미연결.
3. **NOAA NODD GOES-18/19 ABI**: [공식 NODD 목록](https://www.noaa.gov/nodd/datasets)과 [NOAA 관리 AWS 등록](https://registry.opendata.aws/noaa-goes/)에 공개 S3와 ABI L1b/L2 NetCDF 경로가 있다. GOES-19는 75.2°W, GOES-18은 미주 서부 관측으로 한국 AOI의 대안이라고 추천하지 않는다. 현재 후보는 추천 규칙에 포함하지 않는다. 연결 전에 fixed-grid 투영/지구 원반 가시성·스캔 영역과 AOI 실제 교차를 검사하고 시간·채널 prefix 탐색을 별도 어댑터로 구현해야 한다. 공개 자료는 NOAA 이용/출처 조건을 따르며 클라우드 계산 비용까지 무료라는 의미가 아니다.
4. **GK2A AMI**: [공식 API허브](https://apihub.kma.go.kr/apiList.do?seqApi=6)의 LE1B/산출물별 dataList·data·영상 경로를 검토했다. 자료는 전구/동아시아/한반도, NetCDF 등 실제 파일 규격/투영·채널별 해상도 확인이 필요하다. 활용신청과 authKey 전까지 미연결 유지. 연결 전 각 영역·스캔의 AOI 교차를 검증해야 하며 동아시아라는 명칭만으로 전 세계 지원을 주장하지 않는다.

추가 읽기 전용 컬렉션 발견 결과(앱 검색 연결과 다름): CMR `VJ109GA.002`는 `C2631841524-LPCLOUD`(시작 2018-01-01), `VJ209GA.002`는 `C2817354878-LPCLOUD`(시작 2023-02-10)를 200으로 반환했다. `HLSS30` v2.0은 `C2021957295-LPCLOUD`, `HLSL30` v2.0은 `C2021957657-LPCLOUD`를 반환했다. 이 결과는 컬렉션 메타데이터 발견이며 새 목적 적합도/기간별 granule 존재·파일 접근 검증이 아니다.

HLS는 [NASA 제품 설명](https://hls.gsfc.nasa.gov/products-description/)의 S30/L30 30 m UTM 지표반사도이고 [접근 안내](https://hls.gsfc.nasa.gov/data-access-and-tools/)의 밴드별 COG·Earthdata Login을 따른다. 연결 시 전 지구 육상 타일과 AOI 실제 교차·제품별 보유기간을 확인하며 물리적 해상도 향상이나 기존 S2 엔진 호환을 추정하지 않는다. SLSTR는 CDSE 공식 `/collections` 목록에서 `sentinel-3-sl-2-lst-nrt`, `sentinel-3-sl-2-lst-ntc`를 발견했다(전체 목록 428개; 앱 발견 API는 75개 상한을 표시). 이름을 추측한 `sentinel-3-slstr-l2-lst` 등은 404여서 등록하지 않았다. [공식 SLSTR 제품](https://sentiwiki.copernicus.eu/web/slstr-products)과 [Land Handbook](https://sentiwiki.copernicus.eu/__attachments/1672112/OMPC.ACR.HBK.002%20-%20Sentinel%203%20SLSTR%20Land%20Handbook%202024%20-%201.4.pdf)의 약 1 km LST·NetCDF-4 granule, 주/야간·구름/불확실성·관측 기하를 검토해야 한다. STAC 메타데이터와 CDSE 인증 원본은 별개이며 이번 SLSTR Item·다운로드·픽셀은 미검증이다.

## 사용자가 준비할 서버 전용 설정 (이번에 설정하지 않음)

- 현재 연결된 **메타데이터 검색은 새 키 없이 동작**한다. Earth Search 설정과 OpenAI `.env`를 보존한다.
- 향후 Copernicus 원본 접근: 사용자 본인의 CDSE 계정/서비스 허용 범위를 확인한 뒤, 서버 전용 `CDSE_ACCESS_TOKEN` (단기) / 필요 시 `CDSE_REFRESH_TOKEN`의 별도 비밀 저장소·갱신 수명 설계를 먼저 구현한다. 이번 앱은 이를 읽거나 토큰을 발급/갱신하지 않는다.
- 향후 NASA 원본 접근: 여러 사용자가 쓰는 사이트에서는 운영자 개인 `EARTHDATA_TOKEN`/`.netrc`를 공유하지 않는다. 사용자별 Earthdata OAuth **계정 연결 코드는 로컬 단일 프로세스용으로 구현**했으나 앱 등록·실로그인·인증 파일 다운로드는 아직 확인/구현하지 않았다. 서버 세션과 후속 파일 접근 설계는 [EARTHDATA_USER_AUTH_DESIGN](EARTHDATA_USER_AUTH_DESIGN.md)을 따른다. 기존 CMR 검색은 인증 정보를 읽지 않는다.
- 향후 GK2A: API허브 계정에서 해당 API **활용신청**·승인 후 `KMA_GK2A_AUTH_KEY`를 서버 비밀 저장소에 둔다. query authKey를 브라우저/로그로 전달하지 않는 별도 서버 어댑터가 먼저 필요하다.
- NODD의 검증한 공개 S3 읽기는 AWS 키가 필요 없지만 대용량 연산·전송은 이용하는 인프라의 과금 조건을 별도 확인한다. 요청자 비용 Asset은 사용자 AWS 자격증명·명시 비용 동의 전 우회하지 않는다.
- CDSE·GK2A의 위 변수는 **미래 설계 이름**이며 로더에 추가하지 않았다. Earthdata는 개인 토큰 변수를 추가하지 않고 **앱 등록 정보 3개 변수만** `scripts/server-env.mjs`의 백엔드 allowlist에 추가했다. 계정 생성·자격증명 입력·새 의존성·배포·push는 수행하지 않았다. 비밀값을 채팅에 붙여넣지 않는다.

`safe_urls.py`는 자격증명 userinfo, 토큰/서명/authKey query를 가진 원본/미리보기/Asset 링크를 노출하지 않는다. 인증 필요 Asset의 URL은 인증 없는 원래 경로만 보존하고 직접 다운로드/링크 저장 대상에서 제외한다. 제공처 redirect가 생성한 단기 서명 URL을 앱 상태·파일 목록·manifest·로그에 보관하지 않는다. 새 다운로드 프록시·대리 결제는 없다.

## 검증 범위

정확한 최신 명령·종료 코드·통과/실패/미실행은 [TEST_REPORT](../TEST_REPORT.md) 맨 위를 따른다. `backend/tests/test_providers.py`와 `frontend/tests/providers.spec.ts`의 fixture는 테스트에서만 사용한다. 실연결은 `LIVE_STAC=1`의 `test_providers_live.py`와 별도 공개 API E2E로 구분한다. 서버 오류를 fixture로 대체하지 않는다. API 목록·원본 링크·권한 안내는 실제 픽셀의 분석 가능성 확정이 아니다.

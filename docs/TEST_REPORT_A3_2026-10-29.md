# A3 작은 AOI 픽셀 품질 진단 — 최신 검증 보고서

검증일: 2026-10-29 (Asia/Seoul). 실제 작업 폴더: C:\Users\aicam\Documents\ChatGPT\바이브코딩. Git 저장소가 없는 기존 프로젝트를 이어서 수정했다. 이번 요청은 **A3만** 구현했다. A4 변화 분석·내보내기, A5 SAR 연결, 배포·푸시·유료 API·새 인증은 수행하지 않았다.

## 시작 확인과 재사용

AGENTS.md, frontend/AGENTS.md, README.md, TEST_REPORT.md, docs/NEXT_STEPS.md, 패키지/테스트 설정, 최신 API·모델·목적 규칙·추천·비교·다운로드 코드를 읽었다. 설치된 Next.js의 use-client 문서도 확인했다. 수정 전 실제 pytest는 **101 passed / 7 skipped**, 종료 0, 7.76초였다. 이전 A2 결과를 현재 성공 근거로 재사용하지 않았다. A2 보고서는 [과거 기록](docs/TEST_REPORT_A2_2026-10-29.md)에 보존했다.

A2의 canonical STAC 조회·시간/본문 제한·촬영일 해석, 기존 normalize, purpose_plan의 제품·필수 밴드·SCL 선택, footprint_metrics를 재사용했다. 별도 목적 추천기를 만들지 않았고 A1 컬렉션 부분 실패/페이지네이션·순위 모델은 유지했다. 구현 전 변경 파일과 테스트 계획을 제시했다.

## 최종 소스 변경 후 실제 실행

| 위치 | 명령 | 종료 코드 | 실행 결과 |
|---|---|---:|---|
| backend | $env:LIVE_STAC='1'; ..\.venv\Scripts\python.exe -m pytest -q | 0 | **143 passed**, 42.63초, 218 warnings |
| frontend | npm.cmd run build | 0 | production Webpack 빌드, TypeScript, 정적 생성 완료 |
| frontend | npm.cmd run typecheck | 0 | 독립 tsc --noEmit 통과 |
| frontend | npm.cmd run test:e2e | 0 | **33 passed**, 1.5분, Edge headless, 최신 백엔드 재시작 후 실행 |
| backend | $env:LIVE_STAC='1'; ..\.venv\Scripts\python.exe -m pytest -q -s tests/test_pixel_quality_live.py | 0 | 실제 사례 재현 **1 passed**, 9.26초; logs/a3-live.txt 저장 |
| 루트 | node scripts/start-local.mjs | 실행 중 | 최신 로컬 서버, /health 200, http://127.0.0.1:3000 |

백엔드 143개는 **135개 단위/합성 검사 + 8개 실제 외부 연결 검사**다. 이번 A3에 34개 단위/합성 검사와 1개 실제 픽셀 검사를 추가했다. 실시간 검사는 LIVE_STAC=1로 직접 실행했으며 외부 접속 미실행을 fixture 통과로 대체하지 않았다.

고정 4×4 GeoTIFF 기대값에서 SCL·DN NoData·10 m→20 m 평균/유효 기여율·분류 최근접·전체 구름 0%·NoData null·품질 파일 실패를 확인한다. 두 날짜 검사에서는 AOI 6,400 m², 공통 촬영 3,200 m², 공통 유효 2,400 m²를 확인했고 AOI 대비 37.5%, 공통 촬영 대비 75%가 각각 일치했다. 한 장면 실패 시 성공 장면을 유지하고 공통 값은 null이다. LAEA 경계 셀 부분 면적 합계, AOI 상한, 제품·필수 밴드/SCL 누락, 중복·역전·같은 날짜, 요청자 비용, NoData 상충, 보정 누락/상충/NaN, 단일 작업 잠금, 범위·파일·전송량·요청/시간 제한, timeout 시 자식 프로세스 종료를 검사한다.

새 E2E 6개 중 5개는 TEST ONLY 계약 fixture로 0%/실패 null, 입력·운영 기준 보존, QA 카드 연결, 기준일/영상/운영 기준 변경 중 늦은 응답 폐기, 미지원 센서 버튼, 모바일·504를 검사한다. 1개는 실제 추천→검색→두 날짜→SCL·필수 밴드 범위 읽기→진단 결과를 확인한다. 기존 27개도 재실행해 목적·그룹 페이지·비교·밴드 선택/복원·저장된 링크 목록 실제 내용·부분 실패·빈 결과·요청 경합·모바일 회귀를 확인했다. fixture는 tests 전용이며 서비스 실패 시 가짜 결과로 대체하지 않는다.

실제 A3 브라우저 검사는 HTTP >=400/페이지 오류 목록이 []임을 단언했다. 기존 실제 검색 검사도 HTTP 오류 []였다. 의도적으로 주입한 504는 오류 UI 검사다. 과거 원인 불명 404가 일반적으로 해결됐다고 주장하지 않는다. 화면 산출물 frontend/test-results/a3-live.png와 a3-mobile.png를 직접 확인했고 모바일 가로 넘침 검사도 통과했다. 다음 E2E 실행 시 산출물은 갱신된다.

## 이번 실행 중 발견·수정한 문제

- 최초 집중 pytest: 1 failed / 27 passed, 종료 1. HTTPX MockTransport의 이미 소비된 content 응답이 iter_raw에서 StreamConsumed를 냈다. 실제 HTTP 범위 읽기와 구분해 테스트 응답을 ByteStream으로 수정했다. 이후 집중 28개 및 최종 전체가 통과했다.
- 제한 환경의 한 집중 테스트 실행은 E 출력 후 진행되지 않아 해당 실행을 중단했다(종료 1). 상세 원인은 확정하지 않았다. 로컬 실행 권한으로 같은 범위와 최종 전체 검사를 실행해 통과했다.
- 최초 A3 E2E: 1 failed / 5 passed, 종료 1. 기준일 변경이 A3 패널을 다시 마운트해 사용자의 최소 유효율을 70으로 초기화했다. 요청/결과만 무효화하고 설정 입력은 유지하도록 수정했다. 최종 33개 통과.
- 개발 서버 재시작과 동시에 수행한 typecheck는 자동 생성 .next/dev/types 파일 교체 중 TS6053으로 실패했다(종료 1). 서버 준비 완료 후 같은 독립 명령을 순차 실행해 종료 0을 확인했다. production build는 종료 0이다.

## 구현과 판정 범위

POST /pixel-quality는 기존 목적·AOI·기간·두 Item ID와 A2 기준일, 최소 공통 유효율을 받는다. S2 L2A의 서로 다른 UTC 날짜, 같은 센서 계열/제품, 촬영 순서와 기간, 필수 밴드·SCL, 공통 촬영 영역을 검사한다. 클라이언트 Asset URL을 직접 열지 않고 canonical STAC을 재조회한다.

실제 GeoTIFF 헤더 CRS·해상도·transform·width/height·자료형·NoData·window를 기록하고, DN=0과 파일 마스크를 제외한다. 공개 sentinel-cogs.s3.us-west-2.amazonaws.com의 S2 L2A TIFF만 허용한다. HEAD 크기 확인과 검증된 HTTP 206 Range만 사용하며 200 전체 GET/리다이렉트로 대체하지 않는다. ETag가 있으면 If-Match로 파일 변경을 확인한다. URL 쿼리·자격증명·요청자 비용은 거부한다.

상한은 AOI 25 km², 공통 격자 100,000셀, 원본 window 1,000,000픽셀, 압축 블록 4,194,304픽셀, 원본 파일 2 GB(십진), 누적 전송 64 MiB, HEAD 포함 128회, 요청당 8초, 래스터 프로세스 60초, 앱 프로세스당 동시 1개다. 사전 Item 조회는 기존 A2의 총 네트워크 45초/본문 2 MB 제한을 별도로 따른다. Rasterio 작업은 별도 프로세스로 실행하고 timeout 시 종료·회수한다. 원본 전체 파일이나 출력 래스터를 저장하지 않는다.

정책 s2-l2a-qa-2026-10-29.1: 식생·수역·도시 목적 모두 SCL 4/5/6을 관측 유효로 취급한다. NoData, 포화/결함, 어두운 영역/지형 그림자, 구름 그림자, 분류불명, 구름/권운, 눈/얼음, 미지 분류를 제외한다. 목적 대상 확정 분류가 아니며 눈 분석에는 사용하지 않는다. SCL은 최근접으로 범주를 보존한다. 반사도는 원본 NoData·SCL 제외 후 평균 재표본화하며 원본 유효 기여율 0.999 이상을 채택한다. 보정이 미확인이면 DN으로 유효성만 계산한다.

AOI 중심 LAEA 등적 투영의 공통 20 m 격자를 사용하고 CRS·transform·extent·width/height를 제공한다. AOI/footprint 경계를 0.001도로 세분화하고 셀과 교차하는 부분 면적으로 경계 가중치를 계산한다. 개별 유효 면적, 공통 영역 안의 개별 유효 면적, 두 날짜 공통 유효 면적을 각각 제공하고 AOI 전체/공통 촬영 영역 분모를 구분한다. 분류 경계는 20 m 격자 근사다. 10 m 자료를 20 m로 집계하며 해상도 향상을 주장하지 않는다.

기본 공통 유효율 70%는 설정 가능한 앱 운영 기준이다. 자료 실패/픽셀 없음은 null·판정 보류, 실제 전부 구름은 checked·0%다. analysis_ready는 false이며 지수·변화·침수 확정 판정은 제공하지 않는다. 기존 추천 카드·결과·비교 UI에 해당 AOI의 장면 QA 상태를 연결하되 센서 자체가 통과했다고 표시하지 않는다.

## 실제 사례와 재현

식생 목적, AOI [126.70, 36.40, 126.71, 36.41], 검색 기간 2025-07-01~31, Sentinel-2 카드 검색 후 전후 모드에서 다음 두 Item을 선택한다. A3 버튼을 누르면 같은 공개 파일을 다시 읽는다. 외부 제공처 메타데이터·파일 변경 시 결과는 달라질 수 있다.

- S2B_52SBF_20250705_0_L2A — 2025-07-05T02:27:34.099Z
- S2C_52SBF_20250730_0_L2A — 2025-07-30T02:27:52.286Z
- AOI 및 공통 촬영 면적: 995,374.3943821327 m²
- 개별 유효 면적: 34,800 m² / 826,542.8101834629 m²
- 두 시점 공통 유효 면적: 34,800 m²
- 공통 유효 / AOI 및 공통 촬영 영역: 3.496171912439209% (이 사례는 두 분모가 같음)
- 실제 래스터 전송: 6,176,768바이트, HEAD+Range 22회. 사전 canonical Item 조회 2회는 별도.
- SCL은 실제 20 m, red/nir는 실제 10 m GeoTIFF 헤더를 확인했다. 전체 장면 구름량으로 이 수치를 추정하지 않았다.

## 제한·미해결 사항

1. 실제 두 Item 모두 baseline 05.11, earthsearch:boa_offset_applied=true인데 raster:bands offset=-0.1이 함께 있어 보정 근거가 상충한다. 제공처 공식 저장소에도 관련 이슈가 있다. **scale/offset 미확인**으로 보존하며 임의 -1000 보정이나 반사도/지수 값을 제공하지 않는다. SCL·DN NoData 기반 품질 면적은 별도로 계산한다. 이 상충은 해결됐다고 주장하지 않는다.
2. SCL은 분류 결과로 오분류 가능성이 있고, 0.999 유효 기여율 및 70% 기준은 운영 정책이다. 플랫폼 차이·계절·관측각·대기 보정 일관성이나 과학적 분석 적합성은 확정하지 않는다.
3. 공개 Sentinel COG의 tiled uint8 SCL / uint16 단일 반사도 밴드, 북쪽 위·미터 단위 투영·10/20 m 원본 격자만 지원한다. 품질 자료/실제 파일 NoData 조건이 없거나 다른 제공처·형식이면 미확인/실패다. SAR/Landsat/열환경 처리는 미구현이다.
4. 현재 단일 로컬 서버의 프로세스 내 잠금이다. 다중 서버/멀티워커 분산 제한은 미구현이다. 브라우저 취소 뒤에도 서버가 최대 60초 래스터 한도까지 진행할 수 있다. 처리 한도 내 실패는 재시도 또는 더 작은 AOI 선택이 필요하다.
5. Windows Python 3.13.14 / Rasterio 1.4.4로 실제 실행했다. 새 의존성 Rasterio 및 전이 의존성을 추가하고 lock을 갱신했다. Starlette HTTPX, Rasterio의 NumPy shape/affine 연산/is_tiled 관련 사용 중단 예정 경고 218개와 Node 색상 환경 경고가 남는다. 테스트 실패는 아니며 의존성 호환성 개선은 별도다.
6. A4 지수·변화량·마스크/GeoTIFF 내보내기, A5 Sentinel-1 검색은 **미구현·미실행**이다. 이번 요청에서 시작하지 않았다.

공식 자료를 2026-10-29 직접 확인했다: [Copernicus S2 제품·NoData·보정](https://sentiwiki.copernicus.eu/web/s2-products), [CDSE L2A 밴드](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S2L2A.html), [SCL 분류](https://custom-scripts.sentinel-hub.com/custom-scripts/sentinel-2/scene-classification/), [제공처 offset 이슈](https://github.com/Element84/earth-search/issues/71), [Rasterio window](https://rasterio.readthedocs.io/en/stable/topics/windowed-rw.html), [Rasterio 재투영](https://rasterio.readthedocs.io/en/stable/topics/reproject.html), [Rasterio Python opener](https://rasterio.readthedocs.io/en/stable/topics/vsi.html). 출처·확인일·정책 버전은 코드와 응답에도 저장한다.

## 실제 변경 파일

아래는 위 실제 작업 루트 기준 경로다. 기존 파일은 필요한 부분만 확장했다.

| 파일 | 변경 내용 |
|---|---|
| backend/app/pixel_quality.py (신규) | A2/목적 규칙 재사용, canonical 조회·조건·단일 작업 제한·시간 제한 프로세스 관리 |
| backend/app/pixel_raster.py (신규) | 실제 헤더/window, SCL/NoData, 공통 격자, 유효/제외 면적·분모·보정 근거 |
| backend/app/pixel_policy.py (신규) | 버전별 SCL 정책·운영 상한·공식 출처 |
| backend/app/range_reader.py (신규) | 제한된 HEAD/206 범위 읽기·크기/전송량/시간·요청 상한 |
| backend/app/pixel_worker.py (신규) | 격리된 래스터 처리, 메타데이터/전송 기록 반환 |
| backend/app/models.py | S2 두 날짜 전용 요청·운영 기준 검증 |
| backend/app/main.py | POST /pixel-quality 연결 |
| backend/app/analysis_conditions.py | A2 픽셀 미검사 설명과 A3 실행 안내 |
| backend/app/selection.py | 기하 존재 안내를 A3 QA 상태와 혼동하지 않도록 문구 수정 |
| backend/app/recommendations.py | S2 한정 A3 처리 지원 범위 안내 |
| backend/requirements.txt, backend/requirements-lock.txt | Rasterio·NumPy 선언 및 설치 버전 고정 |
| frontend/src/components/PixelQuality.tsx (신규) | A3 진단 버튼·운영 기준·면적/분모/제외 이유·파일 근거·실패 구분 |
| frontend/src/components/AnalysisConditions.tsx | 기존 기준일 재사용과 A3 연결 |
| frontend/src/components/SceneComparison.tsx | 전후 비교에서 진단 결과 연결·메타데이터 설명 구분 |
| frontend/src/components/Results.tsx | 실제 검사된 장면을 항상 미검사로 표시하던 문구 정리 |
| frontend/src/app/page.tsx | 현재 AOI 장면 QA 상태 연결·빈 화면 안내 |
| frontend/src/lib/types.ts | A3 결과 계약 |
| frontend/src/app/globals.css | 기존 화면에 맞춘 A3 반응형 스타일 |
| backend/tests/test_pixel_quality.py (신규) | 고정 소형 TIFF·공통 면적·사전 조건·실패/한도 검사 |
| backend/tests/test_range_reader.py (신규) | 실제 범위 읽기 프로토콜·상한·timeout·리다이렉트 거부 |
| backend/tests/test_pixel_quality_live.py (신규) | 실제 두 날짜 STAC/COG 범위 읽기 재현 |
| frontend/tests/pixel-quality.spec.ts (신규) | 6개 A3 UI/실제 연결 E2E |
| AGENTS.md, README.md, docs/NEXT_STEPS.md | A3 현재 범위·재현법·정책·제약, A4 이후 계획 유지 |
| TEST_REPORT.md, docs/TEST_REPORT_A2_2026-10-29.md | 최신 실행 근거와 과거 보고서 분리 |

로컬 산출물: backend/logs/a3-live.txt, frontend/test-results/a3-live.png, a3-mobile.png. 자동 생성 빌드/테스트 캐시와 가상환경 설치 파일은 소스 변경 목록과 분리한다.

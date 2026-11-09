# 목적별 탑재체·센서 추천 — 최신 검증

2026-10-29 (Asia/Seoul). 작업 루트: C:\Users\aicam\Documents\ChatGPT\바이브코딩. .git이 없는 기존 프로젝트 폴더다. 기존 앱과 A1 상태 처리를 유지하며 추천 엔진을 확장했다. 배포·푸시·새 인증·유료 API·SAR 연결·래스터 QA 엔진은 수행하지 않았다.

## 최신 소스 수정 이후 실제 실행

| 위치 | 실제 명령 | 종료 코드 | 결과 |
|---|---|---:|---|
| backend | $env:LIVE_STAC='1'; ..\.venv\Scripts\python.exe -m pytest -q | 0 | **72 passed**, 12.87초 |
| frontend | npm.cmd run build | 0 | production Webpack·TypeScript·정적 페이지 생성 완료 |
| frontend | npm.cmd run typecheck | 0 | 빌드 후 별도 tsc --noEmit 통과 |
| frontend | npm.cmd run test:e2e | 0 | **22 passed**, 40.8초, Edge headless |
| 루트 | node scripts/start-local.mjs | 실행 중 | 최종 서버 재시작, /health 200, 127.0.0.1:3000 |

백엔드 72개 중 **6개 실제 외부 연결**, 66개 테스트 전용 메타데이터/전송 계층 검사다. 실제 검사는 컬렉션·원본 Item 대조·페이지네이션·공개 Asset HEAD 및 새 S2 L2A/Landsat 8·9 L2SP 추천 검색이다. 실제 결과의 제품 조건·필수 밴드 존재·검색됨/QA 미검사를 확인했다. 원본 파일 전체 다운로드나 픽셀 처리는 수행하지 않았다.

E2E의 search.spec.ts 지도 검색 및 sensor-recommendations.spec.ts 카드 검색은 실제 STAC 연결이다. 카드 추천은 실제 로컬 API를 사용한다. 오류/0건/timeout/지연/정확한 링크 파일 내용 검사는 테스트 fixture를 쓴다. 카드 가용성 UI 검사는 실제 추천 응답의 가용성 필드만 테스트용으로 바꾼다. 실제 가용성 계산은 백엔드 별도 검사로 검증한다. 서비스에 fixture 대체 경로는 없다.

최종 두 실제 검색 E2E의 HTTP 오류 URL 목록은 []였다. 합성 504는 의도한 /api/search 실패다. 과거 원인 불명 404가 일반적으로 해결됐다고 주장하지 않는다. Starlette TestClient의 httpx 사용 중단 예정 경고 1개 및 Node NO_COLOR/FORCE_COLOR 경고는 남아 있다.

화면 산출물: frontend/test-results/sensor-desktop.png, sensor-mobile.png, live-map.png, live-search.png, a1-mobile.png. 새 데스크톱 두 카드와 모바일 한 열 화면을 직접 확인했으며 가로 넘침·잘린 버튼이 없었다. 다음 E2E 실행 시 산출물은 갱신된다.

## 구현 상태 및 한계

- 구현: 기존 purpose_plan.RULES를 목적·필수 밴드·프로필 규칙의 단일 원천으로 확장했다. 데이터 전용 sensor_catalog.py를 기존 recommendations.py가 사용하며 프론트에 추천 규칙을 복제하지 않았다. 동일 입력은 동일 추천이며 추천 시 웹/LLM 호출이 없다.
- 구현: 관측 방식, 탑재체, 플랫폼, 제품/컬렉션, 필수 밴드, 품질 자료, 원관측/출력 격자, 제약, 근거/확인일/버전 카드. 대상 크기/시점/구름·야간 선택 입력과 누락 가정 표시. 모호한 목적은 기존 직접 선택으로 확인한다.
- 식생·녹지/도시: MSI 및 OLI/OLI-2 지표반사도. 홍수·장마: SAR 우선이나 버튼 미지원, 광학은 맑은 시기 조건부 보완. 구름 중/야간 필수면 광학 검색 버튼도 비활성이다.
- 열환경: L8 TIRS / L9 TIRS-2 L2SP ST_B10만 직접 후보로 추천한다. S2 직접 LST 추천 금지. 100 m 원관측과 30 m 재표본화 출력, 지표온도와 기온 구별. 해당 ST 제품은 야간 요구를 충족하지 않는다.
- 구현: 카드 검색은 AOI·기간을 보존하고 연결된 컬렉션·플랫폼·제품 수준·필수 밴드 메타데이터 조건을 적용한다. 제외 수 filtered를 표시하고 제외 후보로 소모되지 않은 반환 몫은 다음 페이지에서 사용한다. A1 요청/시간 상한·부분 실패·복합 ID 중복 처리를 유지했다.
- 독립 상태: 목적 관측 조건 met/conditional/not_met, 앱 검색/처리/다운로드 지원, 가용성 unsearched/searched/none/failed, 선택 장면 QA not_checked. 미조회/실패 0건을 영상 없음으로 확정하지 않는다. 실제 일부 후보가 있으면 검색됨과 미완료 안내를 함께 표시한다.
- 회귀: 그룹별 페이지, 비교·전후 모드, 밴드 선택/전체/복원/시각화, 실제 저장된 txt 내용, 모바일, 목적/기간/AOI/위성/한도/새 선택 입력 3종 변경 중 오래된 응답 차단 검사를 통과했다.
- 미구현·미실행: 실제 래스터 QA, 공통 격자/유효 픽셀 검사, SAR 수집·처리, 변화 분석. 추천 조건 충족은 픽셀 분석 가능 판정이 아니다. Asset 링크는 접근·인증·다운로드 보장이 아니다. 직접 컬렉션 검색은 참고 후보를 포함하며 이 가정을 표시한다. A2~A5 전체는 후속 계획이다.

## 규칙·공식 근거

규칙 **sensor-purpose-2026-10-29.1**, 확인일 **2026-10-29**. 이번 작업에서 아래 자료를 직접 확인했고 URL·확인일·사양·제약을 카탈로그와 카드에 보존한다.

- [ESA MSI](https://www.esa.int/Applications/Observing_the_Earth/Copernicus/Sentinel-2/Facts_and_figures), [Copernicus L2A 밴드](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S2L2A.html).
- [ESA C-SAR](https://www.esa.int/Applications/Observing_the_Earth/Copernicus/Sentinel-1/Instrument), [Copernicus SAR 제품](https://sentiwiki.copernicus.eu/web/s1-products). IW 관측 사양과 아직 연결하지 않은 GRD 출력 격자를 구별한다.
- [USGS Landsat 8 OLI/TIRS](https://www.usgs.gov/landsat-missions/landsat-8), [NASA Landsat 9 OLI-2/TIRS-2 PDF](https://www.nasa.gov/wp-content/uploads/2015/04/landsat_9_fast_facts.pdf).
- [USGS EROS Level-2/ST·야간 제약](https://www.usgs.gov/centers/eros/science/usgs-eros-archive-landsat-archives-landsat-8-9-olitirs-collection-2-level-2), [USGS ST](https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature), [USGS Level-2](https://www.usgs.gov/landsat-missions/landsat-collection-2-level-2-science-products).

USGS ST 페이지 일부 웹 도구 요청은 timeout이었으나 직접 HTTP 요청은 200이었다. 구체적 제품/야간 제약은 접근 가능한 USGS EROS 본문으로 확인했다. 대상 폭이 필수 밴드 최대 원관측 간격의 3배 미만이면 조건부로 안내하는 것은 **앱 운영 가정**이며 공식/보편적 식별 기준이 아니다. 한 픽셀을 객체 식별 크기로 단정하지 않는다.

## 실제 변경 파일

모두 작업 루트 기준. 읽은 시작 경로 중 metadata.py, MapPanel.tsx는 재사용하며 이번에는 수정하지 않았다. 패키지 의존성도 추가하지 않았다.

| 경로 | 변경 |
|---|---|
| backend/app/sensor_catalog.py | 신규 공식 사양 데이터 |
| backend/app/purpose_plan.py | 공통 목적·제품·밴드 규칙 확장 |
| backend/app/recommendations.py | 기존 엔진의 카드·가정·상태 |
| backend/app/purposes.py | 녹지·장마 키워드 |
| backend/app/models.py | 선택 입력·추천 ID 검증 |
| backend/app/main.py | 추천 조건 검색·가용성 연결 |
| backend/app/stac.py | 제외 수·할당량 보존 |
| backend/app/evaluation.py | 장면 QA 미검사 |
| frontend/src/components/SensorRecommendations.tsx | 신규 추천 카드 |
| frontend/src/app/page.tsx | 선택 입력·카드 검색·상태 연결 |
| frontend/src/lib/types.ts | 카드/상태 계약 |
| frontend/src/app/globals.css | 반응형 카드 스타일 |
| frontend/src/components/Results.tsx | 제품 조건·QA·제외 수 |
| frontend/src/components/SceneComparison.tsx | 선택 장면 QA 표시 |
| frontend/src/components/AssetDownloads.tsx | 공통 규칙 버전 |
| backend/tests/test_sensor_recommendations.py | 신규 결정론·누락·입력·상태·필터/다음 페이지 |
| backend/tests/test_purpose_plan.py | 제품 fixture와 명시적 참고 검색 회귀 |
| backend/tests/test_live.py | 실제 추천 검색 2개 추가 |
| frontend/tests/sensor-recommendations.spec.ts | 신규 카드 API/검색·입력 보존·상태·모바일 |
| frontend/tests/reliability.spec.ts | 선택 입력 3종 경합 추가 |
| README.md, AGENTS.md, docs/NEXT_STEPS.md | 사용법·단일 원천·범위·한계 |
| TEST_REPORT.md | 이번 최신 실행 |
| docs/TEST_REPORT_A1_2026-10-29.md | 직전 A1 보고서 원문 보관 |

.next, tsconfig.tsbuildinfo, public/maplibre-worker.js, test-results는 빌드/테스트 생성물이며 소스 구현과 구분한다.

## 중간 실패 / 재실행

- 초기 pytest 종료 **1**, **2 failed / 45 passed / 4 skipped**. 이전 열환경 fixture에 플랫폼/제품 수준이 없었고 이전 자동 검색 검사는 S2 포함을 기대했다. fixture를 보완하고 두 컬렉션 할당량 검사를 명시적 수동 참고 검색으로 바꿨다. 요구대로 열환경 자동 추천은 Landsat ST만 유지했다.
- 수정 후 네트워크 비활성 pytest 종료 **0**, **65 passed / 4 skipped**. 실제 추천 검색 2개 추가 후 LIVE_STAC **71 passed**(종료 0). 필터된 빈 페이지의 다음 페이지 검사 추가 후 최종 **72 passed**다.
- 첫 확장 E2E 종료 **0**, **19 passed**, 36.4초. 선택 입력 경합 3개 추가 후 최종 **22 passed**로 다시 실행했다.
- 초기/최종 독립 typecheck 모두 종료 0. 최종 build 종료 0. 위 표는 최신 소스 변경 이후 실행 결과다.
- 소유 launcher를 빌드 전 Ctrl+C로 중단한 종료 코드 1은 의도한 서버 종료다. 다른 프로그램을 종료하지 않았다.

## 재현 및 과거 이력

1. 루트에서 launcher 실행 후 목적 녹지 변화, 충남 예시 AOI, 2025-07-01~31을 입력한다. MSI/OLI 카드는 미검색·미검사다.
2. MSI의 이 조건으로 검색: 같은 AOI·기간, L2A 제품 조건의 실제 후보를 반환한다. red/nir 및 시각화/제공된 품질 밴드 기본 선택은 공통 규칙에서 결정된다.
3. 침수는 SAR 미지원/광학 조건부, 구름 중 필수는 광학 버튼 비활성, 열환경은 TIRS/TIRS-2 L2SP 카드 하나를 확인한다.
4. 위 표 명령을 각 폴더에서 실행한다. LIVE_STAC 미지정 시 외부 연결 검사는 skip이다. E2E 실제 검색은 fixture로 자동 대체하지 않는다. 테스트 txt의 합성 URL은 실제 다운로드 가능성 증거가 아니다.

직전 A1의 **51 pytest / 14 E2E**는 [과거 A1 원문](docs/TEST_REPORT_A1_2026-10-29.md)에 보관했다. 더 이전 33 pytest / 3 E2E 등은 그 문서의 이력 링크를 따른다. 이번 완료 근거는 최신 **72 pytest / 22 E2E / 독립 typecheck / build**다. A2~A5 전체 구현·검증은 수행하지 않았다.

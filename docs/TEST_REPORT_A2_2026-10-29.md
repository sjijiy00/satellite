# A2 두 영상 분석 조건 검사 — 최신 검증 보고서

검증일 2026-10-29 (Asia/Seoul). 작업 루트 C:\Users\aicam\Documents\ChatGPT\바이브코딩. Git 저장소가 아닌 기존 프로젝트 폴더이며 사용자 기존 코드를 이어서 수정했다. **A2만 구현했고 A3~A5는 착수하지 않았다.** 배포·푸시·새 인증·지속 접근·유료 API는 수행하지 않았다.

## 시작 상태 및 재사용

AGENTS.md, frontend/AGENTS.md, 최신 README/TEST_REPORT, docs/NEXT_STEPS, 패키지·테스트 설정, 현재 API/모델/정규화/목적 규칙/선택·면적 함수/비교 UI를 확인했다. Next.js 설치본의 use-client 문서도 읽었다. 수정 전 새 pytest 결과는 **66 passed / 6 skipped**, 종료 0, 4.20초였다. 과거 72/22 결과를 현재 성공으로 재사용하지 않았다.

기존 purpose_plan의 필수 밴드 선택, sensor_catalog의 제품·품질 정보, 정규화, LAEA 중첩 계산, 센서/전후 선택, 복합 Item ID를 재사용했다. 추천 엔진이나 검색 부분 실패 모델을 다시 만들지 않았다.

## 최종 수정 이후 실제 실행

| 위치 | 명령 | 종료 코드 | 결과 |
|---|---|---:|---|
| backend | $env:LIVE_STAC='1'; ..\.venv\Scripts\python.exe -m pytest -q | 0 | **108 passed**, 19.78초 |
| frontend | npm.cmd run build | 0 | production Webpack 빌드·TypeScript·정적 생성 완료 |
| frontend | npm.cmd run typecheck | 0 | 빌드와 독립된 tsc --noEmit 통과 |
| frontend | npm.cmd run test:e2e | 0 | **27 passed**, 54.1초, Edge headless |
| 루트 | node scripts/start-local.mjs | 실행 중 | 최신 서버 재시작, /health 200, http://127.0.0.1:3000 |

백엔드 **101개 합성/단위 검사 + 7개 실제 외부 연결 검사**다. 새 A2 합성 검사는 35개이며 실제 A2 검사는 원본 STAC Item 재조회·S2 필수/품질 자료·공개 red Asset HEAD·격자 메타데이터·공통 면적·픽셀 미검사 상태를 확인한다. 기존 6개 실시간 검색/Item 대조/페이지네이션/Asset HEAD 검사도 다시 실행했다.

새 E2E 5개 중 하나는 실제 추천→검색→두 영상 선택→기준일→A2 API→실제 HEAD 연결을 확인한다. 나머지 4개는 테스트 전용 검색/조건 응답으로 기준일 전달·입력 보존·선택 변경 초기화·늦은 응답 폐기·잘못된 기준일·API timeout·모바일을 확인한다. 기존 22개도 재실행해 부분 실패/0건/timeout, 그룹 페이지, 비교 변경, 밴드 전체 선택·복원, 저장된 링크 txt의 정확한 내용, 검색 중 조건 변경, 모바일 회귀를 확인했다. fixture는 tests 전용이며 서비스에 가짜 결과 대체 경로가 없다.

실제 A2 E2E의 HTTP 오류/페이지 오류 목록은 빈 배열임을 단언했다. 기존 실제 검색 E2E도 HTTP 오류 목록 []를 출력했다. 주입한 504는 테스트용 /api/analysis-conditions 또는 /api/search 오류다. 과거 원인 불명 404의 일반적 해결을 주장하지 않는다.

## 구현 내용과 판정의 범위

- 새 POST /analysis-conditions는 기존 검색 AOI·기간·목적, 두 컬렉션/Item ID와 선택 기준일을 받는다. 클라이언트가 보낸 Asset URL/geometry로 원격 접근하지 않고 고정된 Earth Search에서 원본 Item을 다시 조회한다.
- 기준일은 UTC 00:00이다. 영상1 촬영일 < 기준일 ≤ 영상2 촬영일, 두 촬영일의 검색 기간 포함, 동일 Item/동일 시각/역전, 센서·컬렉션·제품 일치 여부를 검사한다. 기준일 미입력 또는 날짜 정보 부족은 미확인이다. 같은 센서 계열의 서로 다른 플랫폼은 교차 보정·관측 조건 추가 검토를 안내한다.
- 기존 필수 밴드·제품 규칙을 사용한다. 카탈로그에 실제 품질 Asset 키를 추가해 S2 SCL, Landsat QA_PIXEL/QA_RADSAT, 열환경 ST_QA(Earth Search 키 qa)를 확인한다. 품질 자료 존재와 품질 마스크 적용은 별개다.
- 공개 Asset HTTP HEAD 접근 응답을 확인한다. 401/403/404/410은 현재 접근 불가, timeout/리다이렉트/HEAD 미지원/비래스터 응답/요청자 비용/서명 URL 등은 미확인이다. 파일 본문·래스터 헤더·픽셀은 읽지 않았다. HEAD 200은 파일 무결성이나 다운로드 성공 보장이 아니다.
- CRS·shape·transform은 STAC 메타데이터와 필드별 출처를 표시한다. Asset/단일 raster band가 Item 기본값에 우선하고 명시적 null도 보존한다. 누락 CRS를 타일 이름/위치로 추정하지 않는다. transform에서 계산한 격자 간격·extent는 CRS 단위로 표시하며 항상 미터로 간주하지 않는다. 다중 밴드별 서로 다른 격자를 단일 격자로 추정하지 않는다. 격자 차이는 조건부/정합 필요, 누락·잘못된 값은 미확인이다.
- AOI∩각 footprint의 개별 중첩률과 AOI∩두 footprint의 공통 촬영 면적·AOI 대비 비율을 구분한다. 기존 AOI 중심 LAEA 등적 투영과 경계 0.02도 세분화를 재사용한다. 양의 면적 공통 영역 없음은 0, geometry 누락/실패는 null이다. 공통 geometry도 API 응답 근거로 제공한다.
- 각 항목에 통과/조건부/미확인/불가, 이유, 다음 행동, 근거를 제공한다. 요약은 조건부/미확인/불가이며 **분석 가능 확정 판정은 보류**한다. 픽셀 품질은 항상 미검사다.
- 전후 비교 모드에 A2 패널을 추가했다. 검사 중 기준일·영상 변경이나 부모 검색 입력 변경 시 이전 결과를 폐기하고 늦은 응답도 덮어쓰지 않는다. 기존 추천/비교/다운로드 UI는 유지했다.

실제 브라우저 사례에서 개별 AOI 중첩은 약 **46.937%, 74.911%**, 공통 촬영 영역은 **21.848%**, 공통 기하 면적은 약 **542,668,748 m²**였다. 이것은 해당 선택 쌍의 footprint 계산 사례이며 구름 없는 공통 유효 면적이 아니다. 반사도/SCL 격자 차이는 조건부로 표시됐다.

화면 검증 파일: frontend/test-results/a2-live.png (실제 API 결과), frontend/test-results/a2-mobile.png (명시적인 TEST ONLY 응답). 두 이미지를 직접 확인했다. 모바일 가로 넘침 검사를 통과했다. 다음 E2E 실행 시 산출물은 갱신된다.

## 제한과 미해결 사항

- **파일 헤더·픽셀 미검사**. CRS/격자는 STAC 증거이며 파일 실제 헤더와 일치하는지 확인하지 않았다. 누락값은 미확인으로 남긴다. A3 픽셀 QA, 정합·공통 유효율, 변화 분석은 미구현·미실행이다.
- HEAD 성공은 HTTP 접근 응답만 의미한다. 인증·비용 동의·계정 생성·서명 발급·전체 다운로드·리다이렉트 추적은 하지 않는다. 현재 실시간으로 확인한 Landsat Asset은 requester_pays=true라 자동 접근을 생략한다. 접근 정책 해소나 다른 공개 자료 선택은 후속 사용자 결정이다.
- 허용 호스트는 sentinel-cogs.s3.us-west-2.amazonaws.com, landsatlook.usgs.gov, usgs-landsat.s3.us-west-2.amazonaws.com이다. 이 범위 밖 공개 링크도 A2 자동 접근은 미확인이다. URL 쿼리·자격증명은 접근하거나 검사 근거에 저장하지 않는다.
- 검사당 원본 Item 2개 포함 최대 14회 요청, 총 네트워크 45초, 요청당 8초, Item 본문 2 MB 상한. 검사 내 순차 요청, 자동 재시도 없음. 상한/오류는 미확인이고 0%가 아니다. 로컬 JSON·기하 계산 시간은 별도다.
- 장면 footprint는 밴드별 실제 유효 촬영 영역이나 구름 마스크가 아니다. 센서·제품 동일/기하 통과/HEAD 통과를 과학적 적합성 또는 픽셀 QA 통과로 해석하지 않는다.
- STAC Projection Extension 공식 문서 https://github.com/stac-extensions/projection 와 HTTPX 공식 async 문서를 2026-10-29 확인했다. Item/Asset 기본값·shape 순서·transform·CRS 단위 해석에 반영했다. 래스터 파일 헤더를 읽었다는 근거는 생성하지 않는다.
- Starlette TestClient httpx 사용 중단 예정 경고 1개와 Node NO_COLOR/FORCE_COLOR 경고가 남아 있다. 의존성을 새로 추가하거나 교체하지 않았다.

## 실제 변경 파일

경로는 작업 루트 기준이다.

| 파일 | 변경 |
|---|---|
| backend/app/analysis_conditions.py | 신규 A2 원본 조회·조건 판정·공개 HEAD·제한 |
| backend/app/grid_metadata.py | 신규 STAC 격자·CRS 메타데이터 해석 |
| backend/app/models.py | ItemReference / ConditionsRequest와 기준일 검증 |
| backend/app/main.py | A2 API 연결 |
| backend/app/evaluation.py | 기존 LAEA 면적 함수를 공통 재사용 함수로 분리 |
| backend/app/selection.py | 개별/공통 촬영 면적·비율·geometry; A1 존재 검사 유지 |
| backend/app/sensor_catalog.py | 기존 품질 자료의 실제 Asset 키 매핑 |
| frontend/src/components/AnalysisConditions.tsx | 신규 기준일·검사 항목·근거·상태 UI |
| frontend/src/components/SceneComparison.tsx | 전후 모드에서 A2 패널 연결 |
| frontend/src/lib/types.ts | A2 응답 타입 |
| frontend/src/app/globals.css | 기존 UI에 맞춘 반응형 A2 스타일 |
| backend/tests/test_analysis_conditions.py | 신규 35개 합성 조건/접근/기하/격자 검사 |
| backend/tests/test_live.py | 실제 A2 원본/HEAD 검사 추가 |
| frontend/tests/analysis-conditions.spec.ts | 신규 A2 E2E 5개 |
| README.md, AGENTS.md, docs/NEXT_STEPS.md | A2 사용법·범위·A3 이후 미착수 갱신 |
| TEST_REPORT.md | 이번 최신 결과 |
| docs/TEST_REPORT_SENSORS_2026-10-29.md | 직전 센서 추천 보고서 원문 보관 |

기존 recommendations.py, purpose_plan.py, stac.py, 다운로드 선택 기능과 부분 실패 상태 모델은 재사용했다. .next / tsconfig.tsbuildinfo / public/maplibre-worker.js / test-results는 빌드·테스트 생성물이다.

## 실행 이력 및 재현

- 수정 전 기본 pytest: 종료 0, 66 passed / 6 skipped, 4.20초.
- A2 최초 합성 검증: 종료 0, 99 passed / 7 skipped, 7.91초.
- 최초 전체 실제 연결 검증: 종료 0, 106 passed, 20.00초.
- 최초 전체 E2E: 종료 0, 27 passed, 55.7초.
- Landsat ST_QA 키 및 격자 우선순위 추가 검증 후 최종 전체: 위 표의 108 passed / 27 passed, build/typecheck 종료 0. 이번 작업에서 실패한 테스트는 없다.
- 소유한 launcher를 빌드/재시작 전 Ctrl+C로 종료한 코드 1은 의도한 서버 종료다. 다른 프로그램은 종료하지 않았다.

재현: 서버를 실행하고 식생 변화 → 충남 예시 AOI → 2025-07-01~31 → MSI 카드 검색 → 전후 변화용 영상 선택 → 서로 다른 날짜 두 영상 → 그 사이 UTC 기준일 → 두 영상 조건 검사 순서로 진행한다. 검사 근거를 펼치면 Item URL·HTTP 상태·격자 필드 출처를 확인할 수 있다. 중복/역전/기준일 밖/CRS 누락 등은 새 백엔드 테스트로 결정론적으로 재현하며 실제 제공처 결과를 가짜로 대체하지 않는다.

## 과거 기록

직전 센서 추천의 72 pytest / 22 E2E 기록은 [센서 추천 원문](docs/TEST_REPORT_SENSORS_2026-10-29.md), A1은 [A1 원문](docs/TEST_REPORT_A1_2026-10-29.md)에 보관했다. 이번 완료 증거는 위 최신 실행이며 과거 수치를 재사용하지 않았다. **A2 종료 후 멈추며 A3 이후를 자동 진행하지 않는다.**

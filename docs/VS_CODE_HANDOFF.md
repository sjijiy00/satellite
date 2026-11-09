# VS Code 개발 인수인계

## 현재 인계 — GPT-4o 적용 (2026-11-02)

- VS Code에서 이 폴더 `C:\Users\aicam\Documents\ChatGPT\바이브코딩`을 열면 현재 수정된 코드와 설정을 그대로 사용한다. 별도 프로젝트 복사본이나 VS Code 전용 AI 설정은 만들지 않았다.
- 사이트의 자연어 조건 해석 모델은 서버 전용 `backend/.env`의 `AI_NL_MODEL=gpt-4o`다. 새 환경 파일 예시는 `backend/.env.example`, 신규 설정 도구 기본값은 `scripts/configure-server-env.mjs`를 따른다. `OPENAI_API_KEY`는 서버에만 남겨두고 `.vscode/settings.json`, 프런트 환경 변수, `NEXT_PUBLIC_*`에는 넣지 않는다.
- 사용자 확인 후 이 프로젝트의 기존 3000/8000 서버만 재시작했다. 현재 `GET http://127.0.0.1:8000/request/config`는 `ready=true`, `model=gpt-4o`를 보고하고 프런트 `GET http://127.0.0.1:3000/api/health`는 `phase=1`이다. 이는 설정 인식이며 실제 OpenAI 응답 성공/추출 품질의 검증은 아니다.
- 기존 Responses API의 strict JSON schema는 유지한다. GPT-4o 요청에는 이전 `gpt-5.6-luna` 전용 `reasoning.effort=none`을 보내지 않는다. 테스트: `.venv\Scripts\python.exe -m pytest -q backend/tests/test_ai_interpretation.py backend/tests/test_ai_primary.py` → 50 passed; 작업 폴더 안으로 `TEMP`/`TMP`를 지정한 `node --test scripts/server-env.test.mjs` → 16 passed. 상세 실패·미실행·재시작 이력은 `TEST_REPORT.md`의 GPT-4o 절을 따른다.
- GPT-4o는 공식 문서상 deprecated이고 이전 모델보다 비용이 높다(입력/출력 백만 토큰당 $2.50/$10.00). 상태 화면의 비용은 사용량 기반 추정치이며 실제 청구액은 OpenAI 계정에서 확인한다. [GPT-4o 공식 모델 문서](https://developers.openai.com/api/docs/models/gpt-4o).
- 아래 2026-10-30 인계의 모델·서버 PID·제공처 수·지원 범위는 당시 기록이다. 현재 상태는 최신 README와 TEST_REPORT를 우선한다.

---

## 최신 인계 — 현재 웹 3000/8000에 다중 제공처 반영 (2026-10-30)

- 이전 서버는 health 200이지만 `/catalog`·`/api/catalog` 404로 구버전이었다. 프로세스 경로/부모 트리를 확인하고, 전체 작업 목록을 조회할 수 없어 사용자에게 먼저 확인했다. 사용자가 “진행 중인 작업 없음 — 프로젝트 재시작 진행”으로 답한 뒤 프로젝트 런처 17560의 트리만 종료하고 루트 `.\start.cmd`로 재시작했다.
- 현재 http://127.0.0.1:3000/ 에서 최신 코드 실행 중. 런처 43896, backend 43852(8000), frontend 37084(3000). 두 catalog 200·제공처 3/컬렉션 4, 양쪽 health 200. 다른 앱/IDE/환경 파일은 변경하지 않았다.
- 기존 검색을 재사용했다. 카드 선택→수동 컬렉션 동기화, 이후 수동 방식/checkbox 수정→카드 해제. 버튼 위 예상 최종 컬렉션과 결과의 서버 최종 컬렉션/추천 조건/AOI를 표시한다. 새 검색·분석 엔진은 없음.
- 지정한 UTC 2025-07-20~26 / bbox 126.7,36.4,126.71,36.41에서 카드/수동 각각 S1 1건·VIIRS 7건·S2 2건. 전부 기간 내·기하 중첩 100%이나 픽셀 QA/파일 접근 성공을 뜻하지 않는다. S1/VIIRS 인증 원본은 직접 링크가 없으며 다운로드하지 않았다. VIIRS는 일별 지표반사도·QA/NDVI 미지원이다.
- CMR가 추가 동시 검색 1회 timeout으로 부분 실패, 단독 카드 1회 504를 반환한 기록도 남겼다. 실제 검색 8건의 수동 재검증은 통과했고 마지막 SAR 관측 시간 설명 수정 후 6건도 통과했다. 최신 TEST_REPORT의 명령/실패/검증 경계를 따르며 과거 전체 통과를 이번 근거로 재사용하지 않는다.
- OpenAI 실제 요청 0, 픽셀 처리/분석·자동 원본 다운로드·Supabase·새 키 설정·배포·push 없음. 서버는 종료하지 않고 계속 실행한다. Python 자동 reload는 없으며 이후 수정 시 활성 작업을 확인한 후 프로젝트만 재시작해야 한다.

---

## 최신 인계 — 다중 제공처 실제 검색 (2026-10-30)

- 이 절과 최신 TEST_REPORT가 과거 “SAR 미연결” 기록보다 우선한다. 기존 Earth Search·Next/MapLibre·FastAPI·S2 A2–A4/관측 합성/ML을 유지했다.
- Copernicus 현재 STAC `sentinel-1-grd`, NASA CMR `VNP09GA.002` Suomi NPP VIIRS 실제 AOI/UTC 기간 검색을 연결했다. 새 제품은 검색·메타데이터만 지원하며 원본은 CDSE 인증/Earthdata Login이 필요하다.
- `provider_registry.py`의 플랫폼/센서/제품/제공처/컬렉션 등록, `sensor_catalog.py`의 사양, `purpose_plan.py`의 단일 목적 규칙을 따른다. CMR/사양을 AI가 생성하지 않는다. NOAA는 위성명이 아니다.
- Scene/선택/비교/지도 키는 제공처+컬렉션+Item이다. 어댑터별 부분 실패·조회 상한·기간 밖 필터를 보존하고 인증 파일은 직접 링크 목록에서 제외한다. `GET /catalog`와 `/catalog/discover/{provider}`는 읽기 전용 등록/공식 컬렉션 발견이며 미검토 컬렉션을 자동 연결하지 않는다.
- NOAA NODD/GK2A/NOAA-20·21 VIIRS/HLS/SLSTR는 미연결 후보다. [다중 제공처 문서](MULTI_PROVIDER_SEARCH.md)에 공식 근거·권한 표·후속 환경변수 이름·범위 한계를 기록했다. 기존 비밀 `.env`는 읽거나 수정하지 않았다.
- 이번 검증은 별도 3013/8013 서버에서 수행하며 기존 3000/8000 서버를 종료하지 않는다. 최종 테스트 결과와 실행 종료 여부는 최신 TEST_REPORT를 따른다. 기존 8000은 새 코드를 자동 재로딩하지 않으므로 새 코드 사용은 해당 프로젝트 실행 창을 사용자가 재시작해야 한다. 배포·push 없음.

---

## 최신 인계 — OpenAI 서버 설정 인식 완료 (2026-10-30)

- 사용자가 기존 자격증명의 지속 사용·설정 적용·프로젝트 재시작을 승인했다. 키가 든 기존 `backend/.env.example` 파일 자체를 `backend/.env`로 이름 변경하고 비밀 없는 예시를 재생성했다. 키 값은 재인용/다른 파일 복사하지 않는다.
- 서버 로더는 `backend/.env` 하나만 읽고 기존 프로세스 설정을 우선한다. 프런트·지도 worker·독립 build에는 OpenAI/AI_NL 설정을 전달하지 않는다. `scripts/server-env.mjs`, `start-local.mjs`, `frontend-check.mjs`를 따른다. 다른 파일 변수를 임의로 주입하지 않는다.
- 일반 설정은 enabled=1/provider=openai/model=gpt-5.6-luna다. 사용자가 이미 지정한 모델은 보존하는 도구이며 이번에는 기존 모델이 비어 있어 선정값을 적용했다. 공식 Responses·Structured Outputs 지원 비용 지향 모델이고 이 모델에는 reasoning none을 사용한다.
- 작업 상태와 프로젝트 프로세스 경로/부모 관계를 확인하고 이 프로젝트만 재시작했다. 3000 루트·프록시 health·8000 health 모두 200, 양쪽 request/config는 ready=true/openai/gpt-5.6-luna/누락 없음이다. 브라우저를 새로고침하면 설정을 인식한다.
- **설정 인식 성공이며 실제 계정 접근·모델 응답 성공은 미검증**이다. 이번 작업의 OpenAI 실제 요청 0회. 유료 검증은 설정 적용 승인에 포함되지 않으며 한 문장 1회 최소안도 별도 승인 전 실행하지 않는다.
- Node 모의 설정 테스트 12건, backend 253 passed/12 skipped, 독립 typecheck/build 종료 0. 이전 87 E2E를 이번 설정 변경의 재실행으로 재사용하지 않는다. 최신 TEST_REPORT 및 [설정 안내](AI_NATURAL_INPUT.md)를 따른다.
- 첫 읽기에서 예시 파일의 키가 도구 출력에 포함되는 실수가 있었다. 값을 재인용하거나 파일/보고서/테스트로 복사하지 않는다. 키 재요청·재발급을 요구하지 않는다. 후속 비밀 설정 확인에는 존재 여부만 사용한다.

---

## 최신 인계 — 자연어 해석·카메라/AOI 분리 (2026-10-29)

이 절이 아래 날짜·지역 자동입력 및 사용자 흐름 기록보다 우선한다. 현재 지명은 **지도 카메라 전용**이며 AOI/좌표를 만들지 않는다. `영천군의 2025년 8월 식생상태 확인`은 2025-08-01~31과 영천시 참고 위치로 카메라 이동을 제공한다. 영천군의 역사적 의미와 현재 영천시 화면 참고 한계를 안내한다.

- AOI는 지도 두 꼭짓점 지정 후 `분석 AOI 확정`, 또는 좌표 입력 후 `좌표 적용`으로 직접 확정한다. 수동 좌표 변경은 확정을 해제한다. 새 지명이 기존 AOI와 다를 수 있으면 기존 좌표를 보존하고 유지/새 선택을 확인한다. 카메라만 이동해도 검색 조건/기존 결과는 바뀌지 않는다.
- 무료 규칙 해석은 debounce/blur/IME 보호를 유지한다. OpenAI는 별도 명시 버튼에서만 서버에 요청한다. 제공처는 사용자 지정 OpenAI, 모델/키는 현재 미설정이다. 실제 API 연결을 완료했다고 설명하지 않는다.
- `ai_interpretation.py`의 strict 추출 스키마·원문 근거/달력 재검증·12초/분당6회/프로세스100회/동시1회/10분 캐시와 실패·취소·사용량 구분을 유지한다. AI에 좌표/사양/품질/가용성을 생성시키거나 코드를 실행시키지 않는다. 기존 추천/검색/분석 엔진을 재사용했다.
- API는 기존 interpret 요청에 `interpretation_mode`, 제안에 `engine/extraction`, 지명에 `role=camera_only/view_bbox`를 추가했다. 옛 `region.bbox` 응답은 적용하지 않고 재시작을 안내한다. 별도 `GET /request/config`는 비밀값 없는 준비/사용량 정보다.
- 최종 검증 후 이 프로젝트의 로컬 런처를 최신 코드로 재시작했다. 3000→8000 일반 프록시에서 영천군 예시와 `.3` 응답을 확인했으며 검증용 8011은 종료했다. 현재 브라우저는 새로고침하면 된다.
- [설정·자료 출처·검증 범위](AI_NATURAL_INPUT.md)를 읽는다. OpenAI 키·모델은 사용자가 서버 실행 창에서 직접 설정한다. `backend/.env.example`은 안내용이며 자동 로드하지 않는다. 최신 실행 결과는 TEST_REPORT 맨 위를 따른다.

---

## 최신 인계 — 선택 영상에 따른 다음 작업 흐름 (2026-10-29)

이 절과 최신 TEST_REPORT가 아래 기록보다 우선한다. 기존 Next.js·MapLibre·FastAPI와 날짜/AOI 자동입력·검색·추천·비교·밴드/원본 링크·A3/A4·관측 합성·ML 엔진을 재사용했다. 새 앱·분석 엔진·Supabase·유료 API는 추가하지 않았다.

- 추천 카드에서는 제품만 고르고 추천 아래 하나의 검색 버튼을 사용한다. 결과에서 선택된 장면의 `다음 작업`으로 원본 확인/다운로드, 비교, 실제 지원되는 QA/분석을 연결한다.
- 검색 전에는 후속 요청/ML이 나타나지 않는다. 후속 요청은 선택 이후 접힌 `다른 작업 요청`에서만 표시하며, 지원되는 검색·비교·지도 이동·구름 안내를 기존 상태/API로 연결한다. 미지원 의도는 실행하지 않고 원래 목적을 유지한다.
- 품질 해결은 사용자 요청 또는 실제 AOI 저하 때 표시한다. 동일 기간 대체 관측을 확인한 뒤 관측 합성 계획, 확인된 잔여 결측이 있을 때 접힌 실험적 ML 순서다. ML 진입에 합성 실행 완료를 요구하지는 않지만 원본 픽셀을 검사한 합성 계획의 근거와 별도 ML 검증/확인이 필요하다.
- 비교 쌍을 page.tsx의 단일 상태로 옮겼다. 목적·AOI·UTC 기간·선택·비교 쌍 변경은 오래된 계획/확인/지도 레이어를 지우고 진행 중 작업을 취소한다. 늦게 도착한 작업 시작 응답도 취소한다.
- 식생 한 시점 S2 조건에서만 합성/ML, 식생 두 날짜 S2에서 A4 NDVI, 지원되는 S2 쌍에서 A3를 제공한다. 홍수의 SAR 미연결·열환경의 앱 내 온도 분석 미지원은 계속 명시한다. Sentinel-2를 지표온도 대안으로 제시하지 않는다.
- 실행 결과와 변경 파일/검증 한계는 TEST_REPORT 맨 위를 따른다. 사용자가 실행 중인 3000/8000 프로세스는 유지했다. 기존 8000이 옛 코드를 메모리에 유지하므로 기존 실행 창을 종료하고 `start.cmd`로 재시작해야 새 해석 응답을 읽는다.

---

## 최신 인계 — 자연어 날짜·관심지역 자동입력 (2026-10-29)

이 절과 최신 TEST_REPORT가 아래 14:53 및 12:00 기록보다 우선한다. 날짜·지역 자동입력은 이제 구현되어 있다. 기존 검색·지도·QA·A4·관측 합성·선택형 ML 추정은 재사용했으며 Supabase·새 분석 엔진을 추가하지 않았다.

- `request_interpretation.py`/`models.py`에 선택형 `resolve_conditions` 제안을 연결하고 `condition_proposals.py`, `app/data/regions.json`에 달력·출처 등록 지명 해석을 분리했다.
- `useConditionInput.ts`, `AutomaticConditions.tsx`, `page.tsx`가 debounce/blur·한글 조합 보호·중복 방지·문장 버전·수동 수정 우선·충돌 재적용·단일 날짜/좌표/AOI·오래된 결과 표시를 담당한다.
- 예시 문장은 2026-07-01~31과 충청남도 포함 사각형으로 반영한다. 충남 전체는 25 km² 픽셀 처리 상한을 넘으며 작게 줄이지 않는다. 사건 날짜는 생성하지 않는다.
- 출처 확인 지역은 현재 충남/충청남도와 상주시의 등록 별칭이다. 그 외 및 미지원 하위 지명은 수동 지정을 안내한다. [방법·자료 연도·범위](AUTOMATIC_CONDITIONS.md)를 읽는다.
- 기존 3000/8000 서버를 임의 종료하지 않았다. 검증에는 별도 8011 FastAPI와 테스트 전용 실제 HTTP 전달을 사용한다. 변경 전 백엔드를 실행 중이면 사용자가 기존 실행 창에서 종료 후 `start.cmd`로 다시 실행해야 신규 응답을 읽는다.
- 최신 실행 수치·미실행 범위는 TEST_REPORT 맨 위를 따른다. 아래의 이전 성공 수치를 이번 변경 전체의 근거로 재사용하지 않는다.

---

## 최신 추가 기능 인계 — 2026-10-29 14:53 KST 확인

**이 절이 현재 인수인계 기준이다. 아래 `이전 인계 기록`은 12:00 시점 내용을 보존한 기록이며, 그 안의 미검증 상태·예정 기능·시작 프롬프트는 이 절과 최신 README/TEST_REPORT로 갱신해서 읽는다. 이번 작업은 이미 개발된 기능을 확인하고 문서만 갱신했으며 새 기능을 구현하지 않았다.**

### 원본과 VS Code는 같은 폴더

- 원본 대화: **Satellite Insight AI 초기 설정**, thread `01a18145-dfd6-72c0-b1ec-a8a0a1639fca`. 지원 도구로 읽은 작업 디렉터리는 `C:\Users\aicam\Documents\ChatGPT\바이브코딩`; 확인 시 마지막 턴 완료, 대화 idle 상태였다. 원본 대화에 지시/프롬프트를 보내지 않았다.
- VS Code 대상: `C:\Users\aicam\Documents\ChatGPT\바이브코딩`. 앞선 열기 명령과 `VS_CODE_HANDOFF.md - 바이브코딩 - Visual Studio Code` 창 제목에 더해, VS Code의 저장된 `workspaceStorage/af3fcf1cf12c80fd74b242fc180a1206/workspace.json`의 folder URI를 읽어 같은 절대 경로임을 확인했다(기록 생성 12:01 KST). 이번에는 창 내부나 저장되지 않은 편집 버퍼를 조작하지 않았다. 이 근거는 저장된 작업공간을 확인한 것이며 현재 활성 창을 새로 검증했다는 뜻은 아니다.
- 같은 디스크 폴더이므로 추가 기능 파일은 이미 공유된다. 복사·이동·별도 앱 생성·병합이 필요하지 않았다. 이번 수정 파일은 이 문서 하나이며 기존 코드·보고서·예시 산출물·사용자 수정은 덮어쓰지 않았다. Git 저장소는 여전히 없다.

### 이전 인계 이후 확인한 추가 구현

| 기능 | 현재 디스크의 근거 파일 | 상태와 한계 |
|---|---|---|
| UTC 날짜별 지도 탐색 | `frontend/src/lib/imageryExplorer.ts`, `components/ImageryExplorer.tsx`, `MapPanel.tsx`, `Results.tsx`, `SceneComparison.tsx`, `app/page.tsx` | 날짜·목록·footprint·선택·두 장면 비교 상태 연결. 확정 AOI 확대. 제공처 미리보기와 정량 원본을 구분 |
| 실제 QA/NDVI 지도 레이어 | `backend/app/pixel_raster.py`, `change_analysis.py`, `pixel_worker.py` 및 프론트 지도 연결 | 실제 A3/A4 배열에서 생성한 PNG만 표시. 표시용 위치 근사이며 정확한 분석 격자·값은 GeoTIFF 기준 |
| 제한된 자연어 후속 행동 | `backend/app/request_interpretation.py`, `frontend/src/components/NaturalWorkflow.tsx` | “선택한 두 날짜를 비교해”, “이 지역으로 이동해”를 기존 비교/확정 AOI 이동으로 연결. 지명 자동 좌표화·본문 날짜의 폼 자동 반영은 아직 없음 |
| 실제 관측 픽셀 선택 합성 | `cloud_composite.py`, `cloud_jobs.py`, `NaturalWorkflow.tsx` | 이전부터 존재하던 제한된 식생 S2 합성 흐름. 최신 전체 E2E 기록에는 실제 계획→확인→합성 ZIP 사례가 포함됨. 한 날짜 실측이나 ML 추정으로 표시하지 않음 |
| **선택형 ML 추정영상** | `backend/app/cloud_estimate.py`, `cloud_jobs.py`, `main.py`, `pixel_worker.py`, `frontend/src/components/EstimatedImage.tsx`, `NaturalWorkflow.tsx`, `ImageryExplorer.tsx`, `MapPanel.tsx`, `app/page.tsx`, `lib/types.ts` | 원본 개발 대화의 최신 완료 작업이며 코드·API·UI 연결을 확인함. 이번 인계에서 새로 만든 기능이 아님. `/estimate/plan`, `/estimate/jobs`와 상태/취소/다운로드 API가 있음 |

ML 추정은 같은 Sentinel-2 플랫폼·처리 기준선의 식생 한 시점 소형 AOI에 제한된다. 목표일/참조일 모두 맑은 적색·근적외선·녹색 짝픽셀로 국소 ridge 회귀를 학습한다. 2×2 공간 사분면 4-fold 검증과 단순 참조일 복사 기준선 대비 개선을 운영 게이트로 사용하며, 목표일 실제 관측값은 보존한다. 목표일 실측·추정·남은 결측을 구분하고 원본 재검사/확인 digest 후 실행한다. 맑은 보류 픽셀의 MAE/RMSE는 구름 아래 정확도를 보증하지 않는다. 홍수·산불·전후 변화·열환경·SAR·센서간 복원으로 일반화하지 않는다.

추정 ZIP은 `target_observed.tif`, `estimated_only.tif`, `estimate_with_observed.tif`, `pixel_status.tif`, `donor_index.tif`, `donor_date.tif`, `manifest.json`을 담는 코드와 기존 검증 기록이 있다. 자세한 방법은 [ESTIMATED_IMAGE_METHOD.md](ESTIMATED_IMAGE_METHOD.md), 공개 사례는 [GeoTIFF ZIP](../examples/sentinel-2-local-estimate-2021-07-16.zip) 및 [화면 기록](../examples/sentinel-2-local-estimate-ui.png)을 본다. 실제 관측 합성과 모델 추정 결과를 섞어 설명하지 않는다.

### 기존 실행 근거와 이번 미실행 범위

최신 [TEST_REPORT.md](../TEST_REPORT.md)의 맨 위는 선택형 ML 추정영상 보고서다. 원본 개발 대화의 마지막 완료 답변과 아래 결과가 일치한다. **다음은 원본 작업에서 실행한 기록을 확인한 것이며 이번 동기화에서 재실행한 결과가 아니다.**

| 기존 실행 시각 (KST) | 기존 결과 | 해석 |
|---|---|---|
| 약 14:41 | backend **195 passed / 12 skipped** | 기본 pytest. LIVE_STAC opt-in 12건은 이 실행에서 미실행 |
| 약 14:39 | `test_cloud_estimate_live.py` **1 passed** | LIVE_STAC=1로 별도 실행된 공개 영상 추정 계획→실행→ZIP/6 TIFF 재열기 사례. 전체 live suite 통과로 해석하지 않음 |
| 약 14:41–14:42 | typecheck·production build 종료 0 | 원본 작업 당시의 검사 |
| 약 14:46–14:49 | 전체 브라우저 E2E **53 passed** | 새 추정 실연결 흐름과 기존 검색/합성/A2–A4/지도/모바일/응답 경합 포함. fixture와 실제 사례 구분은 보고서 참조 |

이전 지도 단계 185 passed/11 skipped·49 E2E와 A4 173 pytest·39 E2E는 과거 이력이다. 한 공개 사례의 통과로 다른 지역·계절·구름 아래 정확도를 보장하지 않는다. QGIS 앱에서 직접 여는 수동 검증은 미실행으로 기록되어 있다. 이번에는 서버 시작/중지, 테스트, 설치, 인증/키 설정, 배포/push를 하지 않았다.

### 스택·실행·남은 범위

- 필수 스택 **FastAPI + React/TypeScript + Supabase** 유지. Next.js·MapLibre 의존성은 그대로다. 최신 앱 소스와 패키지/requirements에서 Supabase 통합을 찾지 못했다. 메모리 계획/작업 관리와 자식 Python 래스터 worker를 Supabase 영속 작업 이력·분산 queue로 표현하지 않는다.
- 실행 진입점은 확인한 `start.cmd` → `node scripts/start-local.mjs` 그대로다. 후속 사용 시 프로젝트 루트에서 `.\start.cmd`; 웹 화면 `http://127.0.0.1:3000`, API 문서 `http://127.0.0.1:8000/docs`. 3000/8000 점유 시 중복 실행을 거부하므로 기존 서버를 임의로 종료하지 않는다. 실행 명령 상세와 테스트 명령은 아래 기존 절을 사용할 수 있다. 현재 서버 실행 상태는 이번 확인 범위가 아니다.
- 환경변수 이름 `API_BASE_URL`, backend 실연결 opt-in `LIVE_STAC`은 기존과 같다. 값/자격증명은 읽거나 기록하지 않았다. frontend E2E에는 실제 연결 사례가 있어 backend의 LIVE_STAC 설정만으로 차단되지 않는다.
- HLS/GIBS는 [HLS_ADAPTER_DESIGN.md](HLS_ADAPTER_DESIGN.md)에 설계만 있다. 최신 지도 보고서에는 gods-eye-view 구조를 참고했고 MIT 코드/자산은 복사하지 않았다고 기록한다. 기존 인계의 “외부 참고 미검토”는 그 당시 상태다.
- **다음 사용자 요청 예정인 ‘자연어 날짜/지역을 폼·지도에 자동 반영하고 수동 수정 우선 유지’는 이번에 적용하지 않았다.** 확인한 `request_interpretation.py`는 날짜 언급/불일치를 질문으로 반환하고 확정 폼의 UTC 기간을 사용한다. `page.tsx`의 날짜·AOI는 직접 입력/지도 선택으로 갱신된다. 기존 “확정 AOI로 이동” 버튼은 지명 자동입력이 아니다. 다음 프롬프트는 사용자가 직접 넣을 예정이다.

### VS Code AI가 먼저 읽을 짧은 시작 지침 (최신)

> 같은 `C:\Users\aicam\Documents\ChatGPT\바이브코딩` 폴더에서 이어서 작업해줘. 먼저 AGENTS.md와 docs/VS_CODE_HANDOFF.md의 최신 인계 절, README.md, TEST_REPORT.md, docs/ESTIMATED_IMAGE_METHOD.md 및 실제 코드를 읽어줘. A3/A4·날짜별 지도 탐색·실제 관측 합성·선택형 ML 추정영상은 이미 디스크에 반영되어 있으니 재구현하거나 원관측과 추정을 혼동하지 마. 원본 작업의 195 passed/12 skipped·별도 공개 영상 1 passed·53 E2E 기록은 기존 근거이며 이번 인계에서 재실행하지 않았어. 필수 FastAPI·React/TypeScript·Supabase와 기존 Next.js·MapLibre를 유지하되 Supabase 통합은 아직 확인되지 않았어. 사용자 수정과 진행 중 작업을 보존하고, 다음에 내가 붙여넣는 날짜·지역 자동입력 프롬프트를 받은 뒤 그 지정 범위에서 진행해줘.

---

## 이전 인계 기록 — 2026-10-29 12:00 KST (보존용)

기준: 2026-10-29의 로컬 파일 확인. 이 문서는 개발 환경 인수인계이며 새 기능 구현 지시가 아니다. 진행 중인 다른 작업이 있으면 최신 코드·문서를 다시 확인한다.

## 기존 폴더와 작업 원칙

- 실제 프로젝트: `C:\Users\aicam\Documents\ChatGPT\바이브코딩`
- 이 폴더를 VS Code의 **파일 → 폴더 열기**로 그대로 연다. 복사·이동·재생성하지 않는다.
- 먼저 `AGENTS.md`, `frontend/AGENTS.md`, `README.md`, `TEST_REPORT.md`, `docs/NEXT_STEPS.md`를 읽는다. frontend 코드를 수정할 때는 해당 AGENTS.md의 설치된 Next.js 문서 확인 지침을 따른다.
- 확인 시 Git 저장소가 아니었다. Git 상태/커밋으로 변경 여부를 증명할 수 없으며, 기존 파일과 실행 중 작업을 보존해야 한다. Git 초기화·원격 연결·push는 이번 인수인계에서 하지 않았다.
- 이번 인수인계는 문서만 작성하며, 테스트·서버 실행/종료·배포·확장 설치·Supabase 설정을 수행하지 않는다. 환경변수 값이나 자격증명은 읽거나 문서화하지 않는다.

## 제품 목표와 필수 스택

공간분석 대학원생·연구자·GIS 실무자가 목적, AOI, 기간을 입력하면 관측 방식·탑재체·위성·제품을 근거와 함께 추천하고 실제 검색, AOI 픽셀 QA, 확인한 조건 안의 대체영상/관측 합성, GIS용 결과와 출처로 이어지는 서비스다. 주요 문제는 목적에 맞는 탑재체 선택과 정해진 지역·기간의 구름이다. 탑재체 선택을 필수로 만들지 않으며, 단순 가능/불가 판정이나 지구본 장식이 제품 목표가 아니다.

| 항목 | 요구 / 확인된 상태 |
|---|---|
| FastAPI | `backend/app/main.py`, `backend/requirements.txt`에서 확인 |
| React + TypeScript | `frontend/package.json`에서 Next.js 16 계열·React 19 계열·TypeScript 확인. 기존 Next.js 유지 가능 |
| Supabase | 사용자 필수 스택. 확인한 앱 소스/의존성에서 통합을 찾지 못함. 인증·프로젝트·작업 이력 저장은 후속 구현 |
| 지도 | MapLibre GL 유지 |
| 래스터 | Rasterio·NumPy·PyProj·Shapely 사용. 기존 자식 Python 래스터 프로세스가 존재함 |

## 코드 존재와 검증 상태를 분리한 현황

| 범위 | 파일에서 확인한 내용 | 검증 근거 / 한계 |
|---|---|---|
| 검색·추천·지도 | Earth Search STAC Sentinel-2 L2A/Landsat C2L2 검색, 목적별 추천, 센서/제품 카드, AOI·footprint, 부분 실패·검색 한도·복합 Item 키 | `stac.py`, `sensor_catalog.py`, `purpose_plan.py`, `MapPanel.tsx`, `Results.tsx`. 이번 작업에서 실연결 재검증 안 함 |
| 비교·Asset | 두 장면 메타데이터·제공처 미리보기, 밴드 다중 선택, 원본 Asset 직접 링크와 링크목록 저장 | `SceneComparison.tsx`, `AssetDownloads.tsx`. 미리보기는 분석원본/지수 계산 결과가 아님 |
| A2 | canonical Item 재조회, 날짜·센서/제품·필수/품질 자료·공개 Asset HEAD·CRS/격자·공통 footprint 검사 | `analysis_conditions.py`, `grid_metadata.py`. A2 자체는 픽셀 검사 아님 |
| A3 | 작은 AOI(25 km² 이하)의 S2 L2A 실제 SCL/필수 밴드 범위 읽기, 공통 격자·유효 면적, 상한·실패/null 처리 | `pixel_quality.py`, `pixel_raster.py`, `pixel_policy.py`, `range_reader.py`, `pixel_worker.py`, `PixelQuality.tsx`. 기존 A3/A4 보고서 참조 |
| A4 | 같은 Sentinel-2 플랫폼·처리 기준선, 보정이 확인된 두 날짜의 공통 유효 픽셀 NDVI 전후/차이. GeoTIFF·마스크·처리 JSON ZIP | `change_analysis.py`, `ChangeAnalysis.tsx`. 기존 `TEST_REPORT.md`의 A4 검증 기록 참조 |
| 자연어 문맥·관측 합성 | `request_interpretation.py`, `cloud_jobs.py`, `cloud_composite.py`, `NaturalWorkflow.tsx` 및 page 연결 코드가 이미 존재. `/request/interpret`, `/cloud/plan`, `/cloud/jobs` 상태·취소·다운로드 API 존재 | **기존 A4 보고서보다 넓은 코드 범위다. 이 인수인계에서는 테스트하지 않았고, 현재 전체 성공을 확인하지 않았다. 새 기능을 미구현으로 단정하거나 완료 검증으로 표현하지 말 것** |

자연어 해석은 기존 목적 규칙과 제한된 후속 요청을 사용하며 지명 자동 지오코딩·상대 날짜 자동 확정을 하지 않는다. 화면에서 확정한 AOI/UTC 기간과 선택 장면을 사용한다.

현재 합성 코드는 식생 한 시점/기간 상태의 Sentinel-2 L2A, 같은 플랫폼·처리 기준선, 최대 4장면·기간 차이 31일·AOI 25 km²를 제한한다. 실제 QA 계획과 확인 digest 후 작업 시작, 재조회, 취소가 구현되어 있다. 한 출력 픽셀의 red/nir/green 밴드는 같은 장면에서 선택하며 `analysis_bands.tif`, `valid_mask.tif`, `source_index.tif`, `source_date.tif`, `manifest.json`을 ZIP에 기록하는 코드가 있다. 실제 실행 성공 여부는 별도 검증해야 한다.

작업/계획 상태는 `cloud_jobs.py`의 메모리 딕셔너리이며 15분 TTL과 보관 상한이 있다. 래스터는 `pixel_quality.py`가 `app.pixel_worker` 자식 프로세스를 실행한다. 이것을 Supabase 기반 영속 작업 이력이나 분산 worker/queue가 구현된 것으로 표현하지 않는다. 장시간 처리를 별도 운영 worker로 분리하고 Supabase에 상태/결과 참조를 저장하는 것은 후속 설계다.

## 테스트 기록의 의미

확인한 `TEST_REPORT.md`는 2026-10-29 A4 보고서이며 당시 backend **173 passed**(합성/단위 163, 실연결 10), frontend build/typecheck 성공, E2E **39 passed**를 기록한다. QGIS 앱 자체는 실행하지 않았다고 명시한다. 이 숫자는 과거 A4 실행 근거이고, 자연어/합성 등 최신 변경 전체에 대한 통과 증거가 아니다. `test_cloud_composite.py`, `test_cloud_jobs.py`, `test_cloud_composite_live.py`, `cloud-workflow.spec.ts` 등 새 테스트 파일은 존재하지만 이번에 실행하지 않았다.

## 실행·검증 명령 (후속 작업용, 이번에는 실행하지 않음)

기존 `.venv`, `frontend/node_modules`가 있다. 의존성을 무조건 재설치하지 말고 필요할 때 README와 lock 파일을 따른다. 다음은 Windows PowerShell 기준이다.

프로젝트 루트에서 통합 개발 서버:

```powershell
Set-Location 'C:\Users\aicam\Documents\ChatGPT\바이브코딩'
.\start.cmd
# 같은 실행 진입점: node scripts/start-local.mjs
```

통합 실행기는 3000/8000 포트 점유를 확인하며, 점유 중이면 새 실행을 거부한다. 기존 서버를 임의 종료하지 않는다. 별도 터미널로 실행하려면:

```powershell
# 루트: 백엔드
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

```powershell
# 별도 터미널: 프론트엔드
Set-Location 'C:\Users\aicam\Documents\ChatGPT\바이브코딩\frontend'
npm.cmd run dev
```

프론트엔드 http://127.0.0.1:3000, 백엔드 API 문서 http://127.0.0.1:8000/docs. 브라우저의 `/api/*`는 `frontend/next.config.ts`가 백엔드로 전달한다.

```powershell
# backend 폴더: 실연결을 제외한 테스트
Set-Location 'C:\Users\aicam\Documents\ChatGPT\바이브코딩\backend'
Remove-Item Env:LIVE_STAC -ErrorAction SilentlyContinue
..\.venv\Scripts\python.exe -m pytest -q

# 실제 외부 연결 검증을 의도한 후속 작업에서만
$env:LIVE_STAC = '1'
..\.venv\Scripts\python.exe -m pytest -q --disable-warnings
Remove-Item Env:LIVE_STAC -ErrorAction SilentlyContinue
```

```powershell
# frontend 폴더
Set-Location 'C:\Users\aicam\Documents\ChatGPT\바이브코딩\frontend'
npm.cmd run typecheck
npm.cmd run build
npm.cmd run test:e2e
```

build는 `.next`를 갱신하므로 실행 중 개발 서버와 작업 시간을 조율한다. `playwright.config.ts`는 localhost:3000, Edge, headless, worker 1개이며 서버 자동 시작 설정이 없다. E2E는 서버가 준비되어 있어야 하고 실제 STAC/래스터 연결 테스트도 포함한다. **backend의 LIVE_STAC opt-in이 frontend E2E를 차단하지 않는다.** fixture와 실제 연결 결과를 분리해 기록한다. production 실행은 frontend에서 `npm.cmd run build` 후 `npm.cmd run start`이며 backend가 별도로 필요하다.

## 환경변수 이름

- `API_BASE_URL`: Next.js 서버 측 백엔드 프록시 설정 (`frontend/next.config.ts`).
- `LIVE_STAC`: backend 실연결 테스트 opt-in.
- 이 목록은 확인한 앱 설정·테스트의 이름이다. `.env` 실제 값이나 키는 읽지 않았다. Supabase 환경변수 이름은 아직 구현에 연결된 것이 확인되지 않아 임의로 확정하지 않는다.

## 다음 권장 단계와 후속 범위

1. 진행 중인 다른 개발 작업 유무와 최신 파일을 다시 확인하고, A4 문서와 자연어/합성 코드 사이의 차이를 검토한다. 해당 변경 검증이 끝났는지 확인한 뒤 보고서를 갱신한다.
2. 사용자 지정 범위에서 Supabase 인증·프로젝트·작업 이력의 스키마, 접근 정책, 상태/결과 참조를 설계한다. 자격증명은 사용자 설정 절차로 다루고 문서에 넣지 않는다.
3. 현재 MapLibre의 AOI/footprint/목록/날짜/선택/두 영상 비교 연동을 우선한다. 참고 대상으로 지정된 `https://github.com/bilawalsidhu/gods-eye-view`의 `recentImagery/catalog.js`, `model.js`, `source.js` 및 지도 UI 구조는 **향후 선별 검토 대상**이다. 이 인수인계에서는 외부 코드를 가져오거나 검토하지 않았다.
4. HLS NASA CMR/GIBS 제공처 추가는 다음 설계다. GIBS는 미리보기이며 분석원본이 아니고, HLS 30 m는 S2 native 10 m 또는 지표온도 제품이 아니다. 고정 최근 30일/구름 20%를 과학적 판정으로 복제하지 않는다. 코드 MIT와 데이터 라이선스는 별개다.

기간 임의 확대, 사건 전후 혼합, 미관측 픽셀 생성은 금지한다. 실제 관측 선택 합성과 ML 추정은 구분한다. SAR/A5·센서간 합성·ML 복원·Cesium 교체·음성·항공기·선박·CCTV·FLIR는 자동 착수하지 않는다. S3/요청자 비용 자료의 자동 인증·비용 동의·다운로드 프록시는 구현하지 않는다. 장면 구름량은 AOI 구름량이 아니고, 기하 중첩은 유효 관측률이 아니다. 누락/실패는 null·미확인으로 남기고 추천을 과학적 품질 점수로 표현하지 않는다.

## VS Code에서 이어서 쓸 시작 프롬프트

> 현재 열린 `C:\Users\aicam\Documents\ChatGPT\바이브코딩` 프로젝트에서 이어서 작업해줘. 먼저 루트/하위 AGENTS.md와 docs/VS_CODE_HANDOFF.md, README.md, TEST_REPORT.md, docs/NEXT_STEPS.md 및 최신 코드를 읽어줘. 필수 스택은 FastAPI + React/TypeScript + Supabase이고 기존 Next.js·MapLibre는 유지해. 기존 사용자 수정과 실행 중 작업을 보존하고 프로젝트를 복사하거나 재생성하지 마. A3/A4 및 자연어/관측 합성 코드가 이미 있으므로 구현 존재와 실제 검증 성공을 구분해 현재 상태와 문서 차이를 먼저 알려줘. 과거 173 pytest/39 E2E 성공을 최신 전체 통과로 재사용하지 마. Supabase 통합은 미확인이며 현재 메모리 작업 관리와 자식 래스터 worker를 운영용 영속 작업 시스템으로 오인하지 마. 아직 새 기능 구현·설치·서버 변경·테스트·배포를 시작하지 말고, 다음에 내가 지정하는 개발 범위에서 진행해줘.

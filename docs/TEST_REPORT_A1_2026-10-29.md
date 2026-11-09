# A1 최신 검증 보고서

검증일: **2026-10-29 (Asia/Seoul)**. 작업 루트: `C:\Users\aicam\Documents\ChatGPT\바이브코딩`.
이 폴더에는 `.git`이 없으므로 Git 체크아웃/커밋 상태를 주장하지 않는다. 기존 앱을 이어서 수정했으며 배포·푸시하지 않았다. A2~A5는 착수하지 않았다.

## 최신 실행 결과

아래 명령은 A1 코드 변경 후 실제 실행했다. 과거 33개 pytest / 3개 E2E 기록을 재사용하지 않았다.

| 실행 위치 | 실제 명령 | 종료 코드 | 결과 |
|---|---|---:|---|
| `backend` | `$env:LIVE_STAC='1'; ..\.venv\Scripts\python.exe -m pytest -q` | 0 | **51 passed**, 12.57초, Starlette 사용 중단 예정 경고 1개 |
| `frontend` | `npm.cmd run test:e2e` | 0 | **14 passed**, 29.5초, 설치된 Edge headless |
| `frontend` | `npm.cmd run build` | 0 | Webpack production build, TypeScript, 정적 페이지 생성 완료 |
| `frontend` | `npm.cmd run typecheck` | 0 | 빌드 종료 후 별도로 `tsc --noEmit` 실행 완료 |
| 루트 | `node scripts/start-local.mjs` | 실행 중 | 최종 서버 재실행, `/api/health` 확인, 127.0.0.1:3000 사용 가능 |

백엔드 51개 중 4개는 `tests/test_live.py`의 실제 외부 연결 검사다. 나머지는 합성 메타데이터/페이지/전송 계층을 사용하는 단위·API 검사다. E2E 14개 중 `search.spec.ts` 첫 테스트는 실제 STAC 요청·지도 AOI·메타데이터를 검증한다. 새 `reliability.spec.ts` 11개는 테스트 전용 검색 응답을 모사하며 `/selection-overlap`의 기하 안내는 로컬 실제 API를 사용한다. 합성 결과의 출처는 `TEST_ONLY_SYNTHETIC`으로 표시한다. 서비스에는 fixture 대체 경로가 없다.

테스트 코드만 작성하고 실행하지 않은 A1 필수 검사는 없다. A2~A5의 실제 래스터·분석·SAR 검사는 미구현·미실행이다.

## 실패 및 재실행 기록

- 첫 E2E: 종료 1, **13 passed / 1 failed**. 프록시 timeout 검사의 `getByRole('alert')`가 앱 알림과 Next.js 내부 route announcer 두 개를 선택했다. 실제 오류 문구는 표시됐으나 선택자가 모호했다. `.error[role="alert"]`로 한정한 뒤 전체 14개 재실행 통과.
- 첫 typecheck 시도: 루트에서 실행해 종료 1, 루트 `package.json` 없음(ENOENT). 설정이 있는 `frontend`에서 명령을 실행해 성공했고, 최종 빌드 후에도 독립 재실행했다.
- 제한된 실행 환경에서 루트 `python -m pytest -q backend/tests` 시도는 출력 없이 대기하여 중단(종료 1). 성공으로 계산하지 않았다. 문서화된 `backend` 작업 디렉터리와 허용된 실행 권한으로 실제 연결을 포함해 50개 통과 후, 한도 1건 경계 테스트를 추가해 최종 51개를 다시 실행했다.
- 기존 3000/8000 서버가 실행 중일 때 시작 명령은 종료 1로 중복 실행을 막았다. PID/명령을 확인해 이 작업에서 띄운 기존 launcher만 종료하고 최신 코드로 재시작했다. 다른 프로그램을 종료하지 않았다.
- 최종 실제 검색 E2E는 페이지 이동 시작부터 끝까지 응답 URL/상태를 수집했고 **HTTP 4xx/5xx 목록은 `[]`**였다. 과거의 원인 미상 콘솔 404가 해결됐다고 주장하지 않는다. 합성 실패 테스트의 504 콘솔 메시지는 주입한 `/api/search` 실패이며 예상된 결과다.
- Starlette testclient의 httpx 사용 중단 예정 경고, Node의 NO_COLOR/FORCE_COLOR 경고는 남아 있다. 실행 실패는 아니며 이번에 의존성 교체로 범위를 넓히지 않았다.

## 구현 상태와 검증 범위

| 기능 | 상태 / 확인 내용 |
|---|---|
| 컬렉션별 상태 | 성공·빈 결과·부분 성공·실패·조회 제한·미조회 분리. 일부 실패 시 다른 컬렉션 실제 결과 보존. 전부 실패와 전체 0건 구별 |
| 페이지네이션/한도 | 컬렉션별 최신순 페이지에서 번갈아 1건씩 반환, 빈 몫 재사용. 12회 요청 / 45초 deadline / 회당 10초. 마지막 페이지, 버퍼, 다음 페이지 존재 또는 미확인 공개 |
| 중복 식별자 | `(collection, id)`로 검색 중복 제거 및 지도·비교·밴드 상태 연결. 서로 다른 컬렉션의 같은 ID는 보존 |
| 그룹과 순위 | 센서 그룹은 고정 탐색 순서. 영상 순위는 실제 밴드·기하·구름량·해상도·날짜 메타데이터로 별도 비교. 누락값 마지막, 점수 미생성 |
| 비교 선택 | 센서 후보 비교 / 전후 변화용 영상 선택. 전후 기본 선택은 같은 컬렉션·센서·제품이며 다른 컬렉션 자동 대체 금지. 중복·날짜 역전/동일·메타데이터 누락 안내 |
| 공통 영역 | A1 선택 안내만 구현: AOI∩두 footprint에 양의 면적이 존재하는지 확인. 경계 접촉만 있으면 없음. 누락/잘못된 기하는 미확인. 실제 면적·품질·Asset 검사는 아님 |
| 밴드/다운로드 | 목적 기본값, 시각화 세트, 전체/해제/복원, 직접 URL·제한 링크 표시, txt 저장 유지. 그룹 페이지 이동에도 선택 유지. 저장 파일을 실제로 읽어 선택 URL 집합·제외 URL 검증 |
| 응답 경합 | 검색 중 목적·날짜·AOI·위성 선택·조회 한도 변경 시 요청 취소 및 버전 검사. 늦은 응답이 현재 결과를 덮어쓰지 않음 |
| 모바일 | 390×844 결과 포함 화면의 가로 넘침 없음, 비교 모드·선택 컨트롤 작동 |
| 미리보기 | 부분 지원: 공개 HTTP(S) 제공처 이미지에 한함. 없는 이미지는 생성하지 않음 |
| A2~A5 | 계획만 기록. Asset 헤더·격자·픽셀 품질·변화량·GeoTIFF 분석 산출물·Sentinel-1 검색은 미구현 |

백엔드 추가 검사: 첫 요청 실패 후 다른 컬렉션으로 한도 재사용, 정상 빈 결과와 한도 정확 일치, 다음 페이지 timeout 후 기존 결과 유지, 페이지 간 중복 및 같은 ID/다른 컬렉션, 반복 페이지의 요청 상한, deadline과 미조회, 전부 실패 대 전부 빈 결과, 잘못된 Item 부분 제외, 그룹과 독립된 순위·누락값, next 링크 GET/POST·merge·출처 제한, 실제 asyncio 요청 대기 상한, 공통 기하의 holes·접촉·AOI 밖·누락, 전체 한도 1건.

## 변경 파일

아래 경로는 모두 위 작업 루트 기준 실제 파일이다.

| 구분 | 경로 |
|---|---|
| 수정: 서버 | `backend/app/main.py`, `stac.py`, `models.py`, `evaluation.py`, `purpose_plan.py` |
| 신규: 선택 안내 | `backend/app/selection.py`, `frontend/src/lib/selection.ts` |
| 수정: 화면/상태 | `frontend/src/app/page.tsx`, `globals.css`, `frontend/src/components/SceneComparison.tsx`, `MapPanel.tsx`, `Results.tsx`, `AssetDownloads.tsx`, `frontend/src/lib/types.ts`, `api.ts` |
| 수정: 기존 테스트 | `backend/tests/test_core.py`, `test_purpose_plan.py`, `frontend/tests/search.spec.ts` |
| 신규: 회귀 테스트 | `backend/tests/test_search_reliability.py`, `frontend/tests/fixtures.ts`, `reliability.spec.ts` |
| 문서 | `AGENTS.md`, `README.md`, `TEST_REPORT.md`, `docs/NEXT_STEPS.md`, `docs/TEST_REPORT_2026-10-28.md` |

`metadata.py`, `recommendations.py`, `test_live.py`, 패키지 설정과 MapLibre 설치 구조는 읽고 확인했으며 불필요하게 다시 만들지 않았다. 기존 npm의 build/typecheck/test:e2e 스크립트를 재사용했다. 라이브러리를 새로 설치하지 않았다. STAC 통신은 기존 설치된 httpx를 사용해 페이지별 상태·취소/시간 한도를 직접 다룬다. 페이지 의미는 [STAC API v1.0.0 예제](https://github.com/radiantearth/stac-api-spec/blob/release/v1.0.0/item-search/examples.md)를 참고했다.

## 재현 방법

1. 루트에서 `node scripts/start-local.mjs` 실행 후 `http://127.0.0.1:3000` 접속. 이미 실행 중이면 중복 시작하지 않는다.
2. 침수 목적, 충남 예시 영역, 2025-05-01~2025-07-31, 25건으로 실제 검색. 센서 그룹·상태·촬영 범위·카드·페이지 이동 확인.
3. 비교 목적을 전후로 바꾸고 동일 Item/역전 시점 선택. 공통 영역 안내와 판정 보류 확인.
4. 밴드 선택 후 링크 목록을 저장해 선택한 공개 URL만 포함됐는지 확인. 전체 영상 파일 일괄 다운로드 기능은 아니다.
5. 위 표의 pytest/E2E 명령 재실행. 부분 실패·빈 결과·timeout·경합은 테스트에서만 모사한다. 운영 검색 결과를 조작하지 않는다.
6. 빌드는 개발 서버를 종료한 뒤 `frontend`에서 `npm.cmd run build`, 이어서 `npm.cmd run typecheck`. 검증 후 launcher로 다시 실행한다.

화면 증거: `frontend/test-results/live-map.png`, `live-search.png`(실제 검색), `a1-mobile.png`(합성 UI 회귀). 테스트 산출물은 다음 E2E 실행 때 갱신될 수 있다.

## 남은 한계

- 두 컬렉션은 같은 Earth Search 제공처를 사용한다. 부분 실패 격리는 컬렉션/페이지 단위이며 독립 제공처 장애 대체는 구현하지 않았다.
- 상한 이후의 정확한 후보 수는 알 수 없다. 조회 중인 최신순 페이지와 버퍼까지만 근거가 있으며 전체 카탈로그 최적 결과를 보장하지 않는다. 다음 페이지 URL·인증정보를 클라이언트에 저장하지 않으며 재검색으로 범위를 좁힌다.
- 45초는 네트워크 요청 deadline이고 JSON·기하 처리에 소량 추가 시간이 필요할 수 있다. 취소된 브라우저 요청의 백엔드 처리는 서버 예산 안에서 끝날 수 있다.
- A1 공통 기하 존재는 분석 가능 판정이 아니다. 개별 장면 중첩률을 두 시점 공통 관측률로 합치지 않았다. 래스터/QA·CRS/격자·scale/offset·면적 계산은 후속 단계다.
- 공개 링크는 원본 전체 장면 주소다. 이 테스트의 실제 HEAD 검사는 특정 Sentinel-2 Asset 1건으로 모든 검색 결과의 접근을 보증하지 않는다. Landsat의 S3/requester-pays 제한은 유지한다.
- 외부 지도·썸네일·카탈로그의 미래 가용성은 보장하지 않는다. 접근 실패를 가짜 데이터로 대체하지 않는다.

## 과거 이력

2026-10-28의 원본 기록(24/26/33 pytest, 3 E2E 및 수동 UI 확인)은 [이전 보고서](docs/TEST_REPORT_2026-10-28.md)에 그대로 보존했다. 해당 숫자는 당시 코드에 대한 이력이고 위 최신 A1 결과와 별개다. 기존 직접 다운로드 링크·밴드 다중 선택·메타데이터 비교는 구현 완료이며 이를 통째로 미구현으로 표기하지 않는다.

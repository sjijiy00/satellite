# Planner 보고서 — 자동 미리보기·제공처 연결

2026-10-30 · 회차1 · 역할 Planner · 기획 완료, 리더 조정 대기. 제품 구현 완료 보고가 아니다.

## 요구 충족 범위와 조사 근거

`AGENTS.md`, 공유 brief/task, 최신 README·TEST_REPORT, `frontend/AGENTS.md`, 관련 코드·테스트·인증 설계를 확인했다. 구조는 FastAPI(`backend/app`), Next.js(`frontend/src`), 실행/환경 전달(`scripts`)이다. 현재 검색은 Earth Search(S2/Landsat), Copernicus(S1 GRD), NASA CMR(VNP09GA.002)의 **3개 제공처·4개 컬렉션**이다. 다른 등록 후보, 다른 센서의 분석 엔진은 이번 범위에 넣지 않는다.

- **수동 확인 원인:** `ProviderPreview.tsx`는 버튼에서만 `inspect()`를 호출하고, `useProviderAccess.ts`에는 자동 실행·가시성 감지·공유 캐시/중복 병합이 없다. 목록·탐색·비교가 같은 컴포넌트를 사용하므로 각자 자동 호출을 추가하면 같은 장면을 중복 수신한다.
- **만료 원인:** `media_access.py`의 receipt는 120초, 미디어 owner는 서버 메모리에서 1시간이다. `/media/session` 성공 Promise는 프런트 모듈에서 계속 재사용된다. 서버 재시작/owner 만료 뒤에도 준비됐다고 판단하며, 병렬 inspect가 새 owner를 각각 만들면 cookie/receipt가 엇갈릴 위험이 있다(코드상 위험, 이번 재현 아님). 이미지 오류는 현재 수동 재검사만 안내한다.
- **인증 유지 한계:** `earthdata_auth.py`는 최대8시간 메모리 세션이며 재시작 시 소멸한다. 실제 발급된 refresh token에 한해 세션별 잠금·회전·401 후 1회 갱신을 구현했지만, 실제 앱 등록/발급/LP DAAC 파일 권한은 미검증이다. 현재 logout은 사이트 세션 제거이며 제공처 전체 세션/토큰 폐기와 동일하지 않다.
- **Kakao 설정 불일치:** 비밀값 없이 확인한 결과 `backend/.env`에는 키가 존재하고 `GEOCODER_ENABLED=1`이다. 런처 환경 병합 결과도 존재/활성=true, 조사 프로세스의 해당 변수 override=false였다. 그러나 backend8000와 웹3000 `/api/places/config`는 모두 HTTP200·ready=false·두 변수 누락이다. 실행 프로세스가 파일 변경을 아직 반영하지 않은 정황이다. 실행 방식/상속 환경까지 확인해야 원인을 확정할 수 있다. Earthdata 앱 설정 3개는 파일/병합 환경 모두 미설정이며 두 서버 status도 configured=false다.

## 우선 구현안과 완료 기준

1. **P0 자동 표시:** 실제 viewport에 들어온 preview만 `asset_keys:[]`, `include_preview:true`로 기존 inspect에 연결한다. 클라이언트 공유 큐 동시2개, 키는 provider/collection/Item+인증 generation으로 한다. 동일 키 요청 병합, 대기 중 비가시 장면 제거, 구독자 없는 요청 취소, 메모리 캐시 건수/바이트 제한을 둔다. 서버 기존 전송 동시2개·이미지8MiB·캐시32MiB/100건·시간당512MiB 제한은 유지한다. 원본 probe/전체 수신은 자동 실행하지 않는다.
2. **P0 세션 복구:** 세션 준비를 만료 가능한 단일 요청으로 합치고 서버 generation 변경/receipt 무효화 때 재준비한다. 검증된 이미지의 일시적 receipt 오류는 가시 상태에서 **자동 복구 최대1회**, 이후 명시 재시도로 끝낸다. 제공처 401/403·쿼터·네트워크 실패를 무한 재시도하거나 로그인창으로 자동 이동하지 않는다. 장면·인증 변경은 이전 요청/캐시/이미지를 무효화하고 늦은 응답을 폐기한다.
3. **P0 설정 반영:** `start-local.mjs → childEnvironments` 경로를 유지한다. 프로세스 환경 우선, 고정 `backend/.env` allowlist, frontend/build 비밀 제거를 보존한다. 직접 uvicorn은 `.env` 자동 로딩이 없으므로 실행 안내를 명확히 한다. 진행 중 작업과 기존 승인 범위를 리더가 확인한 뒤 프로젝트 서버만 재시작하고 직접/프록시 config 일치를 확인한다. Planner는 재시작하지 않았다. Kakao 실조회는 그 다음 별도 검증이며 설정 인식만으로 성공 판정하지 않는다.
4. **P1 재시작 후 연결 유지:** 사용자별 암호화 저장소와 안정적인 불투명 세션 cookie를 구현해야 한다. 로컬 Windows 우선안은 OS 보호 키+암호화 grant 저장소, epoch 기반 만료 시각, 원자 갱신/폐기·파일 권한 제한이다. 키를 DB와 같은 평문 파일에 저장하지 않는다. 만료/철회/로그아웃 때 삭제하고 갱신 중 로그아웃도 되살리지 않는다. 저장소가 준비되지 않으면 메모리 모드를 정확히 표시한다. 공개 callback은 공유 암호화 저장소·키 관리·분산 잠금 전까지 차단한다. 영구 연결 완료는 앱 등록과 실제 재시작/갱신/파일 접근 검증 전 주장할 수 없다.

## API·프런트 계약 제안

기존 `/api/media/inspect`·preview/download 경로를 유지한다. session 응답에 비밀이 아닌 `session_generation`, `expires_at`, preview 응답에 `receipt_expires_at`을 추가하고 UTC 시각으로 전달한다. 만료/세션 무효·busy·쿼터 오류는 안정적인 code와 제한된 재시도 정보를 제공하되 사용자 존재/다른 사용자 receipt 정보는 노출하지 않는다. provider/collection 조합은 기존 서버 검증을 유지한다.

UI 상태는 대기/수신/표시/인증 필요/실패로 구분한다. 숨긴 preview는 자동 재표시하지 않는다. 계정 status에 저장 방식·연결 만료·갱신 가능·재연결 필요를 표시한다. callback/refresh/logout 및 다른 탭의 연결 변경을 generation에 반영한다. 브라우저에 토큰·최종 서명 URL·비밀번호를 전달하지 않는다. 원본 다운로드는 기존 명시 사용자 동작을 유지한다.

## 제공처 공식 조건과 미충족 사항

2026-10-30 공식 자료를 조회했다.

- [NASA SSO](https://urs.earthdata.nasa.gov/documentation/for_users/sso_process_overview)는 서버 코드 교환과 access/refresh token을 설명한다. [앱 승인/EULA](https://urs.earthdata.nasa.gov/documentation/for_users/what_is_app_auth)는 별도 조건이다. OAuth 로그인만으로 LP DAAC 원본 권한을 보장하지 않는다. 앱 등록·정확한 callback·실제 발급/갱신·대상 파일 검증이 필요하다.
- [USGS M2M](https://www.usgs.gov/media/files/m2m-application-token-documentation)는 `login-token`과 ERS application token을 안내한다. 이는 NASA OAuth나 LandsatLook 로그인 cookie의 대체라는 근거가 아니다. 현 표본의 USGS302는 이전 실검증 기록이다. 계정/M2M 이용권한·정확한 제품/파일·다운로드 경로를 별도 검증하기 전 USGS 연결 완료로 표시하지 않는다. 기존 공식 포털 안내와 requester-pays 제한을 유지한다.
- [CDSE 토큰 문서](https://documentation.dataspace.copernicus.eu/APIs/Token.html)는 원본 OData access/refresh와 재인증을 안내하며 비밀번호 하드코딩을 경고한다. 현재 앱에 원본 인증은 미연결이다. 제공처별 승인 방식·토큰 수명·대상 Asset 호환성 검증 없이 범용 비밀번호 저장이나 무기한 연결을 구현하지 않는다.
- [Kakao Local](https://developers.kakao.com/docs/en/local/dev-guide)은 REST 키를 인증 헤더로 전달한다. 키 존재는 권한/쿼터/실위치 성공 증거가 아니다. 지도 이동 전용·수동 AOI 원칙을 유지한다.

## 단계2 파일 소유권 제안

| 역할 | 단독 소유 파일/범위 |
|---|---|
| 백엔드 | `backend/app/{media_access,provider_transfer,earthdata_auth,main}.py`, 새 세션 저장 모듈, 관련 기존 backend 테스트 |
| 프런트엔드 | `frontend/src/lib/useProviderAccess.ts`, 새 preview 큐/캐시 모듈, `ProviderPreview.tsx`, `EarthdataConnection.tsx`, 필요시 `ManagedAssetAccess.tsx`·types·CSS |
| 환경 담당 | `scripts/server-env.mjs`, 해당 테스트·런처·비밀 없는 `.env.example`; 실제 `.env` 보존 |
| QA | 새 자동미리보기 E2E/격리 테스트 파일, QA 보고서; 기존 테스트 변경은 원 소유자와 인계 |
| 보안 | 보안 보고서만; 사용자 격리·저장/폐기·인증/redirect·로그 검토 |
| 리더 | API 계약 확정, README·TEST_REPORT·관련 설계 문서, 배정/인계·재시작 판단 |

공유 파일은 한 작성자만 수정한다. 별도 디자인 역할은 필수 아님. 위 표는 제안이며 이 세션은 배정/위임하지 않았다.

## 검증 계획·실행 기록·미결정

QA는 viewport 밖 요청0, 같은 장면 다중 표시 요청1, 동시상한, 120초/1시간 만료·서버 재시작 복구, 장면 변경·logout·refresh 지연 응답 폐기, 실패 후 명시 재시도, 자동 원본 요청0을 요청수와 실제 표시로 검증한다. 사용자A/B 격리·암호문 저장·키 손실·회전/철회·logout 중 갱신도 검사한다. NASA 공개 browse 실표시와 Landsat 제한 상태, 작은/큰 preview·모바일·밴드/비교·기존 AOI/분석 회귀를 포함한다. 인증 성공 fixture와 실제 사용자 인증을 분리한다.

예정 명령: backend `..\.venv\Scripts\python.exe -m pytest -q --disable-warnings`; root `node.exe --test scripts/server-env.test.mjs`, `node.exe scripts/frontend-check.mjs typecheck`, 격리 build; frontend 격리 서버 대상 `npm.cmd run test:e2e`. LIVE_STAC는 명시 opt-in이다.

이번에는 읽기/메타데이터 진단만 실행했다. Node stdin 진단 종료0: 값 대신 존재/활성 여부만 출력, 위 config/status GET4건 HTTP200. 파일 조사 명령은 종료0, 초기 `git status --short` 포함 조사 명령은 종료1(`not a git repository`); Git diff 근거 없음. 공식 문서 조회 성공. pytest/build/브라우저·실제 Kakao/NASA 인증 호출은 미실행이며 과거 TEST_REPORT 통과를 이번 통과로 재사용하지 않는다. 전문 스킬/하위 에이전트 사용 없음. 변경은 이 보고서 한 파일뿐이다.

리더 결정 필요: 로컬 영속 저장의 키 관리/보존기간과 추가 의존성, P1 포함 회차 범위, USGS/CDSE 실제 인증을 진행할 계정·권한 준비 여부. 준비가 없으면 해당 요구는 미충족으로 남긴다. 추가 조사/구현을 스스로 시작하지 않고 대기한다.

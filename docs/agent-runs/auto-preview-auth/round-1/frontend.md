# Frontend 보고 — 자동 미리보기·제공처 연결

2026-10-30 · 회차1 · 구현 완료 / TypeScript·독립 큐 검증 통과 / 브라우저 E2E는 실행 환경 제한으로 QA 인계.

## 읽은 계약과 변경 소유권

공통 brief, leader-plan, planner, frontend-task, 루트/프런트 AGENTS, 최신 README·TEST_REPORT와 실제 관련 코드를 확인했다. Next 로컬 문서 `frontend/node_modules/next/dist/docs/01-app/01-getting-started/05-server-and-client-components.md`, `03-api-reference/01-directives/use-client.md`에 따라 브라우저 API는 Client Component의 effect에서 사용했다. 전문 스킬·하위 에이전트·위임은 사용하지 않았다.

수정 파일은 다음 소유 범위뿐이다.

- `frontend/src/lib/useProviderAccess.ts`
- 새 `frontend/src/lib/providerPreviewQueue.ts`
- `frontend/src/components/ProviderPreview.tsx`
- `frontend/src/components/EarthdataConnection.tsx`
- `frontend/src/app/globals.css`
- 기존 `frontend/tests/media-access.spec.ts`, `frontend/tests/earthdata-auth.spec.ts`
- 이 역할 보고서

백엔드·scripts·실제 .env·다른 역할 문서·새 QA 테스트는 수정하지 않았다. 서버 재시작·production build도 실행하지 않았다.

## 구현과 API 계약

- IntersectionObserver의 실제 교차 여부로 구독한다. 화면 밖/사용자가 숨긴 미리보기는 자동 구독하지 않으며, 대기 구독 취소·마지막 구독자 이탈 시 요청 abort를 수행한다. StrictMode 재구독을 위해 취소를 microtask까지 유예한다.
- provider/collection/id/인증 generation의 JSON 복합 키로 목록·상세·비교를 공유한다. 전역 inspect 동시 최대2, 재사용 TTL90초(서버 receipt 만료 5초 전 중 짧은 값), 미사용 캐시 최대60건·보고서 문자열 추정 1MiB를 적용한다. 화면에서 사용 중인 보고서·이미지는 각 구독자의 UI 상태이며 미사용 캐시와 구분한다. 클라이언트가 이미지 바이트를 Blob 캐시하지 않는다.
- 자동 inspect body는 `asset_keys:[]`, `include_preview:true`다. 원본 확인/다운로드는 기존 명시 동작으로 유지한다. 미리보기 경로는 `/api/media/previews/`, 원본 수신 경로는 `/api/media/downloads/`의 same-origin 상대 경로만 수용한다.
- 초기 접근 확인 버튼을 제거했다. 대기/수신·제공처 실패·표시·숨김 상태와 명시 재시도/보기/숨기기/browse 저장을 제공한다. 이미지 오류는 가시 상태에서 공유 큐와 컴포넌트 양쪽의 복구 제한을 적용해 강제 session 준비 후 자동 재검사를 최대1회만 수행한다. 이후에는 명시 재시도가 필요하다. 숨김 상태는 인증 변경에도 유지한다.
- media/session 준비는 single-flight, 최대60초 또는 서버 만료 5초 전까지 재사용하며 영구 Promise 캐시를 제거했다. 이전 서버의 ready-only 응답도 30초 TTL로 호환한다. HTTP409 `MEDIA_SESSION_REQUIRED`는 강제 준비 후 inspect 1회만 재시도한다. 병렬409의 이미 갱신된 session revision은 재사용한다.
- 인증 변경 시 session 준비와 공유 요청을 abort하고 캐시를 폐기한다. generation 검사로 늦은 응답을 차단한다. 원본 hook은 장면·밴드·인증 문맥이 다른 report를 렌더링하지 않는다. 다른 탭에는 비밀 없는 임의 변경 신호만 localStorage로 전달하고 status는 변경 시 1회 확인한다. 자동 로그인 이동·주기 polling은 없다.
- Earthdata status의 실제 `storage`, `storage_message`, `connection_expires_at`, `access_token_expires_at`, `refresh_available`를 표시한다. 이전 응답의 선택 필드는 누락을 허용한다. 제공처 status는 배열/키 객체 및 잘못된 선택 필드를 방어적으로 처리한다. DPAPI/메모리/저장소 미지원과 NASA/USGS/CDSE를 구분하고, 만료·철회·저장소 변경에 따른 재연결 가능성을 알린다. provider endpoint가 없으면 기존 Earthdata status를 유지한다.
- 기존 E2E는 클릭 대신 scroll로 자동 표시를 확인하도록 수정했고 API route fixtures를 유지했다. 실제 제공처 LIVE 테스트는 `LIVE_STAC=1`일 때만 실행한다.

## 실행한 검증과 실패

| 명령/검증 | 종료 코드 | 실제 결과 |
|---|---:|---|
| root `node.exe scripts/frontend-check.mjs typecheck` | 0 | 구현 중·최종 검사 통과. 최종 재검사 통과 |
| frontend `node.exe node_modules/@playwright/test/cli.js test tests/media-access.spec.ts tests/earthdata-auth.spec.ts --list` | 0 | 두 파일 11개 수집 성공. 테스트 실행 성공을 뜻하지 않음 |
| root Node stdin + TypeScript transpileModule + vm + node:assert의 TEST ONLY 큐 harness | 0 | 최종 5개 검증 그룹 통과(2.12초). 실제 모듈을 메모리에서 transpile하고 fetch/EventTarget/시간을 제어. 테스트 코드를 제품에 추가하지 않음 |
| 격리 dev 3043 / `.next-frontend-auto-preview` 시작 | 1 | Next 내부 child-process fork에서 `spawn EPERM`. 서버 시작 안 됨 |
| 격리 focused Playwright, 아래 명령과 동일 인자 | 1 | 10개 fixture 실행 준비 후 WorkerHost fork의 `spawn EPERM`. 브라우저·assertion 실행 전 실패, 통과0으로 보고 |

큐 harness의 최종 검증: 동일 Item 중복 병합, 동시2 상한, queued 취소, 마지막 구독자 abort, StrictMode 해제→즉시 재구독 요청1, 인증 변경 뒤 늦은 성공 응답 폐기, TTL90초 뒤 재조회, session TTL/single-flight, 자동 body가 preview-only인지 검사, 409 후 준비·1회 retry, 반복409 중단, 이미지 receipt 복구 최대1회와 이후 명시 retry, 65개 순차 처리 뒤 초기 캐시 퇴출. 이는 fixture 단위 검증이며 실제 HTTP/이미지 디코딩/DOM 가시성/실제 로그인 검증이 아니다.

실행 실패의 부가 기록: 첫 격리 서버 시작용 `node -e`는 PowerShell의 따옴표 전달로 SyntaxError/종료1이었다. 이후 stdin으로 바꿔 실행했으며 Next와 Playwright 모두 실제 `spawn EPERM`에 도달했다. 승인 재요청·샌드박스 우회·사용 중 서버 종료는 하지 않았다. 빌드/전체 E2E/LIVE_STAC/실제 NASA 인증/실제 Kakao 조회는 이 역할에서 실행하지 않았다. 새 스크린샷도 생성하지 못했다.

## QA 인계

QA의 별도 dist/port 서버에서 아래 focused 검증과 독립 auto-preview E2E·전체 검증을 실행해야 한다. 이번 역할에서 E2E 통과나 실제 browse 표시 성공을 주장하지 않는다.

```powershell
# frontend, QA가 준비한 격리 서버 주소 사용
$env:E2E_BASE_URL='http://127.0.0.1:<QA-port>'
$env:E2E_OUTPUT_DIR='test-results-auto-preview-qa'
node.exe node_modules/@playwright/test/cli.js test tests/media-access.spec.ts tests/earthdata-auth.spec.ts --grep-invert LIVE
```

특히 viewport 밖 요청0, 다중 표시 요청1, 장면 변경/탭 변경/로그아웃 중 수신 격리, 숨김 후 자동 재표시 없음, 실제 이미지 오류 뒤 복구1회, 모바일 배치, 자동 원본 요청0을 브라우저 요청수와 표시로 확인해야 한다. 실제 인증·다운로드 성공은 별도 권한/계정 준비와 실검증이 필요하다. 구현 완료 후 추가 범위를 스스로 착수하지 않는다.


## 같은 단계 리더 보완 — 명시 다운로드·browse 저장의 receipt 만료 복구

리더의 추가 지시에 따라 같은 회차·소유 범위에서 보완했다. 위 변경 목록에 `frontend/src/components/ManagedAssetAccess.tsx`를 추가한다. 백엔드·scripts·새 독립 QA 테스트는 수정하지 않았다.

### 동작과 한도

- **원본은 사용자가 원본 다운로드를 누른 경우에만** `receiveMediaFile()`을 호출한다. 자동 preview 큐·단순 접근 확인은 원본 GET을 시작하지 않는다. 기존 receipt가 만료 응답을 반환하면 정확히 같은 provider/collection/Item와 클릭한 선택 Asset 하나만 `asset_keys:[key]`, `include_preview:false`로 다시 확인하고, 성공한 새 same-origin receipt로 수신한다. 같은 파일의 중복 클릭은 ref 잠금으로 차단한다.
- receipt 갱신은 사용자 클릭당 논리적 재검사 최대1회, receipt GET 최대2회다. 재검사 자체에 기존 `MEDIA_SESSION_REQUIRED` 협상이 발생하면 이미 정한 session 재준비·POST 1회 재시도만 적용한다. 재검사 후 권한 없음·다른 Asset·다른 장면·외부 URL이면 새 파일 GET을 실행하지 않는다.
- 현재 backend의 HTTP404 `detail.code:MEDIA_RECEIPT_INVALID`와 `error.code` 형태를 모두 처리한다. 코드 없는 이전 서버의404/410도 최대1회만 재확인한다. 제공처401/403·쿼터·네트워크 장애·부분 수신은 자동으로 전체 전송을 반복하지 않는다. 반복 만료는 “접근 갱신은 1회만 시도했습니다. 접근 확인 후 다시 시도하세요.”를 파일 상태에 표시한다.
- **browse 저장을 링크에서 버튼으로 변경**했다. 클릭 후 실제 응답과 이미지 형식·전체 바이트를 확인한 Blob만 브라우저 저장에 넘긴다. 알려진 `receipt_expires_at`이 지났으면 오래된 URL을 먼저 받지 않고 preview-only 재검사1회 후 저장한다. 만료 시각이 없으면404/410 receipt 실패 후1회 복구한다. 실패는 상태 문구로 표시하고 추가 저장은 사용자 클릭이 필요하다. 이미지 표시용 자동 복구 한도와 이 명시 저장 동작의 한도는 각각 별도다.
- 파일 수신은 원본256MiB·browse8MiB, 클릭 작업 전체120초 상한이다. Content-Length뿐 아니라 실제 스트림 누적 바이트도 검사하고, 부분/빈 본문·잘못된 이미지 MIME이면 저장하지 않는다. 브라우저로 넘기는 receipt는 검증된 `/api/media/{downloads|previews}/{receipt}` 상대 경로이며, fetch redirect는 차단한다.
- 장면·선택 밴드·인증 변경/언마운트는 진행 중 원본 수신·갱신을 취소하고 늦은 응답을 저장하지 않는다. browse 숨기기·인증 변경·언마운트는 진행 중 browse 저장을 취소한다. 원본 갱신은 전체 report를 교체해 자기 수신을 중단시키지 않으며 성공한 receipt만 해당 화면 문맥에서 재사용한다.
- 파일 수신 완료 문구는 브라우저에 저장 작업을 넘겼다는 뜻이다. 사용자의 실제 디스크 저장 결과·제공처 권한·영구 연결 성공을 보증하지 않는다. 실제 원본/로그인은 검증하지 않았다.

### 추가 테스트와 실제 실행 근거

기존 `frontend/tests/media-access.spec.ts`에 **7개 E2E fixture**를 추가했다: 만료 원본의 같은 Asset 재검사·다운로드 성공, 반복 만료의1회 제한, 갱신 중 인증 변경 취소, 갱신 중 밴드 해제 취소, 만료 시각이 알려진 browse 저장, expiry 없는 browse404 복구, browse 반복 만료 중단. 클릭 전 원본 전송0과 정확한 inspect body·receipt GET 순서를 함께 검사한다. 기존 browse 저장 접근성 검사는 버튼으로 수정했다.

| 추가 실행 | 종료 코드 | 실제 결과 |
|---|---:|---|
| root `node.exe scripts/frontend-check.mjs typecheck` | 0 | 최종 추가 구현·18개 테스트 TS 검사 통과 (3.42초) |
| frontend `node.exe node_modules/@playwright/test/cli.js test tests/media-access.spec.ts tests/earthdata-auth.spec.ts --list` | 0 | 두 파일 **18개 수집**, 기존11+추가7. 실제 브라우저 실행 아님 |
| root Node stdin + TypeScript transpileModule/vm/node:assert의 명시 전송 fixture harness | 0 | **20개 검사 통과** (0.55초). 실제 새 함수를 메모리에서 실행 |

20개 전송 검사는 같은 Asset 원본 성공/반복 만료,401 재시도 없음·재연결 신호, 갱신 후 권한 거부, 외부 URL/다른 Item/다른 Asset 거부, browse 기한 만료 선갱신/404 복구/반복 실패 제한, 잘못된 MIME, 부분 본문, 원본 Content-Length 상한, browse 무길이 스트림 상한, 갱신 중 인증/외부 abort, 잘못된 초기 URL4종을 확인했다. fetch·응답은 명시 TEST ONLY이며 실제 제공처 수신 근거가 아니다.

추가 harness의 첫 실행은 PowerShell stdin 인코딩 때문에 한국어 정규식이 손상되어 SyntaxError/종료1이었다. 정규식을 ASCII Unicode escape로 고쳐 위20개 검사가 종료0으로 실행됐다. 앱 소스의 한국어는 UTF-8 파일에서 직접 읽었다.

앞선 단계의 Next/Playwright child-process `spawn EPERM` 제한 이후 서버·브라우저 실행 조건 변경이 없으므로 이번 보완의 브라우저 실행은 재시도하지 않았다. QA의 격리 서버에서 위18개 중 LIVE 제외 **17개 fixture**, 새 독립 auto-preview 검사와 전체 회귀를 실행해야 한다. 실제 LIVE_STAC·NASA 원본·사용자 로그인·production build는 이 역할에서 여전히 미실행이다. QA가 browse 저장을 확인할 때 `getByRole('button',{name:'미리보기 이미지 저장'})`를 사용해야 한다.

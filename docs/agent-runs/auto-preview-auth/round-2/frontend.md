# Frontend — 회차2 최종 수정 보고

2026-10-30 · 최종 두 번째 구현 사이클. logout 503·명시 재시도·현재/다른 탭 UI 무효화만 수정했다. 구현·TypeScript·의미 있는 fixture 검증 완료, 실제 브라우저 검증은 환경 제한으로 미실행이다.

## 적용한 지침과 소유 파일

`round-1/analysis.md`, `round-2/frontend-task.md`, `round-2/leader-plan.md`, 공유 brief, 프런트 AGENTS와 Next 로컬 `use-client.md`, 현재 README·TEST_REPORT 및 실제 Auth logout 응답을 읽었다. 전문 스킬·하위 에이전트·위임은 사용하지 않았다.

수정은 다음 네 파일뿐이다.

- `frontend/src/components/EarthdataConnection.tsx`
- `frontend/tests/earthdata-auth.spec.ts`
- `frontend/src/lib/providerPreviewQueue.ts`: 과제에서 허용한 비밀 없는 탭 신호의 최소 확장만. 기존 큐·전송·재시도 알고리즘은 변경하지 않았다.
- 이 `round-2/frontend.md`

백엔드·환경변수·scripts·미디어 컴포넌트·다른 역할 문서는 수정하지 않았다. 새 기능·세 번째 구현 사이클은 착수하지 않았다.

## 실제 동작과 실패 의미

1. 로그아웃 시작 시 연결 표시를 해제하고 파일 접근·진행 요청·캐시를 `notifyAuthChange('unconfirmed')`로 무효화한다. 503 또는 실패 응답에서도 다시 무효화하며 `connected:false`, `storage_disposed:false`, 서버의 문자열 `message`를 읽어 **디스크 폐기 미확인**을 표시한다. 모든 지속 쓰기 실패와 durable record만 성공한 경우의 차이는 서버가 준 안내를 그대로 유지한다. 응답 오류·비정상 JSON·네트워크 실패·15초 제한도 성공으로 표시하지 않는다.
2. 미확인 상태에서는 **연결 폐기 다시 시도** 버튼을 유지한다. HTTP-only 쿠키를 프런트에서 읽거나 지우지 않으며 같은 브라우저의 same-origin POST로 서버가 보존한 쿠키를 다시 보낸다. 자동 logout 재시도·로그인 이동·status polling은 없다. 명시 동작 뒤 status를 1회 재조회하며 다른 탭의 신호에서도 재조회한다.
3. 미확인 상태는 일반 연결 status와 분리해 보존한다. status가 늦게 `connected:true`를 반환하거나 추가 `storage_disposed:true`를 담아도 폐기 성공으로 바꾸지 않는다. NASA 연결 표시·갱신·새 로그인 경로와 제공처 목록의 NASA 연결 표시도 미확인 동안 차단한다. ref 기반 요청 잠금, abort와 요청 버전으로 중복 클릭·외부 탭 변경·언마운트 뒤 늦은 결과를 보호한다.
4. 미확인 해제는 **명시 logout 응답의 HTTP 성공 + `connected:false` + boolean `storage_disposed:true`**에만 허용한다. 이미 실패한 대상은 현재 서버의 `cleanup_required:false`와 boolean `revocation_recorded`도 요구한다. `revocation_recorded:false`인 정상 폐기도 성공할 수 있으며, 이 값 자체를 폐기 성공으로 사용하지 않는다. `session_missing:true` 또는 `cleanup_required:true`는 성공으로 처리하지 않는다. 현재 Auth는 SID 없는 요청을503으로 거부한다. 새 필드 없는 이전 서버의 쿠키 없는200은 이전 실패 대상의 성공으로 덮지 않고 미확인을 유지한다.
5. 탭 간에는 `{nonce, logout:'unconfirmed'|'disposed'}`만 전달한다. 사용자·SID·토큰·서버 오류 본문은 저장하거나 전달하지 않는다. 미확인 여부만 localStorage의 `'1'` 플래그로 보존해 새 탭/새로고침도 경고를 유지한다. 일반 auth 변경이나 status 조회는 이 플래그를 지우지 않는다. 다른 탭에서 검증된 **명시 logout 성공**을 통지했을 때만 같은 미확인을 해제한다. 신호 수신은 재송신하지 않아 탭 간 반복 루프가 없다.
6. 메모리 모드에서 **재시작 시 다시 연결**과 로그인 유지에 운영자의 명시 opt-in 설정이 필요함을 짧게 안내한다. 비밀·토큰 입력 UI는 추가하지 않았다. 서버 status와 logout의 선택 필드는 타입/유한 날짜 범위를 검사하고 잘못된 React 자식 값을 무시한다.

## 테스트 변경과 실제 실행

기존 Earthdata E2E 2개를 현재 폐기 응답 계약에 맞추고 **7개를 추가해 총9개**다. 503 뒤 표시·신호·재조회, 반복503→명시 재시도 성공, 늦은 connected status, 네트워크/파서/쿠키 누락/legacy200, 다른 탭·새로고침의 미확인 보존과 명시 성공 통지를 검사한다. 기존 제공처 API fixture는 유지했다.

| 실행 | 종료 코드 | 실제 결과 |
|---|---:|---|
| root `node.exe scripts/frontend-check.mjs typecheck` | 0 | 최종 TypeScript 통과, 4.16초 |
| frontend `node.exe node_modules/@playwright/test/cli.js test tests/earthdata-auth.spec.ts --list` | 0 | **9개 수집**, 0.69초. 브라우저 assertion 실행 아님 |
| root Node stdin + TypeScript transpileModule/vm/node:assert의 컴포넌트·실제 큐 탭 신호 harness | 0 | **16개 검증 통과**, 최종0.68초 |

Harness는 실제 수정 TSX와 큐 모듈을 메모리에서 transpile하고 fetch·hook state/effect·JSX 트리·EventTarget·공유 localStorage broker를 제어했다. 검증 항목은 메모리 opt-in 안내,503의 신호·연결 해제·재조회·미확인, 반복503, 명시 재시도 성공, 네트워크 실패, malformed logout/status 선택 필드, 쿠키 누락, legacy 성공 응답 보류, 잘못된 message 타입, 상충하는 cleanup 플래그, 늦은 status, ref 중복 클릭 잠금, 외부 신호로 취소된 요청의 늦은 성공 폐기, 탭 간 큐 구독 무효화·미확인 전달, 새 화면의 경고 복원, 다른 탭의 명시 폐기 성공 통지다. 이는 **fixture 상태 전이 검사이며 실제 React DOM·브라우저·HTTP·NASA 인증 검증이 아니다.**

실패도 기록한다. 편집 중 PowerShell 문자열 분할이 파일 접두부를 훼손해 첫 typecheck가 TS1002/TS1128·종료1이었다. 접두부를 복구했고 이후 최종검사는0이다. 첫 VM harness의 자식 탐색 기본 인자 때문에 재귀 RangeError·종료1이었으며, harness 탐색기를 고친 뒤16개 검증을 통과했다. 이 중간 실패를 통과 근거로 재사용하지 않는다.

## QA·리더 인계와 남은 제한

기존 `spawn EPERM`/UI 주소 제한의 변경 근거가 없어 과제 지시에 따라 build·서버 시작·브라우저를 반복하지 않았다. 운영 서버 재시작·전체 E2E·실제 SID/쿠키 보존·DPAPI/ACL·저장소 권한 복구·NASA 측 철회는 이 역할에서 검증하지 않았다. QA의 허용된 격리 환경에서 위9개 E2E와 변경된 서버 계약을 함께 실행해야 한다.

쿠키가 이미 사라졌거나 저장소의 모든 쓰기가 실패하면 이 UI의 재시도만으로 이전 grant의 영구 폐기를 보장할 수 없다. 원래 연결 정보 부재를 성공으로 덮지 않으며 운영자의 저장소 권한 확인·격리와 NASA 측 철회를 별도로 안내한다. localStorage가 차단되면 같은 탭의 경고·무효화는 유지하지만 탭 간 통지/새로고침 보존은 보장하지 못한다. 클라이언트 경고 플래그는 인증·서버 폐기 기록의 대체가 아니다.

현재 Auth의 `session_missing`·`cleanup_required`·`revocation_recorded` 계약을 읽어 연결했으므로 추가 백엔드 변경은 요청하지 않았다. 현재 단계의 담당 수정은 여기서 종료한다.

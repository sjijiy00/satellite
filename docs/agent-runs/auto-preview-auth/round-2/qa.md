# QA — 회차 2 최종 독립 검증

2026-10-30. 핵심 백엔드와 TypeScript는 통과했다. 실제 브라우저·production build·실제 ACL/인증 검증이 없어 전체 요구 완료를 확정할 수 없다. 제품 코드는 수정하지 않았다.

## 독립 실행

| 명령 | 종료 | 결과 |
|---|---:|---|
| backend `..\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --disable-warnings tests/test_earthdata_auth.py tests/test_earthdata_persistence.py tests/test_media_access.py` | 0 | **65 passed, 1 skipped**, 1 warning. 기존 테스트의 저장소 내부 상속 ACL 임시 fixture 사용. 실제 제공처 로그인 아닌 TEST ONLY grant. |
| root `node.exe scripts/frontend-check.mjs typecheck` | 0 | strict TypeScript 통과. |
| frontend `node.exe node_modules/@playwright/test/cli.js test tests/auto-preview.spec.ts tests/media-access.spec.ts tests/earthdata-auth.spec.ts --list` | 0 | 3개 파일 **31개 수집**(LIVE 1개 포함). 수집은 브라우저 실행이 아니다. |

최종 Auth 보고에 따르면 전체 backend는 **359 passed, 17 skipped**였으며 마지막 성공 응답 메타데이터 수정 이전 실행이다. 해당 변경 이후 Auth 담당 focus는 68 passed, 1 skipped였다. 전체 검사는 이번 QA가 독립 실행하지 않았다.

## 핵심 검토

`test_earthdata_persistence.py`의 통과한 테스트는 v2 및 legacy 거부, journal 성공·DB 삭제 실패 후 별도 프로세스의 이전 SID 복원 차단, 모든 지속 쓰기 실패 시 503·쿠키 보존·복구 후 명시 재시도, 비활성 전환 뒤 폐기, SID 누락 시 미확인, refresh 중 logout을 포함한다. 실제 Windows DPAPI 암복호화와 별도 프로세스 확인을 사용하되 ACL 설치는 mock했다. 실제 ACL 설치 테스트는 현재 권한 제한으로 skip이다.

`EarthdataConnection.tsx`는 logout 시작 시 큐 무효화와 불확실 상태를 전달하고, version/abort로 늦은 status를 억제한다. `providerPreviewQueue.ts`는 기존 구독에 인증 변경을 통지하고 다른 탭 이벤트를 전달한다. `earthdata-auth.spec.ts`에서 503 반복·명시 재시도, 지연 status, 다른 탭, 누락 SID와 legacy 응답을 수집했다. 최종 코드에서 다른 탭의 명시 폐기 성공 신호도 확인했다. Frontend 담당은 별도 VM 상태 fixture 16개 통과를 보고했으며 이는 독립 QA 실행이나 실제 브라우저 증거가 아니다. 이 UI/큐 상호작용은 실제 브라우저에서 실행되지 않았다.

## 잔여 문제와 한계

- 모든 지속 쓰기가 실패하면 현재 프로세스에서만 사용을 차단하며 재시작 후 이전 grant 복원을 막을 수 없다. `test_all_persistent_writes_fail_cookie_kept_and_retry_after_repair`도 복구 전 다른 프로세스 복원 가능성을 확인한다. 사용자 재시도 또는 저장소 격리·제공처 철회가 필요하며 영구 폐기 성공이 아니다. 이전 포맷은 자동 삭제하지 않고 격리를 요구한다.
- 회차1 build와 Playwright는 `spawn EPERM`으로 각각 빌드 및 브라우저 assertion 전에 중단됐다. 동일 환경이므로 재실행하지 않았다. 미리보기 표시·동시성·모바일·503 UI·다른 탭의 실제 브라우저 동작과 production build는 미검증이다. Node 자식 프로세스 검사도 회차1에서 실패했다. 환경 제한을 우회하거나 운영 서버를 종료하지 않았다.
- 실제 ACL 설치를 포함한 DPAPI 저장 준비·서버 재시작 복원, NASA 사용자 로그인/refresh/원본 다운로드, USGS/CDSE 신규 인증, LIVE_STAC는 미검증이다. USGS/CDSE 신규 원본 인증은 미구현이다. 실제 사용자 `.env`는 읽거나 수정하지 않았다.
- 리더의 회차1 분석은 Kakao 실제 API HTTP 200과 REGION 1건을 보고한다. 이는 운영 서버 설정 반영이나 앱 지도 동작 확인이 아니다. 이번 QA는 실조회하지 않았다.

위임과 전문 스킬 사용 없음. QA 테스트는 이번 회차에 수정하지 않았다.

## 최종 변경 후 독립 재검사

최종 Auth·Frontend 보고와 현재 응답 메타데이터 및 다른 탭 폐기 신호 코드를 확인했다. 위 backend focus 명령을 한 번 다시 실행해 **68 passed, 1 skipped**, warning 1, 종료 0을 확인했다. 성공 응답의 `revocation_recorded` 확인도 해당 테스트에 포함된다. root `node.exe scripts/frontend-check.mjs typecheck`도 한 번 재실행해 종료 0이었다. 전체 359개와 Frontend 상태 fixture 16개는 담당자 보고이며 독립 실행 결과가 아니다. 동일 EPERM build·브라우저 실패는 반복하지 않았다.


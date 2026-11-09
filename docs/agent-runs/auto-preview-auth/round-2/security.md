# Security — 회차 2 최종 검토

회차 2 계획, 회차 1 보안 보고, 현재 Auth·Frontend 코드와 테스트, `docs/AUTOMATIC_PREVIEWS.md`를 읽었다. 이후 공개된 Auth·Frontend 최종 보고서와 최종 프런트 코드를 재검토했다. 제품·테스트 변경이나 직접 테스트 실행은 하지 않았다.

## 판정 및 잔여 사항

- **회차 1 높음 문제는 조건부로 해결:** `backend/app/earthdata_store.py:386-401`은 DPAPI 폐기 기록을 먼저 원자 교체·재독 검증한 뒤 DB 행을 삭제한다. 이 기록이 성공하고 DB 삭제만 실패하면 503이지만 `load`의 기록 검사(`:346-351`)로 재시작 후 동일 SID 복원을 거부한다. 관련 fixture `backend/tests/test_earthdata_persistence.py:352-369`는 별도 프로세스 복원 거부를 검사하도록 작성되어 있다. 직접 실행한 증거는 아니다.
- **남는 한계 — 모든 지속 쓰기 실패:** journal도 쓸 수 없으면 이전 grant는 재시작 뒤 복원될 수 있다. `earthdata_auth.py:132-143,176-185,458-492`는 현재 프로세스에서 SID를 차단하고 503과 cookie 보존으로 재시도를 허용하며 영구 폐기를 보장하지 않는다고 알린다. 테스트 `:372-395`는 이 한계와 복구 후 재시도를 명시한다. 이는 문서화된 물리적 실패 조건으로, 완료된 폐기라고 보고하면 안 된다. 필요시 저장소 격리와 NASA 측 철회가 별도로 필요하다.
- **정정 — 다른 탭 상태 잔류 지적 철회:** 최종 `EarthdataConnection.tsx:77-85,114-117`은 명시 logout 성공의 `disposed` 신호를 받은 다른 탭에서 미확인 ref와 경고를 지운다. 이전 지적은 최종 코드에 적용되지 않는다. 신호 전달은 localStorage 가용성에 의존한다. Frontend 보고의 16개 VM fixture 검증에는 이 상태 전이가 포함되지만 실제 브라우저 실행이나 이 역할의 독립 테스트는 아니다.

## 검토 근거

- 명시적 `EARTHDATA_PERSIST_SESSIONS=1`만 영속화를 켠다(`earthdata_auth.py:98-105`). 비활성 모드도 기존 저장소가 있으면 logout에서 별도 폐기를 시도한다(`:102-129,463-477`). 식별 cookie가 없으면 이전 grant 폐기를 확정하지 않고 503을 반환한다.
- `earthdata_store.py:165-223,225-245,265-295`는 v2 metadata·설정 fingerprint·store ID 및 별도 DPAPI journal을 확인한다. 기존 형식은 자동 복원/마이그레이션하지 않고 격리 요구하며, journal 누락·손상·복호 실패는 준비 실패로 복원을 차단한다. 사용자 ACL, 파일·DB·행·journal 크기/개수 상한, flush·원자 교체·재독 검증이 코드에 있다. 실제 ACL 설정과 비정상 종료/전원 손실 내구성은 독립 검증하지 않았다.
- `EarthdataConnection.tsx:51-66,89-132`는 logout 시작 시 같은 탭의 표시·요청을 무효화하고 실패 시 불확실성을 유지한다. `providerPreviewQueue.ts:16-41`은 다른 탭에 비밀 없는 변경 신호를 전파하고 큐를 폐기한다. 늦은 status는 버전과 불확실 상태로 제한하며 503을 성공으로 표시하지 않는다. localStorage 사용 불가 시 다른 탭 전달은 보장되지 않는다. E2E fixture는 존재하나 실제 브라우저 실행은 검토하지 않았다.
- `docs/AUTOMATIC_PREVIEWS.md`의 opt-in, v1 격리, 모든 지속 쓰기 실패 한계는 코드의 기본 계약과 부합한다. 다만 저장소 손상 시 문서의 '다시 연결'만으로 해결되는 것은 아니며, v2 journal 복구/격리와 기존 제공처 권한 철회가 필요할 수 있다. 현재 코드가 이를 자동 복구한다고 해석하면 안 된다.

## 검증 한계

이번 역할은 읽기 전용 코드 검토다. 회차 1 보고의 DPAPI fixture 결과는 ACL mock을 사용했으며 실제 ACL 준비는 권한 제한으로 검증되지 않았다. Auth 최종 보고는 담당 테스트 68 passed/1 skipped 및 앞선 전체 359 passed/17 skipped를 기록하며, 전체 실행 뒤 마지막 변경은 담당 테스트로 확인했다. Frontend 최종 보고는 typecheck와 VM fixture 16개 통과 및 Playwright 9개 수집을 기록한다. 이는 다른 역할의 보고이며 이 역할이 직접 실행한 결과가 아니다. 실제 NASA 계정·권한·토큰 갱신, 다른 OS 사용자와 실제 브라우저는 검증되지 않았다. 승인 재요청·우회나 추가 구현 루프는 수행하지 않았다.


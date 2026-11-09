# Security — 회차 1 최종 독립 코드 검토

`brief.md`, `leader-plan.md`, auth/media/frontend 보고서와 현재 구현·테스트를 읽었다. **보안 핵심 미해결: 디스크 폐기 실패 후 재시작 시 이전 grant의 복원을 막는 지속적인 폐기 기록이 없다.** 이 검토에서는 실제 `.env`, 계정, 코드와 테스트를 변경하지 않았고 테스트도 실행하지 않았다.

## 발견 사항

1. **높음 — 폐기 실패가 재시작을 넘어 유지되지 않음 (코드상 확인).** `backend/app/earthdata_store.py:172-174,233-239`의 delete I/O 실패는 `ready=False`를 현재 인스턴스에만 기록한다. `earthdata_auth.py:120-123,155-172,246-254,415-434`에서 logout 또는 refresh 실패 후 삭제도 실패하면 기존 DB 행이 남을 수 있고, 재시작 후 저장소 준비가 다시 성공하면 같은 SID를 가진 요청이 그 행을 복원할 수 있다. 현재 브라우저 cookie 삭제가 이미 복사된 cookie를 무효화하지는 않는다. 특히 503 응답에서 cookie도 삭제하므로 같은 브라우저의 재시도는 원래 SID 없이 성공할 수 있어 기존 행 폐기를 증명하지 못한다. 폐기 실패를 재시작 이후에도 확실히 차단하는 지속적 폐기/격리 설계를 마련하고, 삭제 실패→권한 복구→재시작→기존 SID 재사용 및 재시도 검증이 필요하다. 실제 악용이나 디스크 고장 재현은 하지 않았다.
2. **중간 — logout 503 후 화면 상태 (코드상 확인).** 서버는 `earthdata_auth.py:429-434`에서 `storage_disposed=false`와 503을 반환한다. `frontend/src/components/EarthdataConnection.tsx:69-83`은 비정상 응답을 일반 실패로 처리하므로 성공 메시지를 내지는 않지만, 서버가 cookie를 지운 뒤에도 이전 연결 표시와 다른 탭/큐 상태가 남을 수 있고 디스크 폐기 실패의 구체적 의미를 보여주지 않는다. 실패 내용을 표시하고 인증 상태를 재조회·무효화하되 폐기 완료로 표현하지 않아야 한다.
3. **낮음 — DNS 검증과 연결 사이의 시간차 (미검증 가설).** `backend/app/provider_transfer.py:39-61,97-107`은 허용 호스트의 DNS 공개 주소를 검증하지만 HTTP 연결은 별도로 해석할 수 있다. DNS 변조가 가능한 조건에서의 재바인딩 위험은 미재현이다. 연결 주소 고정 또는 연결 시 검증을 검토한다. HTTPS/호스트·경로 허용목록, redirect 재검사 및 교차 호스트 토큰 제거는 존재한다.

## 확인한 경계와 남은 검증

- `earthdata_store.py:34-59,114-150,176-229`는 사용자 범위 DPAPI, SID 해시와 설정 fingerprint 결합, 제한된 저장 크기, epoch 만료 및 SQLite 트랜잭션을 사용한다. 암호화/저장 실패는 평문 fallback하지 않는다. 손상된 개별 행은 삭제가 성공하면 해당 행만 거부한다(`:201-231`); 삭제나 DB 자체 오류는 전체 저장소를 불가로 만든다. 기존 손상 테스트는 다른 정상 세션이 계속 동작하는지까지 입증하지 않는다.
- `earthdata_auth.py:210-245`는 refresh 중 logout의 메모리 세션 재생성을 막고 회전 grant 저장 후 반환한다. 삭제 실패의 재시작 문제는 위 1번에 별도로 남는다. 공개 callback은 `:38-54`에서 차단하며 다중 프로세스는 지원하지 않는다.
- `media_access.py:226-246,285-329`에서 공개 browse는 OAuth 토큰 없이 가져오고 자동 요청의 빈 asset 목록은 원본 probe를 실행하지 않는다. receipt는 owner와 필요한 인증 SID에 묶인다. `providerPreviewQueue.ts:53-71,141-155`는 자동 preview만 요청하고 동시 2개로 제한한다. `:78-109`와 `ManagedAssetAccess.tsx:21-30,36-42`에서 명시 다운로드 후 만료 receipt 재검사는 최대 1회다. 브라우저 E2E 및 실제 제공처로 독립 재현하지 않았다.
- 제공처 상태는 `earthdata_auth.py:437-454`에서 NASA, USGS/AWS, CDSE 인증을 분리하며 공개 검색과 원본 권한을 구분한다. `scripts/server-env.mjs`의 서버 비밀 분리와 `backend/app/log_safety.py`의 access log 마스킹은 유지되지만 모든 프록시/예외 로그와 실제 빌드 산출물의 무비밀 상태를 독립 검증하지 않았다.

## 실행 근거와 한계

이번 역할은 읽기 전용 검토만 수행했다. 다른 역할 보고의 담당 테스트 47 passed/1 skipped, 큐 fixture 검증과 typecheck는 그 역할의 실행 결과이며 이 검토의 독립 실행 결과가 아니다. Auth 보고의 실제 DPAPI 검증은 ACL 설정을 mock했고 실제 ACL 준비는 권한 거부로 skip되었다. Frontend 보고의 Playwright/서버 실행은 `spawn EPERM`으로 assertion 전에 실패했다. 승인 재요청이나 우회는 하지 않았다. 실제 NASA 로그인·토큰 갱신·파일 권한, 다른 OS 사용자, 실제 브라우저 격리는 미검증이다.

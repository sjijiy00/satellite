# Backend/Auth — 최종 회차2 결과

2026-10-30 · Codex · 지정한 폐기 영속성·명시 opt-in 수정 완료. 실제 ACL 준비와 NASA 계정 인증은 검증하지 못했으며 영구 접속·모든 조건의 영구 폐기를 보장하지 않는다.

## 변경 범위

변경한 소유 파일은 `backend/app/earthdata_auth.py`, `backend/app/earthdata_store.py`, `backend/tests/test_earthdata_auth.py`, `backend/tests/test_earthdata_persistence.py`, `backend/.env.example`, 이 보고서뿐이다. `main.py`·미디어 API 계약, media_access/provider_transfer, 프런트, server-env 변수명/allowlist는 유지했다. 실제 `.env` 읽기·출력·수정, 새 자격증명, 추가 의존성, 위임·전문 스킬·서버 재시작은 없었다.

## 필수 수정 결과

- **명시 opt-in:** `EARTHDATA_PERSIST_SESSIONS=1`에서만 신규 영속 저장·복원을 한다. 미설정/빈 값/0/그 외 값은 최대8시간 메모리 모드이며 status에 그대로 표시한다. 끄면 이미 캐시한 영속 grant도 재사용하지 않는다. 껐다가 켰을 때 검증 가능한 v2 저장소만 복원하며, 이전 포맷을 허용하는 효과는 없다.
- **새 포맷 v2:** 새 저장소에만 SQLite `user_version=2`와 version/fingerprint/store_id 메타데이터를 설정한다. 기존 DB는 먼저 read-only로 검사한다. 무버전 legacy grants, 미지원 버전, 다른 앱 설정, 불완전한 저장소는 자동 복원·마이그레이션·초기화·삭제하지 않는다. `storage_isolation_required`와 고정 안내를 반환한다. 기존 포맷 파일이 바이트 단위로 보존되는 것을 검사했다.
- **별도 폐기 기록:** DB 옆 `sessions.sqlite3.revocations`는 DPAPI로 보호되며 sid_hash/앱 fingerprint/store_id/기한을 결합한다. 임시 파일 쓰기 → flush/fsync → 같은 디렉터리에서 Windows `MoveFileExW(REPLACE_EXISTING | WRITE_THROUGH)` → 실제 저장 바이트와 복호 내용 읽기 검증 → DB DELETE → 별도 조회로 삭제 확인 순서다. DB 삭제 전에 기록이 성공해야 다음 단계로 간다. raw sid/token은 기록하지 않는다.
- **복원·저장 전 검사:** load/save와 메모리 캐시 재사용도 journal 유효성·해당 SID 폐기를 검사한다. 기록 손상·누락·읽기 실패·다른 store/app 결합은 fail-closed다. 읽지 못한 journal을 빈 것으로 덮어쓰지 않는다. 실제 ACL 또는 DPAPI 준비 실패도 제품 코드에서 우회하지 않는다.
- **실패 의미:** journal 성공 + DB 삭제 실패는503, `storage_disposed=false`, `revocation_recorded=true`다. 현재 프로세스의 SID 사용을 차단하고 새 프로세스도 해당 SID를 거부한다. 모든 지속 쓰기가 실패하면503/recorded=false와 재시작 후 영구 폐기 불가능 조건을 명시한다. 두 실패 모두 **쿠키를 삭제하지 않아 원래 SID로 명시 재시도**할 수 있다. 삭제 확인 성공 때만200/disposed=true와 쿠키 삭제다. journal 여부도 성공 응답에서 정확히 반환한다.
- **비활성 전환 후 폐기:** persistence=0이어도 기존 영속 파일이 있으면 검사·폐기를 시도한다. legacy/다른 앱 설정이면503·격리 안내이며 성공으로 넘기지 않는다. 앱 설정이 없으면403으로 거부하고 쿠키를 보존한다. 원래 쿠키가 없는 요청은503/disposed=false이며 이전 실패의 폐기 성공을 주장하지 않는다.
- **상한:** 기존 최대1000 grant/DB80MiB/암호문64KiB/연결30일, 메모리8시간을 유지했다. journal은 최대1000 폐기 항목/256KiB/항목30일이며, 폴더 항목은 임시 파일을 포함해16개로 제한한다. journal 갱신 때 만료 항목을 정리한다. 프로세스 내 SID 거부도 최대1000개이며 초과하면 거부를 버리지 않고 현재 프로세스의 인증 사용을 차단한다. 다중 서버 프로세스와 공개 callback은 지원하지 않는다.

## 실행 검증

모든 OAuth·refresh 응답과 grant는 TEST_ONLY fixture다. DPAPI는 실제 Windows API지만 저장소 동작 테스트의 ACL 설치 함수는 명시적으로 mock했다. 실제 OS 권한 실패는 별도 검사에서 skip으로 남기고 제품 코드의 준비 조건을 완화하지 않았다.

| 실행 | 종료 코드 | 결과 |
|---|---:|---|
| backend 담당 pytest 최초 | 1 | 63 passed / 1 skipped / 2 failed. 프로세스 내 SID 거부 추가로 기존 `reauthorization_required` 표시와 메모리 거부 처리 회귀 발생; 수정 |
| 담당 pytest 재검사 | 0 | 65 passed / 1 skipped |
| 추가 필수 경계 검사 후 담당 pytest | 0 | 68 passed / 1 skipped |
| 전체 pytest, 아래 작업 폴더 fixture 등록 방식 **1회** | 0 | **359 passed / 17 skipped**, 1089 warnings, 97.63초 |
| 전체 실행 뒤 성공 응답의 `revocation_recorded` 표시를 보강한 최종 담당 pytest | 0 | **68 passed / 1 skipped**, 2 warnings, 7.61초. 마지막 코드 변경까지 포함 |

담당 최종 명령:

```powershell
# backend 디렉터리
..\.venv\Scripts\python.exe -m pytest -q --disable-warnings --tb=short -rs tests/test_earthdata_auth.py tests/test_earthdata_persistence.py tests/test_media_access.py
```

전체 명령은 회차1의 TEMP 권한 오류를 반복하지 않도록, 테스트 전용의 새 무작위 작업 폴더 fixture를 등록했다. 다른 테스트 소스는 수정하지 않았고 제품 ACL을 우회하는 실행이 아니다.

```powershell
# backend 디렉터리
@'
import sys
import pytest
sys.path.insert(0, 'tests')
import test_earthdata_persistence as auth_fixtures
raise SystemExit(pytest.main(['-q', '--disable-warnings', '--tb=short', '-rs'], plugins=[auth_fixtures]))
'@ | ..\.venv\Scripts\python.exe -
```

검사한 핵심 경로:

- DB delete 실패 주입 → journal 성공 확인 → DB에 원 grant가 남음 확인 → **별도 Python 인터프리터에서 복사 SID 연결 거부** → 삭제 권한 복구를 모사한 재시도 → 확인된 삭제·쿠키 제거.
- 모든 journal 쓰기 실패 주입 → DB delete 미실행·503·쿠키 보존·현재 프로세스 access_token 거부. **이 조건에서 새 인터프리터가 옛 grant를 복원할 수 있음을 확인**해 영구 폐기 불가능 조건을 검증했다. 쓰기 복구 후 같은 SID 재시도는 폐기 성공하고 새 인터프리터에서도 거부된다.
- 기본 미설정의 실제 콜백 fixture는8시간 쿠키와 메모리 status, 파일 생성 없음. opt-in/v2/version99/legacy/재활성화/다른 앱 설정/미설정 앱/비활성화 후 폐기와 원래 쿠키 부재 검사.
- journal 손상·삭제·읽기 실패의 캐시/load/save 차단, journal 항목·파일 수 상한, refresh 중 logout, 기존 브라우저 격리·state/redirect·회전·갱신 거부 회귀.

조사 중 rg1건은 backend 작업 디렉터리에서 경로에 backend 접두사를 중복 지정해 실패했다. 뒤의 pytest는 종료0이었으며 rg 실패를 검사 성공 근거로 쓰지 않았다. Node/build/브라우저는 이 역할에서 회차2 재시도하지 않았다. 기존 EPERM 조건을 반복하거나 통과로 재사용하지 않았다.

## 잔여 한계와 운영 인계

1. **17 skip = LIVE_STAC16 + 실제 ACL 준비1.** 현재 실행 토큰은 private ACL 설정(WRITE_DAC)에 권한 거부가 있어 전체 저장 준비 검사는 skip이다. 실제 DPAPI 암호문·새 인터프리터 검증을 실제 ACL을 포함한 운영 서버 재시작 검증으로 표현하지 않는다. 정상 권한의 로컬 실행 환경과 QA/보안의 독립 검토가 필요하다.
2. **모든 지속 쓰기 실패는 영구 폐기로 해결할 수 없다.** 해당 응답은 현재 프로세스 차단만 보장한다. 원래 쿠키를 유지한 채 권한 복구 후 다시 요청하고 성공 응답을 확인해야 한다. 필요하면 서버를 종료해 저장소 전체를 확인 가능한 보호 위치로 격리하고 NASA 측 승인/토큰 철회도 별도로 확인한다. 정상 상태 조회나 쿠키 없는 요청은 과거 폐기 성공의 증거가 아니다.
3. **legacy 격리 절차:** 서버를 종료하고 `backend/.private/earthdata` **폴더 전체(DB·journal·관련 파일)를 별도 보호 위치로 수동 격리**한다. 원본을 조용히 삭제하거나 legacy DB에 버전만 붙이지 않는다. 새 빈 저장소에서 명시 opt-in과 OAuth 연결을 다시 수행한다. 격리는 해당 서버에서의 접근 분리이며 NASA 전체 계정 토큰 철회가 아니다. DB만 복사하거나 옛 journal로 되돌려 폐기 기록을 잃지 않아야 한다. 악의적인 전체 저장소 롤백·전원 장애를 실험한 것은 아니다.
4. 실제 NASA 앱 등록·사용자 로그인·provider refresh·파일 권한 검증, USGS/CDSE 원본 인증, 운영사이트 반영은 미실행/미연결이다. 공개 callback·다중 worker·무기한 연결은 지원하지 않는다. 마지막 응답 메타데이터 보강은 최종 담당68개로 확인했으며 전체359개를 그 변경 이후 재실행했다고 주장하지 않는다.

회차2에 새로 확인한 공식 근거: [Microsoft MoveFileExW](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-movefileexw)의 교체·WRITE_THROUGH 플래그를 사용한다. NASA SSO·사용자 범위 DPAPI 근거는 회차1 보고서의 직접 조회 자료를 유지한다. 추가 구현/세 번째 수정 루프는 시작하지 않았다.

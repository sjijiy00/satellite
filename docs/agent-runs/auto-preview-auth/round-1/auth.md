# Backend/Auth — 회차1 결과

2026-10-30 · Codex · 구현과 담당 검증 완료, 운영 권한/실제 인증 검증은 미완료.

## 구현 결과

- `earthdata_auth.py`: 로컬 브라우저별 OAuth 흐름에 영속 저장·지연 복원을 연결했다. Windows 로컬 기본 활성, `EARTHDATA_PERSIST_SESSIONS=0`은 기존 최대8시간 메모리 모드다. Windows 외 기본은 메모리이며 명시적 영속 활성은 준비 실패로 표시한다. 공개 callback은 계속 차단한다.
- 새 `earthdata_store.py`: stdlib ctypes **현재 Windows 사용자 범위 DPAPI**와 SQLite 트랜잭션을 사용한다. 별도 평문 암호키 파일은 없다. DB 키는 sid SHA-256이며 원본 sid/access/refresh token은 평문 저장하지 않는다. 암호문에도 sid hash를 결합해 다른 브라우저 행으로 복사한 grant를 거부한다. 앱 ID/secret/정확한 callback의 fingerprint를 암호화 entropy와 레코드 검사에 사용한다.
- 저장 위치는 고정 `backend/.private/earthdata/sessions.sqlite3`다. 현재 OS 사용자와 SYSTEM으로 제한하는 비공개 상속 ACL 설치 및 임의 비사용자 데이터의 DPAPI 왕복·DB 쓰기로 준비를 확인한다. 준비/쓰기 실패는 조용히 메모리 성공으로 바꾸지 않는다. 연결 시작은503, 콜백은 failed이며 상태에 `persistence_ready`, `storage_error`, `storage_message`를 반환한다.
- 최대1000세션, 암호문64KiB/건, DB80MiB, 연결 최대30일(고정 기한, refresh로 연장하지 않음)이다. epoch 기한과 프로세스 내부 monotonic 기한을 검사한다. 준비/저장 시 최대1000행 범위에서 만료·다른 설정을 정리한다. 유휴 상태의 즉시 물리 삭제를 수행하는 별도 타이머는 없다. SQLite rollback journal도 암호문만 포함하며 트랜잭션 종료 시 정리한다.
- 만료/손상/복호 실패/설정 변경은 복원을 거부한다. 로그아웃·refresh 거부는 디스크도 삭제한다. 갱신 중 로그아웃은 완료된 응답으로 연결을 되살리지 않는다. refresh 잠금·회전 저장·401 후 최대1회 재시도 계약을 유지한다. grant/session/앱 설정 repr에 비밀을 표시하지 않는다.
- `main.py`: `/media/session`을 Media 담당의 `session_response(request)`에 위임했다. `GET /auth/providers/status`는 provider_id/configured/connected/integration/storage/message만 제공한다. Earth Search 공개 검색과 USGS/AWS 인증, Copernicus 공개 검색과 CDSE 원본 인증을 구별하고 미연결 인증을 성공으로 표시하지 않는다. 기존 Earthdata status에는 저장 방식·연결/access 만료 epoch·갱신 가능 상태를 호환 추가했다.
- `server-env.mjs` allowlist에 persistence 스위치만 추가했다. 프런트/빌드의 EARTHDATA 변수 제거와 프로세스 환경 우선순위를 유지했다. `.env.example`에는 빈 항목과 설명만, `.gitignore`에는 `/backend/.private/`만 추가했다.

## 변경한 소유 파일

`backend/app/earthdata_auth.py`, 새 `backend/app/earthdata_store.py`, `backend/app/main.py`, `backend/tests/test_earthdata_auth.py`, 새 `backend/tests/test_earthdata_persistence.py`, `scripts/server-env.mjs`, `scripts/server-env.test.mjs`, `backend/.env.example`, `.gitignore`, 이 보고서.

실제 사용자 `.env`를 읽거나 출력/수정하지 않았다. media_access/provider_transfer/프런트/다른 역할 문서는 수정하지 않았다. 위임·하위 에이전트·전문 스킬·새 의존성·서비스 재시작은 사용하지 않았다. Git 조사 명령은 종료1(`not a git repository`); Git diff/commit 근거는 없다.

## 실행 검증과 실패 기록

명령은 별도 표기가 없으면 backend 작업 디렉터리 기준이다. 모든 OAuth 성공/거부/refresh 응답과 grant는 TEST_ONLY fixture이며 실제 NASA 계정 인증이 아니다.

| 명령 | 종료 | 실제 결과 |
|---|---:|---|
| `..\.venv\Scripts\python.exe -m pytest -q --disable-warnings tests/test_earthdata_auth.py tests/test_earthdata_persistence.py tests/test_media_access.py` 최초 | 1 | 기존 검사34통과, 새 검사10 setup 오류. 기존 `%TEMP%/pytest-of-aicam` 읽기 권한 거부 |
| 동일 대상 `--basetemp=.private/auth-pytest-run1 --tb=short` | 1 | 부모 폴더 부재로 setup 실패 |
| 부모 생성 후 `--basetemp=.private/auth-pytest-run2 --tb=short` | 1 | pytest의 mode0700 임시폴더에 현재 실행 토큰 접근 거부; 종료 정리도 실패 |
| 새 테스트 전용 상속 ACL 임시폴더 fixture 도입 후 동일 대상 | 1 | 44통과/1skip이나 테스트 자체 SQLite 조사 연결 미종료로 teardown5오류. 조사 연결을 명시적으로 닫도록 수정 |
| 최종 `..\.venv\Scripts\python.exe -m pytest -q --disable-warnings --tb=short -rs tests/test_earthdata_auth.py tests/test_earthdata_persistence.py tests/test_media_access.py` | 0 | **47 passed, 1 skipped**, 2 warnings, 2.45초. 최종 epoch 만료 보강까지 포함 |
| 전체 `..\.venv\Scripts\python.exe -m pytest -q --disable-warnings --tb=short -rs` | 1 | **292 passed, 17 skipped, 43 errors**, 99.80초. 다른 기존 테스트의 동일 TEMP setup 권한 오류; 해당 파일 수정하지 않음 |
| 아래 임시폴더 fixture 등록 방식의 전체 pytest | 0 | **338 passed, 17 skipped**, 1089 warnings, 87.29초. 뒤이은 작은 epoch 만료 보강은 위 최종 담당47개로 검증 |
| root `node.exe --test scripts/server-env.test.mjs` | 1 | 테스트 자식 프로세스 시작 자체 `spawn EPERM`. 같은 조사 명령 뒤 rg 성공 때문에 셸 최종 코드는0이었으나 Node 결과는 실패 |
| root `node.exe --test --test-isolation=none scripts/server-env.test.mjs` | 1 | **13 passed, 2 failed**. 신규 persistence allowlist/프런트 제거 검사 통과. 기존 실제 child-process 환경 검사와 disposable Git 검사만 자식 프로세스 생성 실패 |
| 위 Node 명령에 `--test-name-pattern '^(?!(actual child\|gitignore excludes)).*'` 추가 시도 | 1 | 이 실행 환경에서는 실패2개가 그대로 실행됨; 13통과/2실패를 통과로 재분류하지 않음 |

전체 pytest의 안전한 작업 폴더 임시경로 검증 명령(다른 테스트 파일 수정 없음):

```powershell
@'
import sys
import pytest
sys.path.insert(0, 'tests')
import test_earthdata_persistence as auth_fixtures
raise SystemExit(pytest.main(['-q', '--disable-warnings', '--tb=short', '-rs'], plugins=[auth_fixtures]))
'@ | ..\.venv\Scripts\python.exe -
```

실제 Windows DPAPI로 TEST_ONLY 토큰의 암호문 검사와 **별도 Python 인터프리터의 복원**, 브라우저 격리, 콜백 저장/30일 쿠키, 갱신 회전/거부/동시 갱신 병합, 로그아웃 중 갱신, 암호문 행 이동 거부, 손상/만료/설정 변경/저장 실패/상한을 확인했다. 이 테스트들은 **ACL 설치 함수만 명시적으로 mock**했으며 암호화/복호화는 실제 Windows DPAPI다. 다른 OS 사용자/키 손실은 복호 실패 주입이며 실제 두 번째 OS 사용자 로그인 검증이 아니다. 별도 이식 가능한 실패 테스트의 protect/unprotect mock도 실제 DPAPI 성공 증거로 쓰지 않았다.

## 미검증·인계 사항

1. **비공개 ACL 설치를 포함한 완전한 저장 준비는 현재 토큰에서 차단됨.** 변경 없는 실제 `_restrict_directory` 호출은 Windows 오류5(권한 거부), 해당 준비 검사는1 skip이다. 앱 코드는 이런 경우 fail-closed로 영속 연결을 거부한다. 실제 로컬 런처 사용자에게 해당 디렉터리의 ACL 설정 권한(WRITE_DAC)이 있는 환경에서 준비·서버 재시작까지 추가 검증해야 한다. 테스트의 ACL mock을 제품 코드에 적용하지 않았다.
2. 실제 Earthdata 앱 등록/사용자 로그인·refresh 발급·LP DAAC 파일 접근은 **미실행**이다. 무기한 연결을 보장하지 않는다. 로그아웃은 사이트 저장 grant 폐기이며 NASA 전체 SSO/계정 토큰 폐기가 아니다. 삭제 I/O 실패 시503과 `storage_disposed=false`를 반환하고 현재 프로세스는 저장소를 불가 상태로 둔다. 디스크 폐기 실패를 성공이라고 보장하지 않으며 저장 권한 복구 후 확인이 필요하다.
3. **단일 서버 프로세스만 지원**한다. SQLite 트랜잭션이 있다고 다중 worker refresh/폐기 조정이 구현된 것은 아니다. 상태에도 `multi_process_supported=false`를 표시한다. 공개 callback은 미허용이다.
4. Node15개 전체 통과, 프런트 typecheck/build/E2E와 운영 서버 반영은 이 역할의 완료 근거가 아니다. QA/리더가 통합 검증할 사항이며 현재 프로덕션 서버를 재시작하지 않았다. LIVE_STAC16개는 opt-in 미실행이고 별도 ACL1개를 합쳐17 skip이다.
5. USGS/CDSE 신규 원본 인증은 미연결이다. 새 비밀번호/개인 User Token 설정이나 범용 제공처 로그인은 추가하지 않았다. Kakao 실제 설정/위치 조회도 이 역할에서 검사하지 않았다.

## 공식 근거

2026-10-30 직접 조회: [NASA SSO](https://urs.earthdata.nasa.gov/documentation/for_users/sso_process_overview)는 서버 코드 교환과 발급 access/refresh token 흐름을 설명한다. 실제 발급 응답 없이 성공을 추정하지 않는다. [Microsoft CryptProtectData](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata)에 따라 machine-scope 플래그 없이 사용자 범위와 UI 금지를 사용하며 OS 할당 결과를 LocalFree로 해제한다. ACL은 [Microsoft SDDL](https://learn.microsoft.com/en-us/windows/win32/secauthz/security-descriptor-string-format)의 보호 DACL을 사용한다. [USGS M2M](https://www.usgs.gov/media/files/m2m-application-token-documentation), [CDSE 토큰 문서](https://documentation.dataspace.copernicus.eu/APIs/Token.html)는 제공처별 준비 안내에만 연결했다.

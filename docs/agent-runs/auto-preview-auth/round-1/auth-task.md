# 단계2 Backend/Auth

brief.md, planner.md, leader-plan.md와 공통 지침을 읽고 구현. 역할과 작업을 패널에 짧게 표시. 결과는 auth.md. 다른 세션에 위임 금지.

단독 소유: backend/app/earthdata_auth.py, 새 DPAPI 저장모듈, backend/app/main.py, backend/tests/test_earthdata_auth.py 및 새 영속 관련 테스트, scripts/server-env.mjs 및 .test.mjs, backend/.env.example, .gitignore. 사용자 실제 .env는 읽어 출력/수정하지 말 것. media_access/provider_transfer/프런트 수정 금지.

구현: Windows 로컬 per-browser Earthdata OAuth 연결이 서버 재시작 후 지속되도록 stdlib ctypes Windows DPAPI user-scope 암호화 + 원자파일 또는 sqlite 저장. raw token/sid 평문 저장 금지(키는 sid hash). epoch 만료/설정 fingerprint, 손상/다른 OS user/키복호 실패 fail-closed, 로그아웃과 refresh 중 로그아웃의 디스크 폐기, refresh rotation/최대1회 재시도 유지, token repr/log 가림. 현재 앱 단일 process만 지원하고 public callback 차단 유지. 동시 프로세스 영속 저장은 미지원으로 정확히 표시. 최대 세션 수/파일 크기/기간(최대30일)/prune 상한. 불필요 새 의존성 추가 금지. persistence enabled 기본 Windows 로컬 true, `EARTHDATA_PERSIST_SESSIONS=0` 명시 비활성 지원, 상태에서 실제 저장준비/실패 구분; 가능하다면 user 데이터 없는 안전한 준비 검사. 영속 저장 실패를 연결성공으로 과장하지 말 것.

main.py media_session route는 media_access.session_response(request)에 위임하도록 수정(다른 담당이 함수 구현). `GET /auth/providers/status` provider_id earth-search/copernicus/nasa-cmr 등의 설정/연결/integration/storage/message만 반환. 기존 Earthdata status는 저장 방식/연결 만료/갱신가능 등 backward-compatible 추가. USGS/CDSE 인증 미연결을 성공으로 표시하지 않으며 공식 준비 안내 제공. username/password/개인 User Token을 .env에 새로 만들거나 받지 않음. 공식 OAuth 1회 로그인과 provider refresh 사용.

테스트: 기존 OAuth per-browser/state/redirect/refresh/logout 유지, 실제 DPAPI 가능한 Windows에 암호문·재시작 복원 의미 있는 검사, 손상/만료/다른설정/logout 중refresh/실패/비활성 검증. 저장 함수 mock 테스트와 실제 DPAPI 구분. server-env allowlist에 persistence 설정만 허용, frontend 제외 유지. .env.example 값 없이 설명.

NASA 공식 근거 https://urs.earthdata.nasa.gov/documentation/for_users/sso_process_overview . 필요하면 실제 문서 확인. 테스트 명령/종료코드·미검증 실제 인증 포함해 auth.md 작성 후 종료.

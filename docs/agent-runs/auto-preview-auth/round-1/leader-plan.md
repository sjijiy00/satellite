# 리더 확정 계획 — 회차1

기획자 planner.md 검토 완료. 사용자 요구의 핵심은 클릭 없는 실제 browse 표시와 로컬 로그인 연결 유지다. 현재 연결된 3개 제공처·4개 컬렉션의 검색/선택을 유지한다. 알려지지 않은 위성/URL/인증을 자동 지원한다고 주장하지 않는다.

## 단계2와 소유권

- Backend/Auth, pane1:0.2: earthdata_auth.py, 새 Windows DPAPI 영속 세션 모듈, main.py, backend/tests/test_earthdata_auth.py 및 새 영속 테스트, scripts/server-env.mjs·server-env.test.mjs, backend/.env.example, .gitignore. auth-session 영속·안전 갱신·제공처 연결 상태 API. media_access/provider_transfer는 수정 금지.
- Backend/Media, pane1:0.10: media_access.py, provider_transfer.py, landsat_access.py, 관련 backend/tests/test_media_access.py. 세션 generation/만료 응답·receipt 복구 및 제공처 읽기 안전성. main.py 소유하지 않음: route 변경 필요하면 리더에게 보고.
- Frontend, pane1:0.3: useProviderAccess.ts·새 preview 큐 모듈, ProviderPreview.tsx, EarthdataConnection.tsx, 필요시 ManagedAssetAccess.tsx·types/CSS, 기존 media-access·earthdata-auth E2E. 자동 가시성·공유 큐·중복 제거·만료1회 복구·연결 상태. 최신 Next 로컬 문서 확인.
- Security, pane1:0.6: read-only 검토와 security.md. 코드 수정 금지. 구현 초안과 완료 후 근거 검토.
- QA, pane1:0.5: 구현 완료 후 독립 전체 검증과 필요한 새 E2E만. 별도 build 디렉터리/포트 사용, 운영 서버 종료 금지.
- 디자이너 생략: 기존 컴포넌트 내 상태/문구 변경으로 프런트 담당이 수행.
- 토론 A/B pane1:0.7/8, 분석관 pane1:0.9는 단계2 완료 후 실행.
- 리더 소유: README·TEST_REPORT·PROVIDER_MEDIA_ACCESS 문서와 과제 인계. 실제 .env 값 보존. 새 NASA/USGS/CDSE 자격증명 없음, 실제 인증 성공 주장 금지.

## 인터페이스

기존 media/session·inspect·preview·download 경로 유지. media/session 응답은 Backend/Auth가 Backend/Media의 새 `session_response(request)`로 위임한다. Backend/Media가 이 함수를 구현하며 response에 ready, session_generation(서버 생애 비밀 아닌 랜덤 ID), expires_at(UTC epoch 초)를 반환한다. preview 성공에 receipt_expires_at(UTC epoch 초)를 추가한다. 기존 필드는 호환 유지. 새 미디어 세션을 부여해야 하는 inspect는 요청을 진행하지 않고 HTTP409 `{error:{code:'MEDIA_SESSION_REQUIRED',message:...}}`와 안전한 세션 cookie를 반환하도록 하여 프런트가 단일 session준비 후 1회 재시도한다. 원본 전송 자동 실행 없음.

Auth: `GET /auth/providers/status`를 추가하고 제공처별 configured/connected/integration/storage/message와 현재 제한을 비밀 없이 반환한다. NASA는 기존 per-browser OAuth와 refresh를 Windows DPAPI 저장으로 재시작 후 복원한다. `EARTHDATA_PERSIST_SESSIONS=1`일 때만 디스크 영속, 미설정 기본은 현재 Windows 로컬 환경에 한해 활성 또는 명시 opt-in 중 보안 리뷰와 구현 근거로 선택·문서화. 공개 callback은 계속 차단. Windows 아닌 환경은 메모리/미지원 상태를 정확히 반환. 세션 최대30일 이하, 실제 access_token 만료는 provider 발급값 준수. 로그아웃/철회/갱신 중 로그아웃은 디스크도 삭제. cookie는 토큰을 담지 않음.

USGS M2M/CDSE 신규 원본 인증은 실제 계정/권한과 파일 매핑 검증 없이 연결됐다고 표시하지 않으며, 제공처 연결 상태와 공식 준비 절차를 동일 화면/문서로 안내한다. 본 회차에서 구현하지 않은 경로는 미지원으로 명시한다. 이 결정은 미설정 상태에서 범용 .env 비밀번호/타 제공처 토큰으로 우회하는 기능을 만들지 않기 위한 범위 결정이다.

## 스킬·프롬프트·검증

기획 결과에 따라 viewport/중복 요청과 세션 race를 완료 기준에 추가했다. 범용 코드 작업은 전문 스킬을 억지로 호출하지 않는다. 프런트는 로컬 Next docs, Auth는 NASA 공식 SSO/토큰 문서를 사용. 필요시 QA는 기존 Playwright 브라우저/스크린샷으로 실제 표시 확인. 각 역할이 실제 이용한 스킬/미사용을 보고.

단계2 후: 의미 있는 테스트, 전체 pytest, TS/production build, 환경격리 Node 테스트, 전체 E2E. fixture와 LIVE분리. 각 역할은 실패도 보고. QA·보안 통합 보고 이후 A/B가 장단점과 상대 반론을 각각1회 교환하고 분석관이 합의·이견을 분석. 회차1 완료기준 실패시 회차2에 남은 문제만 수정, 최대2회 유지.

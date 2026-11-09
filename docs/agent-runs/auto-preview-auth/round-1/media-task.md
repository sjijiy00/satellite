# 단계2 Backend/Media

brief.md, planner.md, leader-plan.md와 공통 지침을 읽고 구현. 결과는 media.md. 패널에는 역할/짧은 현재작업을 표시. 위임 금지.

단독 소유: backend/app/media_access.py, provider_transfer.py, landsat_access.py 및 backend/tests/test_media_access.py. main.py/Auth/프런트 수정 금지.

계약: media_access.session_response(request)를 구현. ready:true, session_generation(서버 생애 비밀 아닌 식별자), expires_at(UTC epoch초), 기존 HttpOnly cookie세팅. 다른 담당이 main route를 위임시킴. owner 갱신/최초 inspect 동시성 문제 해결: inspect에 valid media owner가 없으면 canonical/전송하지 말고 HTTP409 `{error:{code:'MEDIA_SESSION_REQUIRED',message:'미디어 세션을 다시 준비하세요.'}}` + 안전한 cookie 또는 session준비 요구. 클라이언트가 ready를 강제 갱신하고 1회 retry하도록 계약. 기존 직접 TestClient 시나리오는 명시 session준비로 업데이트. inspect 성공 preview에 receipt_expires_at epoch초 추가. 서버 기존 상한·유저격리·원관측 구분 유지.

검토: 로그인 토큰 갱신 상태와 preview receipt 만료 분리. 프런트 자동 복구가 가능하도록 필요한 안정적 오류 코드를 주되 타인 receipt 정보 노출 금지. 공개 썸네일과 보호원본 구분. 공개 preview는 유효한 인증이 없어도 사용 가능. 외부 URL/DNS/호스트변경시 인증헤더제거/경로 검증 유지. 사용자 원본 다운로드는 기존 명시동작으로만. 다운로드 재시작/원본 receipt 만료로 자동 전체수신을 반복하지 말 것.

USGS/CDSE 신규 인증을 임의 구현하지 말 것. 미설정/미연결 상태 정확히 유지. 현재 canonical/provider mapping과 public preview 결함이 발견되면 근거 있는 범위내 수정 가능. 테스트로 session race/restart/만료·타인격리·자동 preview 후 원본미요청·실패를 검증. 의미 있는 pytest 후 명령/코드/실연결여부 media.md에 남기고 종료. auth persistence 작업은 다른 세션이 병행.

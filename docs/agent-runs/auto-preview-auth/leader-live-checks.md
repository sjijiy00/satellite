# 리더 독립 확인

2026-10-30, 비밀값 출력·실제 `.env` 수정 없음.

- 파일의 GEOCODER_ENABLED 활성 및 Kakao REST 키 존재를 boolean으로만 확인. 기존 실행 backend8000와 web3000 config는 HTTP200이지만 ready=false/두 설정 누락으로 응답. 설정 파일과 기존 프로세스의 불일치 확인. 앱 반영은 재시작 후 별도 확인 필요.
- 고정 backend/.env를 읽는 기존 `childEnvironments`를 그대로 사용해 Node 메모리에서만 Kakao Authorization 헤더 구성. 공식 `https://dapi.kakao.com/v2/local/search/address.json`에 공개 지명 연천군의 exact 요청. 최종 HTTP200, total_count=1, address_type=REGION, REGION 결과1. 실제 키 값과 제공처 결과 본문을 출력/파일 저장하지 않음. 이는 키/지명 조회 실연결 성공이며 운영 앱의 설정 반영·UI 카메라 이동·AOI 확정 성공과는 구별.
- 첫 Node stdin 진단은 PowerShell 문자열 인코딩으로 한글이 보존되지 않은 상태에서 HTTP200/0건. 문자열을 ASCII Unicode escape로 지정한 최종 호출에서 위 1건을 확인. 최초0건을 실제 연천군 부존재나 키 실패로 판정하지 않음.
- NASA 앱 ID/secret/callback, USGS/CDSE 자격증명은 존재 여부만 확인했고 미설정. 실제 NASA 로그인/refresh/인증 원본 전송 미실행.
- Browser Use: 브라우저 access host unavailable. Computer Use 스킬을 읽고 native Chrome의 반환된 단일 창으로 관찰을 시도했으나 Windows 현재 URL을 충분히 확인할 수 없어 도구가 중단. 그 뒤 UI 입력을 중단했고 실제 브라우저 표시/스크린샷 검증 성공으로 기록하지 않음.
- 현재 운영 listen PID는 backend9156(8000), frontend13884(3000), 기존 launcher14192가 확인됨. 프로젝트 서버 종료·재시작은 아직 하지 않음.
- 새 코드의 TestClient 통합 점검: `/media/session` HTTP200, ready/generation/epoch 만료/HttpOnly cookie 확인; `/auth/providers/status` HTTP200, 기존 3개 제공처 상태 확인; 새 미디어 세션 없이 inspect HTTP409·MEDIA_SESSION_REQUIRED 확인. 외부 자료 요청 없는 로컬 통합 검사이며 실제 브라우저·제공처 로그인 검증과 구별.
- 최종 수정 중 운영 서버를 건드리지 않고 검증용 backend8015(PID36620)를 실행했다. 기존 `childEnvironments`의 허용 이름만 메모리에서 전달하고 Python uvicorn 단일 프로세스를 직접 실행했다. 키는 명령 인자·출력·파일로 전달하지 않았다. 실제 HTTP `/health`200, `/places/config`200/ready=true, `/auth/earthdata/status`200/configured=false/persistence_enabled=false/memory, `/auth/providers/status`200/기존3개 제공처를 확인했다.
- 검증용8015의 실제 앱 `POST /places/search`는 HTTP200, status=resolved, upstream_http=200, candidates=1, role=camera_only였다. 단독 공식 API 확인을 넘어 앱 서버 경유도 확인했으나 기존8000/3000 반영·브라우저 카메라 이동/AOI는 여전히 별도이다.
- 검증용8015에서 실제 NASA CMR `G3626199201-LPCLOUD`를 preview-only inspect했다. API200, preview available/upstream200/access_verified=true, 원본 assets=0. canonical granule/browse 수신 및 rasterio 이미지 디코딩 후 같은 출처 receipt 이미지 API200, 전체70963바이트를 수신했다. 실제 공개 이미지 경로 검증이며 화면 자동 표시·NASA 로그인·인증 원본·픽셀 QA 성공이 아니다. 토큰/receipt 값·서명 URL·공개 응답 본문은 결과 파일에 저장하지 않았다.
- 검증 후 소유한 exec 세션의 검증용8015 서버를 종료했다. netstat에서8015 listen이 없고 기존3000(PID13884)/8000(PID9156)이 그대로 listen임을 재확인했다. 이 종료 도구의 종료코드1은 Ctrl+C로 검증 서버를 중단한 결과이며 테스트 실패로 분류하지 않는다. 기존 운영 서버는 종료하지 않았다. 진행 중 분석·다운로드 확인 질문은 아직 답변 대기다.

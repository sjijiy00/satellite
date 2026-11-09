# 단계2 Security

brief.md, planner.md, leader-plan.md 읽고 인증 영속/자동미리보기 변경 보안검토. 결과는 security.md 하나만. 코드/실제.env 수정/비밀값출력/계정로그인/다른역할위임 금지. 현재 구현 병행중이므로 먼저 설계와 기존코드 위험을 검토하고 잠시 기다리지 말고 초안 보고. 리더가 구현완료 후 최종검토 재요청함.

핵심: Windows DPAPI OS-user encryption, sid hash·설정 fingerprint·epoch만료·원자저장·암호화실패 fail-closed·손상/크기상한, logout중refresh와 restart시 폐기, public callback차단/단일process제약, 자동preview request bound와 owner/receipt유저격리·Origin/SSRF/redirect·토큰로그유출, .env→backend only와 frontend/build no secret. USGS/CDSE/NASA 자격범위 분리.

파일/줄/구체재현 근거별 심각도/권고. 실제문제와 미검증/가설 구분. 새 전체보안체크리스트로 과제확장금지. 준비되면 패널에 '업무 완료! | Security | 초안 검토 완료'와 결과파일 남김. 독립코드검증은 최종재요청에서 수행.

# 단계2 QA — 독립 시나리오 작성

brief.md/planner.md/leader-plan.md와 하위지침을 읽고 새 frontend/tests/auto-preview.spec.ts 하나에 실제 사용자 행동을 확인하는 fixture E2E를 작성한다. 결과는 qa-draft.md. 다른 코드/기존테스트/실제.env 수정금지, 서버 종료/운영재시작 금지, 위임금지. 패널에는 역할/현재작업 한줄.

프런트/백엔드 구현 병행중. 지금은 테스트작성과 TS 구문확인까지만 하고 종료하라. build/전체테스트/서버실행은 리더가 구현통합후 다시 요청한다. 무한 대기/폴링하지 말 것.

요구 테스트: 별도 preview 확인 클릭없이 이미지 표시, 자동inspect는 include_preview:true와 asset_keys:[]만·자동원본요청없음, 같은장면카드/상세중복1회, IntersectionObserver viewport밖처리, 실패후명시재시도(무한루프없음), MEDIA_SESSION_REQUIRED 409후ready한번복구, image receipt404 1회복구후오류종료, 장면/인증변경중늦은응답폐기, 모바일overflow 없음. 실제현재 UI구조/기존media-access.spec.ts/helpers 참고하고 구현행위를 그대로복제하는테스트를 만들지 말 것. 각 테스트가 무엇을 보증하는지 명료하게.

NASA/USGS/CDSE actual로그인 모사성공을 실제성공이라고표현금지. 모든모의응답 TEST ONLY 명시. 실제네트워크에 의존하지 않는새테스트. 신규providerstatus/session응답은 backwardcompat구조유지. APIcontract가 아직불확실하면 읽은code근거와기다릴사항을qa-draft.md에기록. 테스트파일+draft만 쓰고 종료.

# QA 최종 검증 — 회차1

brief/leader-plan과 구현 보고 auth.md/media.md/frontend.md, 자신의 qa-draft.md 확인. auth보고작성중이어도 코드/테스트가거의완료되어 지금 검증가능. QA소유: 새 auto-preview.spec.ts와 qa.md 보고만. 다른기존테스트/제품코드수정금지. 새테스트오류는직접수정하고제품오류는리더에게보고. 위임금지.

1. 전체 backend pytest 실행. 임시폴더권한문제면 저장소내 logs/qa-temp를 `--basetemp`로 사용하되 pytest가 지우는 타겟은 직접검증한 task폴더만. -p no:cacheprovider. Auth담당이전체338passed/17skip보고를할예정이라면 중복실행을억지로늘리지말고 그근거읽고독립focuscritical검증과최종통합상태를확인.
2. root node scripts/frontend-check.mjs typecheck, node --test scripts/server-env.test.mjs. subprocess EPERM가나면 재승인·정책우회없이 실제실패를기록. 실제.env사용금지. fixture필터조건/비밀없는 backend.env설정검증.
3. 별도 dist `.next-auto-preview-qa`와 port3015/8015를사용한 production build/전체E2E를시도. 운영3000/8000 프로세스종료금지. 서버시작의childprocess EPERM가재현되면 불필요하게반복하지말고 build/브라우저assertions미실행으로명시. 실행가능한의미있는 queue/download Nodevmharness는프런트담당결과와함께구분.
4. 새E2E와기존media/Earthdata변경의strict타입/테스트수집확인, 인증generation늦은응답/receipt1회복구/동시2/viewport/원본자동0과추가다운로드명시복구테스트커버리지검토. 현재원본/browse저장은button으로변경중이므로기존test선택자갱신누락발견시보고.

LIVE_STAC미실행기본. 실제Kakao키는리더가나중에 config/실조회확인. NASA/USGS/CDSE사용자로그인미실행. Windows저장소ACL통합검증은sandbox권한제한이이미확인돼있으며실제DPAPI암호화roundtrip과전체ACL저장을구별.

결과는qa.md:명령/종료코드/실패·중간수정/미실행/실연결구분,필수미충족·제품오류구체근거,리더가완료판단할한계. 서버를직접띄웠다면본인이만든것만정리. 핵심상태를패널에표시하고종료.

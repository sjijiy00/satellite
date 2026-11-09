# QA 마지막 독립 검증

round-2/leader-plan.md와수정된코드를확인. Auth는65passed/1skipfocus통과후전체검증중,Frontend는TS통과/Earthdata9개수집후보고작성중. 현재코드에독립focus+TS만의미있게실행하고최종qa.md작성. 위임/제품코드수정금지. 자기기존auto-preview.spec.ts의오류만수정가능. 운영서버종료금지.

critical:신규format/legacy거부,DBdelete실패+journal성공후restartoldSID거부,allwritefail503cookie보존+복구후재시도,off전환후logout이전grant폐기,누락SID503/성공과미확인구분,refresh중logout,프런트503/다른탭/지연status와기존queue구독호환.

명령backend관련auth/persistence/media pytest(안전작업폴더fixture기존사용)와rootfrontendtypecheck,E2E collect. 기존동일EPERM환경의build/브라우저/Node하위프로세스실행을반복하지말고round1기록재사용·미검증명시. 마지막전체백엔드는Auth최종결과를근거로쓰고중복전체실행불필요. 실제ACL/로그인/다운로드미검증,리더Kakao실조회200REGION1과운영미반영구분.

코드상중요회귀나미충족은파일/테스트근거로짧게기록. 결과qa.md. 이번은마지막회차이므로문제를숨기거나새반복작업을만들지말고리더에게보고하고종료.

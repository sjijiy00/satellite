# Frontend 최종 수정 — 회차2

round-1/analysis.md와round-2/leader-plan.md확인. 이번소유는EarthdataConnection.tsx, frontend/tests/earthdata-auth.spec.ts와결과frontend.md만. 다른파일필요하면리더보고,위임금지. 짧은역할/현재작업표시.

로그아웃503 JSON본문의connected:false/storage_disposed:false/message를처리. 성공으로표현하지말고'디스크폐기미확인'구체안내. 서버는삭제실패시cookie를보존하도록변경되므로명시'연결폐기다시시도'버튼을유지해원래SID로재시도가능하게함. 응답503에서도현재연결표시를해제하고notifyAuthChange로미리보기/원본진행요청·캐시를무효화하고다른탭통지. status재조회. status/load가늦게응답해도폐기미확인메시지를성공으로덮지않음. 다른탭도폐기불확실성·연결표시낡음을인식하도록비밀없는신호만사용(필요한queue모듈최소확장은소유자인본인이계속담당가능하지만다른구현임의변경금지).

서버상태조회만으로storage_disposed실제성공이라판정금지. 명시logout응답storage_disposed:true일때만미확인해제. cookie없이이전실패를성공으로덮을위험도구분. failedlogoutnetworkorunknown이면성공메시지금지. parser유효성·busy·abort·같은화면상태보호.

기본persistoff로변경되어'메모리모드,재시작시다시연결'상태와명시opt-in설정이필요함을간단하게표시. .env비밀/구체token은UI입력받지않음.

테스트:503후실패의미/연결표시·queue이벤트무효화/반복503/실제명시재시도성공/늦은status응답에미확인보존. 기존연결fixture회귀. TypeScript·테스트수집과의미있는가능한단위검증. EPERM조건변화없으면build/browser반복금지. 수정/테스트/미검증을frontend.md에정직하게기록후종료.

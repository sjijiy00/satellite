# 회차2 — 최종 수정 사이클

회차1 기획·구현·QA·보안·양쪽상호토론·분석관 판정 완료. round-1/analysis.md를 근거로 계획/phase/prompt 변경. 전문 스킬 추가 없음: 일반 코드·기존 공식 근거·pytest/TS 사용. 새 디자인/미디어·제공처연결 작업은 없음. 회차2 종료 후 세 번째 구현 루프 없이 잔여개선만 사용자 보고.

필수 수정: 영속 세션 명시 opt-in, 이전 포맷 저장소의 조용한 복원 금지, 폐기 실패의 durable record/격리 가능한 경우 재시작 차단과 실패의 정직한 의미, logout503에서 cookie·UI·현재/다른탭 요청과캐시 무효화·재시도.

Auth pane2는 자기 기존 파일/테스트만, Frontend pane3는 EarthdataConnection.tsx와 해당 E2E만. QA/보안은 변경 완료 후 독립 검토. 토론 A/B는 마지막 결과를 상호1회 검토하고 Analyst가 최종 요구별판정. 기획/미디어/디자인 역할은 변경필요없는 범위이므로 기존근거재사용.

리더 결정: persistence는 `EARTHDATA_PERSIST_SESSIONS=1`일때만. 사용자는 로그인유지를 요청했지만 아직 NASA설정이없고 실제ACL/브라우저검증도차단되어, 기본으로未검증영속모드를켜두지않는다. 설정예시·선택시실제제한을문서화한다. 다른제공처미연결은미구현으로남긴다.

내구성: 새 store format/version을 도입해 회차1 legacy grants DB는 명시격리/폐기 전 자동복원하지않음(원본사용자자료를자동삭제하지않음). 새버전은 DB와별도의보호된 revocation journal을 먼저원자적기록하고 읽어검증한뒤delete. tombstone성공+DBdelete실패면503이지만재시작복원은막아야함. 모든지속쓰기실패면성공을주장하지않으며cookie를보존해명시재시도가가능하게하고현재프로세스에서연결사용을차단. 제공처철회/저장소격리가필요한잔여한계를문서와UI에구체화. 그런조건에서영구폐기가항상가능하다고주장하지않음.

비활성전환뒤logout도기존v2영속grant가있으면폐기를시도해야함. persistence=0은복원/신규저장을금지하되이전grant폐기를건너뛰어재활성화때부활시키지않음. 잘못된/옛저장포맷·revocation읽기/쓰기실패는복원fail-closed. token/sid는평문저장금지. bounded파일/기간/개수와OSuserACL/DPAPI기존제약유지.

검증은변경의미있는pytest+TypeScript+새503 E2E 수집과가능한fixture검증. 동일EPERM·UI주소정책차단조건이변하지않았으므로build/브라우저를무작정반복하지않음. 마지막전체백엔드는안전작업폴더fixture로1회. 운영사이트재시작은검토후진행중작업확인필요.

# Security 최종 검토 (같은 회차1)

구현 코드를 이제 독립검토하라. brief/leader-plan과 auth/media/frontend 보고서를 확인. auth.md는 작성중이면 코드·테스트로 먼저검토. 소유 파일 security.md만 업데이트. 실제.env/코드/테스트수정 금지, 위임금지.

새 earthdata_store.py, earthdata_auth.py의 실제 DPAPI 저장·폐기/refresh/logouts/restartfailclosed와 새 frontend queue/download수신 검토. 특히 디스크 삭제 실패 후 재시작에 old grant가 복원될 가능성, 손상된 한 세션이 globalstoredisable하는지, 익명/public browse가 OAuth문제로막히는지, provider status 정확성 확인. 구현에 있는 테스트 의미와 실제 실행증거 구별. 503 logout이면 실패를 성공으로표현하는지 확인. 원본의명시사용자동작후만료1회재검사·토큰/서명URL유출/automatic원본없음도검토.

검증시 sandbox환경 ACL설정 권한제한/Node spawn EPERM는 재승인·우회하지 말고 한계를기록. 보안 핵심 미해결과문서범위를 짧고근거있게정리해 최종security.md 작성후완료. 장단점토론인에게 넘길 보고다.

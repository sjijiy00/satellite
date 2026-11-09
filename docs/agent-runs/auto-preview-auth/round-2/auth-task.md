# Backend/Auth 최종 수정 — 회차2

round-1/analysis.md와round-2/leader-plan.md를읽고이번필수수정만구현. 파일소유권기존동일,실제.env수정/위임금지. 결과auth.md. 패널짧은역할/작업표시. 마지막사이클이므로불필요한새기능금지.

1. persistence는EARTHDATA_PERSIST_SESSIONS=1명시opt-in만. 기본메모리(8h),status정확히. 새storeformatversion을도입. 이전grants테이블legacyformat은자동복원/자동삭제하지않고준비실패와격리필요를고정안내. 새깨끗한저장소만버전설정. 사용자이전파일을조용히초기화/삭제금지.
2. 새포맷에서revocation journal을DB와별도보호파일로먼저원자적쓰기/flush/검증한뒤delete. revocation은sid_hash/fingerprint와기한으로묶고비밀없거나DPAPI보호,폴더권한/개수/크기/기간상한. load/save는revocation과journal가용성을검증. DB삭제실패해도journal성공했다면같은SID가재시작후거부돼야함. 삭제성공시에만storage_disposed=true; cleanupfailed는503. 모든지속쓰기실패면확실한폐기를보장할수없음을응답/보고에명시. 그때현재프로세스는세션을재사용하지않고cookie는삭제하지않아재시도에원래SID가남도록함. 옛cookie없는성공으로원래폐기를주장하지않음.
3. persistence=0전환뒤logout도이전영속grant가존재하면확인/폐기를건너뛰지말것. 미설정/다른app설정/legacy포맷은보수적으로fail-closed. 명시opt-in이전DB자동복원금지,이전포맷격리절차문구.
4. tests: delete실패→journal성공→재시작→복사SID거부, 모든write실패→503cookie보존·불가능조건명시, 권한복구뒤재시도→확실폐기, defaultoff/optin/legacy/version/re-enable, persistenceofflogout이전grant, refresh중logout, journaltamper/readfail. 실제OSACL환경제한은우회하지말고mockfixturevsrealDPAPI구분.

main.py/media계약유지. server-env/예시변수명허용동일이나예시기본off설명정리. 기존테스트필요변경. 마지막변경후의미있는focus검증,전체pytest는작업폴더fixture의미사용안전경로로1회가능하면실행. auth.md에정확한코드·실패·잔여한계를기록. 사용자에게불가능한영구접속/전체제공처완료주장금지.

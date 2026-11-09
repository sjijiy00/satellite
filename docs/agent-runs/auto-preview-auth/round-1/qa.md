# QA 최종 검증 — 회차1

2026-10-30 · 독립 QA. 통합 승인 근거는 불충분하다: production build와 브라우저 E2E가 환경의 자식 프로세스 권한 오류로 실행되지 않았다. 운영 서버는 시작·종료·재시작하지 않았고 실제 `.env`를 읽거나 변경하지 않았다.

## 실행 결과

| 명령 | 종료 | 결과 |
|---|---:|---|
| backend `..\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --disable-warnings tests/test_media_access.py tests/test_earthdata_auth.py tests/test_earthdata_persistence.py` | 0 | 47 passed, 1 skipped, 1 warning. TEST ONLY fixture; 실제 제공처 로그인 아님. |
| root `node.exe scripts/frontend-check.mjs typecheck` | 0 | strict TypeScript 통과. QA 테스트 변경 후에도 재실행 통과. |
| root `node.exe --test scripts/server-env.test.mjs` | 1 | Node test runner가 자식 생성 시 `spawn EPERM`, 테스트 본문 실행 전 실패. |
| root `node.exe --test --test-isolation=none scripts/server-env.test.mjs` | 1 | 13 통과, 2 실패. 실제 child 환경과 임시 git 검사에서 subprocess 생성 실패; fixture 설정/필터 검사는 통과. 이 명령도 전체 통과가 아니다. |
| frontend `node.exe node_modules/@playwright/test/cli.js test tests/auto-preview.spec.ts tests/media-access.spec.ts tests/earthdata-auth.spec.ts --list` | 0 | 3개 파일 23개 수집, LIVE 1개 포함. 실행·assertion 통과가 아니다. |
| root `NEXT_DIST_DIR=.next-auto-preview-qa`, `API_BASE_URL=http://127.0.0.1:8015`, `node.exe scripts/frontend-check.mjs build` | 1 | 격리 production build가 최적화 단계에서 `spawn EPERM`; 완료 안 됨. |
| frontend `E2E_BASE_URL=http://127.0.0.1:3015`, `E2E_OUTPUT_DIR=test-results-auto-preview-qa`, Playwright `test --grep-invert LIVE` | 1 | 136개 실행 준비 후 WorkerHost `spawn EPERM`, 브라우저/검증 실행 전 중단. 격리 서버는 시작하지 않았다. |

전체 backend 중복 실행은 지시에 따라 생략했다. Auth 보고의 전체 338 passed/17 skipped는 별도 담당자의 임시 fixture 실행 결과이며, 최종 epoch 보강 후 해당 담당 47개와 이번 독립 47개를 확인했다. 해당 전체 결과를 이번 독립 실행으로 표시하지 않는다.

## 테스트와 확인 범위

QA 테스트는 `auto-preview.spec.ts` 6개다. TEST ONLY 합성 응답으로 자동 preview-only 요청, 요청 중복, viewport 밖, 수동 재시도, 409, 반복 이미지 404, 장면 변경 지연 및 모바일 너비를 검사하도록 작성했다. 최종에 장면 전환 전 실제 inspect 도착을 기다리도록 테스트를 수정했다. 아직 브라우저에서 실행되지 않았고 상세와 카드가 동시에 가시적인 조건의 중복 보장은 별도 확인이 필요하다. 테스트의 일반 앱 API는 로컬 서버에 의존하므로 완전 네트워크 격리를 보장하지 않는다.

기존 `media-access.spec.ts`에는 명시 원본 다운로드의 receipt 갱신 성공·반복 만료 중단·인증 변경, browse 저장 갱신 시나리오가 수집된다. 현재 저장 선택자는 버튼으로 갱신되어 있다. 독립 E2E에는 인증 generation 변경 중 늦은 미리보기 응답과 동시 2 상한의 브라우저 검사가 없다. Frontend 보고의 TEST ONLY Node VM harness는 해당 큐 동시 상한, 인증 변경 후 지연 응답 폐기, preview-only 및 복구 1회 등을 확인했다고 기록하지만, 이번 QA의 독립 실행이나 브라우저 증거는 아니다.

## 미충족 및 한계

- 브라우저 실제 렌더링·viewport·요청 횟수·모바일·전체 회귀 및 production build 미검증. 위 실패는 권한 제한으로 기록하며 우회하거나 재승인 요청하지 않았다. 제품 결함 여부는 이 결과로 확정할 수 없다.
- Auth 보고에서 실제 Windows DPAPI 왕복과 ACL mock을 구분했다. 실제 ACL 설치 포함 저장 준비는 권한 오류로 skip이며, 실제 권한 환경의 저장·재시작 복원은 미검증이다.
- LIVE_STAC, 실제 Kakao 조회 및 NASA/USGS/CDSE 사용자 로그인·원본 파일 접근은 미실행이다. USGS/CDSE 신규 원본 인증은 구현 범위 밖이다. fixture 성공을 실제 로그인 성공으로 해석하지 않는다.
- 실제 제공처 인증 중 장면·인증 변경, 격리 서버와 실제 HTTP 통합 검증은 허용된 환경에서 후속 실행이 필요하다. 별도 전문 스킬과 위임은 사용하지 않았다.

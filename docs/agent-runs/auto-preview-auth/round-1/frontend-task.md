# 단계2 Frontend

brief.md, planner.md, leader-plan.md, frontend/AGENTS.md와 관련 Next 로컬 문서를 읽고 구현. 결과는 frontend.md. 패널 현재작업은 짧은 한국어. 위임 금지.

단독 소유: frontend/src/lib/useProviderAccess.ts 및 새 preview queue 모듈, frontend/src/components/ProviderPreview.tsx, EarthdataConnection.tsx, 필요시 ManagedAssetAccess.tsx/types/globals.css. 기존 frontend/tests/media-access.spec.ts와 earthdata-auth.spec.ts는 직접 업데이트. 새 독립 auto-preview QA 테스트는 다른 담당. 백엔드/scripts 수정금지.

실제 보이는 미리보기를 버튼 없이 자동 표시. IntersectionObserver visibility로 화면 밖 대량 요청 방지, provider/collection/id+auth generation 키 기준 목록/상세/비교 공유 중복 병합, 전역 큐 동시 최대2, bounded cache TTL120초보다짧게, 비가시 queued취소 및 구독자없는요청취소. StrictMode 안전. auto는 asset_keys:[], include_preview:true만 보내며 원본 probe/다운로드 금지. 초기 '미리보기 접근 확인'을 필수 경로에서 없애고 실패시 재시도와 숨기기/보기·browse저장 유지. 이미지 receipt 오류는 가시 상태 1회만 강제 session준비+재inspect 복구, 이후 명시 재시도. 숨긴 이미지 자동 되살리지 않음. auth/scene 변경시 요청abort/cache무효/늦은응답폐기. 다른 탭 auth변경도 대응할 수 있으면 비밀 없는 신호로 처리.

media/session backend 응답 ready, session_generation, expires_at(epoch초) 추가됨. .ready 성공 Promise영구 캐시 폐기. session준비는 single-flight+TTL. inspect HTTP409 error.code MEDIA_SESSION_REQUIRED이면 ready강제갱신 후 요청1회 retry. media preview receipt_expires_at epoch초 추가(backward compatibility). 서버 cookie/receipt는 브라우저 same-origin만.

Earthdata status storage/session expiry 정보를 화면에 정확히 표시. Backend 새 GET /api/auth/providers/status는 provider별 configured/connected/integration/storage/message. 응답 구조가 구현중이므로 방어적으로 파싱하고 기존 earthdata status와 호환 유지. NASA토큰을 USGS/CDSE로그인으로 표현금지. 로컬 Windows암호화저장·제공처 만료/철회시 재연결이 필요함을 간단히 안내. 스팸 status polling이나 자동 로그인 이동 금지.

기존 media/Earthdata E2E를 클릭없는동작으로 수정, API route mocks 유지. typecheck 시행. 라이브 네트워크만으로 fixture 테스트를 통과시키지 않음. QA가 최종 build·전체E2E 실행하므로 직접 서버재시작/build경합 금지. 프런트 관련 focused검증 가능하면 격리 실행; 명령/코드와 실패기록 frontend.md.

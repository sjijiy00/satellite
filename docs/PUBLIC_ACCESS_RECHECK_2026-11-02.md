# 공개 미리보기·원본 접근 재검증 — 2026-11-02

검증 구간: 14:54:32–14:57:01 KST (05:54:32–05:57:01 UTC). 실행 중인 `http://127.0.0.1:3000/api` 프록시를 사용했다. 서버 재시작, 자격증명 열람/설정, 새 로그인, AI 호출은 하지 않았다. 현재 표본에서 서버 전송 결함은 재현되지 않았다. 모든 장면/밴드의 성공을 보증하는 결과는 아니다.

## 실제 제공처 검증

공통 AOI `[126.7,36.4,126.71,36.41]`, 기간 2025-07-20–26, max_items=1. NOAA만 2025-07-20 하루. health와 media/session 200, 네 검색 모두 200 및 실제 Item 1건. 제한 상태 `total_limit`은 한 건 상한이다.

| 제공처/제품 | 실제 미리보기 GET | 원본 검증 | 완료 KST / 제한 |
|---|---|---|---|
| Earth Search Sentinel-2 L2A | JPEG 200, 26,038 bytes | scl 전체 200, **1,591,434 bytes**, 서버 완료 true, GTiff 5490×5490, 4×4 픽셀 디코드 | 14:56:37. 이 SCL 표본만 전체 수신 |
| Planetary Computer Sentinel-2 L2A | PNG 200, 2,190,270 bytes | SCL 전체 200, **1,474,350 bytes**, 서버 완료 true, GTiff 5490×5490, 4×4 픽셀 디코드 | 14:56:47. 서버 임시 SAS 경로 사용, 방문자 로그인 없음 |
| Planetary Computer Landsat C2 L2 | PNG 200, 1,239,292 bytes | qa_pixel 전체 200, **3,718,793 bytes**, 서버 완료 true, GTiff 7841×7961, 4×4 픽셀 디코드 | 14:56:58. 온도/반사도 대용량 밴드 전체 수신은 미검증 |
| NOAA NODD VIIRS NDVI CDR | missing_asset; 제공처 이미지 없음, 기존 UI에 미지원 표시 | ndvi Range 206, 앞 1,024 bytes 접근. 메타데이터 크기 **64,011,565 bytes** | 14:57:01. 전체 수신 미실행 |

정확한 Item:

- ES: `S2B_52SBF_20250725_0_L2A`
- PC S2: `S2B_MSIL2A_20250725T021539_R003_T52SBF_20250725T041758`
- PC Landsat: `LC09_L2SP_116035_20250723_02_T1`
- NOAA: `VIIRS-Land_v001_JP113C1_NOAA-20_20250720_c20250728122022`

작은 TIFF 세 개는 과거 동일 Item 수신 크기로 상한을 정하고 현재 Content-Length를 확인한 뒤 메모리에서만 전체 수신했다. 응답 크기 일치·서버 완료 상태·실제 TIFF 디코드를 확인했다. 파일을 디스크에 저장하지 않았다. 미리보기는 분석용 원본이나 AOI 품질 검사가 아니다.

## 이번 변경

`frontend/src/components/AssetDownloads.tsx` 안내만 개선했다.

- 밴드 선택 → **선택 원본 접근 확인 → 원본 다운로드** 순서를 명시했다.
- `.txt` 링크 목록과 영상 파일을 구분했다.
- PC는 직접 링크가 0개여도 서버 임시 SAS 경로로 받을 수 있음을 안내했다.
- ES Landsat requester-pays는 무인증 경로가 아니며 PC Landsat를 대안으로 선택하도록 안내했다. 제품/처리 버전 확인이 필요하다.

서버 로직 변경은 없다. 기존 `SceneProvenance.tsx`의 NOAA 미리보기 미지원 안내를 유지했다. 가짜 이미지/NetCDF 자동 이미지화를 추가하지 않았다.

`backend/tests/inspect_public_runtime.py`는 직접 실행하는 수동 진단 도구이며 pytest 자동 수집 대상이 아니다. URL/receipt/cookie/인증값을 출력하지 않는다. `--download`도 NOAA는 probe만 수행한다. 행별 결과를 확인해야 하며 프로세스 종료 코드만 성공 근거로 사용하지 않는다.

## 검사 결과

- `backend`에서 `LIVE_STAC=0`, `PYTHONUTF8=1` 환경으로 `..\.venv\Scripts\python.exe -m pytest -q tests/test_public_paths.py tests/test_media_access.py --disable-warnings -p no:cacheprovider`: **45 passed, 1 warning, 1.81s**. 관련 mock 회귀 검사이며 실제 제공처 성공과 별도다. 첫 제한 환경 실행은 응답 없이 대기하여 중단했고, 허용된 실행에서 위 결과를 얻었다.
- `frontend`에서 `npm.cmd run typecheck`: **exit 0**.
- 실제 연결: `backend`에서 `..\.venv\Scripts\python.exe tests/inspect_public_runtime.py`, 이어 `--download` 실행. 위 표가 이번 실제 결과다.
- 새 전체 테스트, production build, 브라우저 E2E는 실행하지 않았다.

## 남은 제한과 승인 차단

기존 Computer Use는 Windows 브라우저 URL을 정책 적용에 충분한 확신으로 판별하지 못해 중단됐다. 이번에는 이를 다른 브라우저 제어 수단으로 우회하지 않았다. 따라서 현재 화면의 클릭·렌더링·브라우저 다운로드 저장/CORS 동작은 직접 재검증하지 못했다. HTTP 프록시 수신과 UI 코드 검토만 확인했다.

최초 전체 검증 계획의 NOAA 64MB 수신과 워크스페이스 검증 파일 저장은 자동 승인 검토에서 대용량·범위 초과로 **실행 전에 거절**됐다. 이후 허용된 작은 TIFF 세 개 메모리 검증으로 범위를 줄였다. NOAA 전체 파일은 이번에 다운로드하지 않았다.

CDSE/HLS 신규 연결과 인증은 변경하지 않았다. 현재 CDSE 운영자 설정 이름은 `OPERATOR_CDSE_USERNAME`, `OPERATOR_CDSE_PASSWORD` 또는 `OPERATOR_CDSE_REFRESH_TOKEN`; NASA는 `OPERATOR_NASA_USER_TOKEN`, `OPERATOR_NASA_TOKEN_EXPIRES_AT`이다. 공통 활성화·제공처별 활성화·공개 재제공 검토 설정은 `OPERATOR_DATA_ACCESS.md`를 따른다. **현재 NASA 운영자 대상은 VNP09GA이며 HLS가 아니다.** HLS S30/L30 검색·제품 식별·파일 허용 범위·QA 연결은 `HLS_ADAPTER_DESIGN.md`의 후속 구현 사항이다. 토큰 등록만으로 HLS가 추가되지 않는다.

실행 중 개발 프로젝트의 시간 한정 스냅샷이다. 기존 README/TEST_REPORT 및 사용자의 다른 수정은 덮어쓰지 않았다.

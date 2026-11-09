# 현재 공통 처리 기반 — 2026-11-04 통합 개선

[연구 작업 흐름](RESEARCH_WORKFLOW.md)이 결과 보관/단일 시점 대형 AOI의 최신 계약입니다. `processing_repository.py`의 서명된 SQLite journal과 전용 비공개 파일, 지속 소유권 키/쿠키로 **새로 생성한 성공 작업**을 재시작 후 복원합니다. 실행 중 작업은 재시작 시 실패 처리하고 자동 재실행하지 않습니다. 동일 보관소의 두 번째 실행 worker는 파일 lease로 거절합니다. `GET /processing/jobs`는 같은 소유자의 최대20개 작업을 조회합니다. 다운로드/보관 상태에서 전체 해시를 검사합니다.

단일 시점 NDVI/MNDWI/NDBI·Landsat 온도 계열은 검증된 제품에 한해 최대200km²/600,000셀/36타일, 타일별 기존 한도·전체256MiB/512요청/255초/ZIP16MiB입니다. 전후 변화50km², 합성/ML25km²는 확대하지 않았습니다. 실제 대형 실연결 근거는 S2B79.6km²/9타일 한 사례이며 도시 전체 완료가 아닙니다. 아래는 이전 foundation 이력이고 현재 제품/자원/보관 상태는 이 절·PRODUCT_ANALYSIS·RESEARCH_WORKFLOW와 최신 TEST_REPORT를 우선합니다.

---

# 실제 장면 → 픽셀 → 검증된 산출물

2026-11-04: 공통 결과에 `artifact.execution_record`(실제 입력/출력/격자·실행/생략/미기록 단계), 작업 `events`, `retention`(실제 파일 available/expired/missing/changed/not_created·남은 초·만료 UTC), `ownership`, `job_expires_at`을 추가했다. 기존 필드는 유지한다. 파일 존재/크기 조회와 다운로드 시 전체 해시 검증은 구분한다. 완료 후 작업 TTL을 갱신하므로 실행 시간이 파일 보관 기간을 소모하지 않는다. 기존 S2 UI도 브라우저 수신을 요구하지 않고 필수 선택/서버 검사를 사용한다. 현재 화면·복원/전달의 정확한 범위는 [WORKFLOW_PAGES.md](WORKFLOW_PAGES.md)의 2026-11-04 절을 따른다.

후속 `products-2`: [PRODUCT_ANALYSIS.md](PRODUCT_ANALYSIS.md)가 새 기초 계산·PC Landsat·제품별 QA/보정·사용자 기준·단위의 최신 계약이다. 아래 foundation-1의 기존 엔진/작업/자원 제한은 유지하며 단독 NDVI/ST/PC 픽셀 미지원은 당시 기록이다. PC S2/HLS/VIIRS/SAR는 계속 미지원이다.

2026-11-03 구현. 실행 근거와 실패 이력은 최신 `TEST_REPORT.md` 및 `test-results/foundation-20261103-200942/`를 따른다. 검색·추천·미리보기·브라우저 원본 수신·픽셀 QA·작업 성공은 서로 다른 상태다.

## 실행 지원의 단일 원천

`backend/app/analysis_catalog.py`의 `/analysis/catalog` 응답은 `processing_contract_version=foundation-1`과 분석별 `execution`, `processing_methods`를 제공한다. 제품/제공처·필수 변수/QA·장면 수·UTC/공간 조건·엔진·산출물·미지원 이유를 서버에서 선언한다. 과학적 추천은 기존 `purpose_plan.py`/`sensor_catalog.py`를 계속 사용한다. 프런트는 서버 계약을 표시하고 실행 서버가 canonical Item을 다시 검증한다.

| 방법 | 실제 엔진과 입력 | 새 공통 경로의 한도 | 결과 |
|---|---|---|---|
| `s2_quality` | Earth Search S2 L2A 한 장면 또는 두 날짜, 목적별 필수 밴드와 SCL | bbox 또는 확정 polygon, 50km²·150,000셀·최대16타일 | 유효/제외 마스크, QA 기록, 실제 품질 지도 |
| `ndvi_change` | 같은 S2 플랫폼·제품 기준선의 두 날짜, 적색/근적외선/SCL·검증된 보정값 | bbox 또는 확정 polygon, 50km²·150,000셀·최대16타일 | 전후/차이 3밴드 GeoTIFF, 유효/제외 마스크, 통계·실제 지도 |
| `observed_composite` | 기존 식생 한 시점·동일 S2의 실제 관측 선택, 2–4장면 | 기존 bbox 25km²·31일, polygon 미지원 | 실제 관측 밴드·촬영일·출처 인덱스·마스크·실제 지도 |
| `local_ridge` | 기존 식생 한 시점 제한 ridge와 공간 보류 검증/복사 기준선 게이트 | 기존 bbox 25km²·31일, polygon 미지원 | 관측/추정/미해결·참조일·검증 기록·분리 지도 |

공통 UI는 현재 Workspace의 선택 장면 또는 비교 쌍을 사용한다. 합성/ML의 3–4장면 선택은 기존 UI/API를 유지하며 새 공통 패널은 현재 비교 쌍을 사용한다. 단독 NDVI, 온도/고온/영역 온도 비교, 수체/침수/토지피복/NDBI 계산 엔진을 추가하지 않았다. 해당 분야에서 S2 품질 검사가 가능해도 그 분석이 구현됐다는 뜻은 아니다. PC·Landsat·HLS·VIIRS·Sentinel-1에 S2 QA/NDVI를 적용하지 않는다.

기존 A3/A4 API와 구형 UI의 25km² 한도·원본 수신 게이트는 호환성을 위해 유지한다. **새 공통 처리 패널은 브라우저 원본 수신 여부를 실행 근거로 삼지 않는다.** 새 경로는 canonical Asset의 서버 범위 읽기가 기본 입력이다. 사용자 로컬 TIFF 업로드/재사용은 구현하지 않았다.

## 요청과 계획/작업

1. 처리 화면에서 세부 의도를 확인하고 서버 지원 방법/선택 장면을 확인한다.
2. `POST /processing/plans`: 분야·분석 ID·방법·확정 ROI·출처·UTC 기간·선택 Item/밴드·기준일·QA 정책 버전을 보낸다. 임계값/비교 영역은 명시적 null/빈 목록이며 현재 엔진이 지원하지 않는 값을 보내면 거절한다.
3. canonical Item 식별자·제품·기간·필수 Asset·보정·관측 중첩을 재조회한다. QA/NDVI의 이 단계는 `canonical_metadata_checked_pixels_pending`이며 실제 픽셀 성공이 아니다. 합성/ML은 기존 픽셀 계획 검증과 ETag/ML 검증 근거를 보관한다.
4. 사용자 체크 확인 뒤 `POST /processing/jobs`: 계획 ID·확인 digest·idempotency key로만 실행한다. canonical 메타데이터/digest를 다시 대조한다.
5. `GET /processing/jobs/{id}`로 queued/running/succeeded/failed/cancelled를 조회한다. `POST .../cancel`은 자식 프로세스를 종료한다. 실패는 품질 null이며, 실제 검사한 전 영역 구름 0%와 구분한다.
6. 검증된 파일만 `GET .../download`에서 제한된 바이너리 ZIP으로 전송한다. 브라우저는 전체 길이·SHA-256까지 확인한 다음 저장을 요청한다. 디스크 저장/GIS GUI 재열기는 별도 확인이다.

계획/작업 변경에는 기존 HttpOnly 서명 세션과 Origin 검사를 사용하고 조회/취소/다운로드에도 소유권을 확인한다. 계획/작업 각각 최대8개·15분 보관, 원본 픽셀 동시 처리1개다. 페이지 복원은 안전한 작업 ID/문맥만 같은 Workspace snapshot에 저장하고 GET 상태만 재조회한다. 계획 확인·다운로드·작업 POST를 자동 재실행하지 않는다. 조건이 바뀌면 이전 작업으로 표시하고 새 조건 지도에 적용하지 않는다.

**현재 로컬 단일 worker 전용**이다. 세션 서명 키/계획/작업은 메모리이므로 재시작하면 이전 작업 접근은 만료되고 자동 재개하지 않는다. 여러 worker 간 공유 큐/소유권/영속 상태 복원은 미구현이며 공개 다중 worker 운영 준비가 완료된 것으로 보지 않는다. 재시작은 진행 중 작업이 없다는 사용자 확인 후 한다. 작업의 파일은 비공개 디스크에 남을 수 있으나 요청 시 TTL 정리되며 복원된 작업 ID로 재접근할 수 없다.

## 공간·헤더·QA

- 검색 bbox와 실제 polygon 통계 범위는 별개다. 기본은 확정 bbox이며 행정경계 통계라고 부르지 않는다.
- 명시 선택한 등록 경계는 서버의 검증된 원본을 다시 읽고 코드/연도/출처/이용 조건/원래 CRS/변환 CRS/해시를 기록한다. 수동 GeoJSON도 유효성·크기·좌표 범위·bbox 일치를 검증한다. 등록 경계의 외접 bbox가 현재 공간 상한을 넘으면 거절하며 몰래 자르지 않는다.
- 실제 파일 헤더에서 CRS·transform·밴드 수·NoData·원본 해상도를 확인한다. 한 LAEA 20m 격자에서 최대160×160셀 타일을 이어 붙여 같은 extent/transform을 유지한다. SCL은 nearest, 연속 반사도는 QA/NoData 제외 뒤 average이며 기존 유효 기여 비율 정책을 유지한다.
- AOI 전체, 기하 관측 영역, 미관측, 품질 제외, 유효 영역의 분모/면적을 구분한다. 제외 마스크는 0=ROI 밖, 1=미관측, 2=품질/NoData/수치 제외, 3=산출물 유효 영역이다. ML의 3에는 추정이 포함될 수 있으므로 `pixel_status.tif`와 원래 엔진 기록을 함께 해석한다.
- 50km²는 로컬 수치 fixture의 타일/비타일 일치 검증 상한이다. 모든 실장면의 시간/전송 성공을 보장하지 않는다. 최신 실연결 표본은 약1km²다. 약1,100km² 도시 bbox 분산 처리와 도시 전체 통계는 미지원이다.

## 제공처·보안·자원

`raster_source.py`는 기존 COG 범위 읽기와 PC 익명 단기 SAS 서명을 분리한다. 현재 실행 카탈로그는 검증된 Earth Search S2 공개 COG만 허용한다. PC 읽기 어댑터는 mock으로 검사했으며 PC 제품 분석을 활성화하지 않았다. NASA/USGS/CDSE 운영자/사용자 인증은 기존 미디어 경로에 그대로 두고 픽셀 엔진 검증 전에는 범위 처리에 연결하지 않는다. 키·승인 플래그를 변경하지 않는다.

canonical URL만 입력으로 사용하고 HTTPS/허용 호스트/DNS 목적지/경로를 검사한다. 인증이나 SAS를 임의 URL에 붙이지 않는다. 범위 읽기의 리다이렉트는 따라가지 않고 정확한 HTTP206/Content-Range를 요구한다. PC401/403에서만 기존 익명 SAS 재발급을 한 번 허용한다. 출력에는 unsigned 원본 식별/주소만 남기고 query/인증 문자열은 거절한다.

- 원본 파일 메타데이터 크기 상한2GB, 단일 읽기8MiB 이하, 총 입력64MiB, 원격 요청/SAS 예약 합계128회, 요청8초, 범위 작업60초/자식 프로세스75초.
- 원본 window 1,000,000셀, Range 캐시16MiB, 동일 격자150,000셀/16타일. OS 차원의 강제 메모리 격리는 추가하지 않았다.
- 소유자별/전체 시간당512MiB 보수적 예약. 실패한 작업에도64MiB 예약을 자동 환불하지 않아 무제한 반복을 막는다.
- ZIP16MiB·해제32MiB·비공개 디스크256MiB, 전송 동시2개·120초·시간당512MiB. 대용량 ZIP을 HTTP base64 JSON으로 반환하지 않는다. 구형 엔진의 내부 IPC/구형 API base64 계약은 호환을 위해 남아 있다.
- 파일은 `backend/.private/processing/{server_job_uuid}/`에 임시 생성→실제 재열기/스펙/해시 검증→원자적 게시한다. TIFF는 CRS/transform/밴드/자료형/단위/NoData/전체 읽기를 확인하고 원래 엔진 파일을 해시 생성 후 수정하지 않는다.
- manifest에 원문 처리 입력·실제 출처 Item/Asset·촬영일·보정·격자·단위·QA·전송/검증 기록과 파일 해시를 남긴다. 동일 격자의 실제 배열만 기존 지도 레이어로 연결한다. 토큰/서명 URL/ZIP/래스터를 브라우저 영구 저장소에 넣지 않는다.

## 검증 명령

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest -q --durations=5
# 실연결은 별도 명시 플래그에서만:
$env:LIVE_STAC='1'; $env:LIVE_PROCESSING='1'
..\.venv\Scripts\python.exe -m pytest -q tests/test_processing_live.py
cd ../frontend
npm.cmd run typecheck
npm.cmd run build
npx.cmd playwright test tests/processing-foundation.spec.ts tests/analysis-selection.spec.ts
# LIVE 플래그가 있을 때만 공개 실제 검색/픽셀/브라우저 ZIP 검증:
npx.cmd playwright test tests/processing-foundation-live.spec.ts
```

실제 실행은 비밀 설정이 없는 격리3011/8011과 전용 build dist를 사용했다. 최신 명령·종료 코드·시각·fixture/실연결 결과는 TEST_REPORT에서 확인한다. QGIS/ArcGIS GUI, 다른 제공처 픽셀 엔진, 재시작 작업 재개, 다중 worker는 별도 남은 검증/구현이다.

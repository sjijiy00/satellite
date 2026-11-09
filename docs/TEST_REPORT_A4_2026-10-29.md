# A4 식생 NDVI 변화 분석 — 최신 검증 보고서

검증일: 2026-10-29 (Asia/Seoul). 실제 작업 폴더: `C:\Users\aicam\Documents\ChatGPT\바이브코딩`. 기존 프로젝트에는 Git 저장소가 없어 파일 단위로 기존 사용자 수정을 보존했다. 이번 요청은 **A4만** 수행했다. A5 Sentinel-1 연결, SAR 처리, 다른 지수, 배포·푸시는 진행하지 않았다. 이전 A3 보고서는 [과거 기록](TEST_REPORT_A3_2026-10-29.md)에 보존했다.

## 시작 상태와 재사용

`AGENTS.md`, `frontend/AGENTS.md`, 최신 README·TEST_REPORT·개발 계획, 패키지/테스트 설정, API/모델/목적 규칙, A2 조건 검사와 A3 실제 픽셀 진단을 읽었다. 변경 전 백엔드 `..\.venv\Scripts\python.exe -m pytest -q`는 종료 코드 0, **135 passed / 8 skipped**, 9.03초였다. 이전 보고서의 성공 수치는 이번 검증으로 재사용하지 않았다.

A2의 canonical STAC 재조회·두 날짜/동일 제품/footprint 검사, A3의 공개 COG HTTP 206 범위 읽기·헤더·SCL/NoData·20 m LAEA 공통 격자·면적·작업 상한, 기존 목적 규칙의 적색 B04/근적외선 B08/SCL 선택을 재사용했다. 독립된 검색기나 추천기를 만들지 않았다.

## A4 구현 범위

- `POST /change-analysis`는 식생 목적의 Sentinel-2 L2A **같은 위성 플랫폼·처리 기준선**, 서로 다른 UTC 날짜의 이전→이후 두 장면을 처리한다. 사용자 AOI·검색 기간·기준일과 기존 비교 선택을 사용한다. 서버가 신뢰하는 원본 STAC Item을 다시 조회한다.
- 실제 SCL/NoData/유효 기여율 마스크와 공통 영역을 사용한 뒤, 메타데이터의 scale/offset·처리 기준선·제공처 보정 표시가 일치할 때만 `NDVI=(B08−B04)/(B08+B04)`를 계산한다. DN=0, NaN/Inf, 음수 반사도, 분모 1e-6 이하, NDVI 범위 밖 값은 제외한다. 1e-6은 **수치 안정성 한계**이며 식생 변화 분류 임계값은 설정하지 않았다. 같은 공통 유효 픽셀의 이전/이후 NDVI와 이후−이전 차이를 제공한다.
- 실제 분석 면적, 공통 촬영/AOI 대비 제외 면적, 품질 마스크와 수치 문제의 제외 면적을 구분한다. 경계 셀은 LAEA 교차 면적으로 가중 집계한다. 20 m 셀의 0/1 TIFF 마스크는 경계의 부분 면적을 표현하지 않으므로 처리 기록에 이를 명시한다. 지표 평균은 분석 면적 가중 평균이다.
- ZIP은 `ndvi_change.tif`(float32, 이전/이후/차이 3밴드, CRS·transform·NoData −9999), `valid_mask.tif`(uint8, 1 유효/0 제외·NoData), `processing.json`을 담는다. JSON은 원본 Item/Asset, 취득시각, 처리 버전 `s2-l2a-ndvi-change-2026-10-29.1`, SCL/수치 정책, 격자, 면적, 원본 파일 헤더, scale/offset, 파일 SHA-256을 기록한다. 인증정보 또는 서명 쿼리는 포함하지 않는다. 압축 결과 4 MB를 넘으면 중단한다.
- 기존 비교 UI 안에 A4 버튼·면적/평균·근거·ZIP 다운로드를 추가했다. A3 품질 진단과 별도 버튼이며 검색/비교/밴드/직접 링크 선택은 유지한다. 요청 도중 기준일·장면·운영 기준이 바뀌면 오래된 응답을 폐기한다. A3/A4 상한 내 작업을 위해 Next.js 로컬 프록시 제한을 120초로 설정했다.

## 실제 실행 결과

| 위치 | 명령 | 종료 코드 | 결과 |
|---|---:|---:|---|
| backend | `$env:LIVE_STAC='1'; ..\.venv\Scripts\python.exe -m pytest -q --disable-warnings` | 0 | **173 passed** (합성/단위 163, 실제 외부 연결 10), 47.07초. 경고 651개는 표시만 생략 |
| frontend | `npm.cmd run build` | 0 | Webpack production build·내장 TypeScript·정적 생성 통과 |
| frontend | `npm.cmd run typecheck` | 0 | 독립 `tsc --noEmit` 통과 |
| frontend | `npm.cmd run test:e2e` | 0 | **39 passed**, 실제 STAC·A3/A4 픽셀 읽기·A4 ZIP 다운로드 포함 |
| 루트 | `node scripts/start-local.mjs` | 실행 중 | 로컬 백엔드 `/health` 200 및 프론트엔드 3000 포트 |

최종 브라우저 E2E 39건 중 A4 6건은 테스트 전용 fixture 5건과 실제 영상/실제 ZIP 1건이다. Fixture는 서비스 경로에서 결과 대용으로 쓰지 않았다. A4 백엔드 28건은 고정 소형 TIFF와 API 사전 조건·수치 경계 검사, 2건은 실제 공개 영상 검사다. 기존 A1~A3·추천·비교·다운로드·모바일 회귀도 전체 재실행했다. A4 실영상 테스트는 다운로드 ZIP 안의 두 TIFF를 Rasterio/GDAL로 다시 열어 CRS·NoData·밴드·격자를 확인했다. **QGIS 프로그램 자체는 실행하지 않았다.**

### 실제 영상 사례

AOI `[126.70, 36.40, 126.71, 36.41]`, 기간 2021-07-01~31, `S2B_52SBF_20210716_0_L2A` → `S2B_52SBF_20210726_0_L2A`. 두 Item 모두 Sentinel-2B, 처리 기준선 03.01, 적색/근적외선 scale=0.0001·offset=0, 보정 미적용 표시와 일치한다. 실제 HTTP Range로 받은 COG에서 계산했다.

| 지표 | 실제 응답 |
|---|---:|
| AOI·공통 촬영 면적 | 995,374.3943821327 m² |
| 공통 유효 분석 면적 | 436,928.9489276938 m² |
| 공통 촬영 영역 중 제외 면적 | 558,445.4454544389 m² |
| 이전 NDVI 면적 가중 평균 | 0.7382915370315717 |
| 이후 NDVI 면적 가중 평균 | 0.77905544223305 |
| 차이 평균 (이후−이전) | +0.040763905201478136 |
| 실제 래스터 전송 | 6,373,376바이트 / HEAD+Range 22회 |

이 수치는 해당 두 장면과 현재 SCL/NoData 정책의 계산 결과다. 식생 증가 면적 또는 원인·과학적 적합성 확정 판정이 아니다. 원본 제공처 자료/메타데이터가 바뀌면 재현 수치가 달라질 수 있다. 브라우저 E2E는 원본 검색→장면 선택→A4 요청→실제 ZIP 다운로드를 확인했다. 실제 다운로드 결과는 [검토용 ZIP](../examples/sentinel-2-ndvi-2021-07-16_2021-07-26.zip)에 복사했다(20,134바이트). ZIP의 세 파일명, 처리 버전·분석 면적·Asset URL에 인증 쿼리 없음도 다시 확인했다. 테스트 fixture가 아니라 실제 공개 영상 계산 산출물이다.

### 실패·수정 이력

- 초기 고정 TIFF 집중 테스트 1건은 fixture의 플랫폼이 같은 값이라 교차 플랫폼 거부 조건을 시험하지 못했다(종료 1). fixture를 바로잡고 이후 집중/전체 테스트를 통과했다.
- 첫 전체 E2E는 **37 passed / 2 failed**, 종료 1이었다. 실제 A4가 30초를 넘을 때 설치된 Next.js rewrite 프록시의 기본 30초 제한이 연결을 끊었고, A3/A4 미지원 버튼의 같은 이름이 Playwright 선택을 모호하게 했다. 프록시를 120초로 설정하고 문구를 수정했다.
- 재실행은 **38 passed / 1 failed**, 종료 1이었다. A4 이름 안에 여전히 A3 이름 전체가 포함되어 Playwright 부분 일치가 발생했다. A4 문구를 완전히 구별해 최종 39개를 통과했다.
- 제한 샌드박스에서 로컬 소켓 접근이 거부돼 시작 단계 E2E를 중단했다(종료 1). 같은 소스를 허용된 로컬 서버/브라우저 환경에서 최종 재실행해 통과했다. 마지막 빌드는 제한 환경에서 생성 캐시 경로 EPERM으로 1회 실패했고 허용된 로컬 환경에서 재실행해 통과했다.

## 수치·오류·한계

고정 소형 래스터 테스트는 정확한 이전 0.5/이후 2⁄3/차이 1⁄6, TIFF NoData/마스크, 전부 구름, 품질 파일 누락, 공통 영역 없음, 다른 격자의 공통 격자 재투영, 중복·역전 날짜, 같은 날짜, 필수 밴드 누락, 다른 플랫폼/기준선, 잘못된 scale/offset, 0 분모·NaN/Inf·음수 반사도, 인증 쿼리 기록 금지를 검사한다. 실패/전부 구름/0%를 혼동하지 않고 계산 불가 시 분석 파일을 만들지 않는다.

공개 2025 Item 일부에서 `earthsearch:boa_offset_applied=true`와 `raster:bands.offset=-0.1`이 동시에 나타나는 **보정 메타데이터 상충이 여전히 미해결**이다. 이 조합은 수치를 임의 보정하지 않고 A4를 보류한다. 실제 사례를 opt-in live 테스트로 확인했다. 현재는 같은 플랫폼/같은 처리 기준선의 공개 Sentinel-2 L2A, 북쪽 위 미터 투영, 10/20 m 원본 격자, 25 km² 이하 AOI로 제한한다. SCL 오분류, 계절/생육주기·관측각·대기 조건 차이, 플랫폼 간 일관성은 별도 검토가 필요하다. `minimum_valid_percent`는 운영 참고 기준이며 A4의 보편적 과학 판정 기준이 아니다. 원본 전체 파일을 저장하거나 SAR/수역/도시 변화로 확장하지 않았다. 단일 앱 프로세스 작업 잠금이므로 다중 인스턴스 분산 상한은 미구현이다.

공식 자료를 2026-10-29 확인했다: [Copernicus S2 제품·DN NoData·보정](https://sentiwiki.copernicus.eu/web/s2-products), [CDSE NDVI B04/B08·SCL 예제](https://documentation.dataspace.copernicus.eu/notebook-samples/openeo/NDVI_Timeseries.html), [CDSE S2 L2A 밴드/해상도](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S2L2A.html). 제공처 offset 상충은 [Earth Search 이슈](https://github.com/Element84/earth-search/issues/71)도 참고했다.

## 실제 변경 파일

| 파일 | 변경 내용 |
|---|---|
| `backend/app/change_analysis.py` (신규) | 수치 검사·공통 NDVI·면적·GeoTIFF/마스크/기록 ZIP |
| `backend/app/pixel_raster.py`, `pixel_quality.py`, `pixel_worker.py` | A3 읽기/마스크/격자 재사용 및 A4 실행 모드 |
| `backend/app/models.py`, `main.py` | A4 요청 모델과 `/change-analysis` API |
| `backend/app/recommendations.py` | 식생 S2의 조건부 A4 지원 범위 안내 |
| `frontend/src/components/ChangeAnalysis.tsx` (신규) | 계산·결과·다운로드·오래된 응답 차단 |
| `frontend/src/components/PixelQuality.tsx`, `SceneComparison.tsx`, `frontend/src/app/page.tsx` | 기존 비교 흐름에 A4 연결 및 안내 |
| `frontend/src/lib/types.ts`, `frontend/src/app/globals.css`, `frontend/next.config.ts` | 응답 타입·모바일 배치·120초 프록시 |
| `backend/tests/test_change_analysis.py`, `test_change_analysis_live.py` (신규) | 고정 TIFF/오류 경계 및 실제 공개 영상 |
| `frontend/tests/change-analysis.spec.ts` (신규) | 선택·다운로드·모바일·경합·실영상 E2E |
| `README.md`, `AGENTS.md`, `docs/NEXT_STEPS.md`, `TEST_REPORT.md` | 실행/정책/상태·검증 기록 갱신 |

재현: 루트에서 `node scripts/start-local.mjs` 실행, 브라우저 `http://127.0.0.1:3000/`에서 식생 목적·위 AOI/기간 입력, Sentinel-2 L2A 검색, 전후 모드에서 위 두 Item 선택, **두 날짜 NDVI 계산** 및 ZIP 저장. 실시간 검사는 공개 제공처 접근이 필요하다. A5는 미착수 상태에서 멈춘다.

## 다운로드 부가설명 축약 — 2026-11-09

사용자 지정 영역의 원본 접근 설명은 짧은 안내만 표시하고 전송 한도·접근 갱신 및 제공처 링크·밴드 추천 버전은 기본 닫힌 details로 이동했다. 버튼·실패 표시·전송 로직은 유지했다. TypeScript와 격리 production build 통과 (`test-results/download-copy-build.log`). 이번 문구 변경에서 실제 원본 다운로드나 유료 AI 호출은 하지 않았다.

## 자연어 지명·반경 자동 좌표 및 실제 결과 — 2026-11-09

충남/충청남도 등 도 명칭 정규화 누락으로 REGION 후보가 거절되던 문제를 수정했다. 명확한 계층 행정 지명을 AI가 place로 분류해도 주소 조회·전체 구성요소 일치 검사로 처리한다. 유일하게 확인된 위치+명시 반경의 bbox를 자동 입력하고 좌표 적용 확인을 남긴다. 수동 좌표는 덮어쓰지 않는다. 기존 좌표 예시 중심126.705/36.405는 Kakao 역지오코딩상 충청남도 청양군 화성면 장계리이며 보령시 안내를 정정했다.

사용자 승인 OpenAI 실제 호출 **2회**: 첫 호출 원문/스키마 검증 실패, 두 번째 성공(보고 입력1943/출력424토큰). 이후 추가 유료 호출을 차단하는 테스트 서버에서 동일 문장의 성공한 실제 응답을 캐시 재사용했다. 가짜 AI/지명/STAC/래스터 응답으로 대체하지 않았다. 최종 실연결 브라우저 **1 passed (41.8s)**: 자연어→자동 날짜/좌표→좌표 확인 클릭(좌표 타이핑 없음)→Earth Search→대상/참조 밴드→식생 세부 선택→합성 계획→ML계획→succeeded→ZIP 다운로드. `test-results/natural-demo-final.log` 및 `test-results/natural-demo/{coordinates.json,result.zip,result.png,verification.json}`.

청양군 화성면 장계리 조회 중심126.702371166096/36.4092884567677, 반경1000m 외접 bbox [126.6912111,36.4002676,126.7135312,36.4183093]. 기간2021-07-16~26, 대상 S2B_52SBF_20210716_0_L2A, 참조 S2B_52SBF_20210726_0_L2A. AOI4008081.108m²/관측2384849.946/추정1069107.356/잔여554123.806, 추정2839셀. 6개 GeoTIFF 재열기·원관측 불변·추정값 혼합 일치 확인. 보류5638표본 RMSE red0.011245/nir0.066703/green0.011196, 구름 아래 참값 정확도 아님. 표면반사도·거짓색 산출물이며 독립 NDVI 출력이 아니다.

지명 backend35 passed, 자동 좌표·수동 보호 frontend fixture2 passed, TypeScript 및 격리 production build 통과 (`natural-radius.log`, `natural-radius-build.log`). 진단 서버는 검증 뒤 일반 서버로 복귀한다. 자연어 첫 회 성공을 보장하지 않으며 제공처/AI 응답 실패는 그대로 표시한다.

## 식생 ML 실제 화면 전체 흐름 확인 — 2026-11-09

기존 estimate-mode 실연결 테스트를 LIVE_STAC=1 명시 실행으로 복구하고 현재 직접 입력·제품 선택·분석 페이지 이동·세부 분석 확정 흐름에 맞췄다. 최초 실행에서 합성 검사 버튼 비활성화를 재현했다. ProcessingExecution의 초기 밴드 설정이 암묵적 목적 기본값 green을 누락시키는 원인이었다. 기본 추천 밴드와 실행 필수 밴드를 합쳐 초기화하며 명시 선택은 유지하도록 수정했다.

실제 Earth Search 검색→두 영상 밴드 체크→대상 선택→세부 분석 확인→합성 계획→ML 계획/검증→확인 실행→succeeded→브라우저 ZIP 저장 **1 passed (44.4s)**. 기록 `test-results/optical-full-live.log`, 실제 결과 `test-results/verified-optical-demo/result.zip`, 화면 `result.png`. fixture 응답·가짜 다운로드 기록·유료 OpenAI 호출 없음. 이번 UI 입력 기간은 **2021-07-16~2021-07-26**, bbox [126.70,36.40,126.71,36.41], 목표 S2B_52SBF_20210716_0_L2A, 참조 S2B_52SBF_20210726_0_L2A. 실제 다운로드 ZIP 6개 TIFF 재열기, CRS/NoData, 실측 불변과 추정값 혼합 일치 확인. 상태 셀 0:401, 1:1560, 2:615; 추정 237513.870m², 잔여153706.477m². 구름 아래 참값 정확도 검증은 아니다. TypeScript noEmit 및 격리 production build 통과 (`optical-fix-build.log`).

## 식생 광학 결측 처리 재검증 — 2026-11-09

열환경 결측 추정과 광학 구름 처리 시연을 구분하기 위해 기존 Sentinel-2 식생 경로를 재검사했다. `LIVE_STAC=1`로 cloud_estimate/composite 단위 및 실제 연결 테스트를 실행하여 **24 passed** (`test-results/optical-recheck.log`). 실제 S2B_52SBF_20210716_0_L2A 목표와 S2B_52SBF_20210726_0_L2A 참조, bbox [126.70,36.40,126.71,36.41]에서 계획→확인→작업→ZIP→GeoTIFF 재열기를 통과했다. AOI 995374.394m², 목표 유효 604154.047m², ML 추정 237513.870m², 미해결 153706.477m². 별도 관측 합성은 유효 843267.917m², 미해결 152106.477m². 합성과 ML은 서로 독립 실행이며 연속 추가 면적으로 합산하면 안 된다. 반사도 ML 공간 보류 MAE red 0.01121/nir 0.06576/green 0.01161이며 구름 아래 참값 정확도는 아니다. 입력 결측은 SCL/NoData 품질 제외 전체를 포함하므로 해당 면적 전부를 구름 면적으로 표현하지 않는다. 출력은 적색·근적외선·녹색 반사도와 거짓색 지도이며 자연색 RGB 또는 독립 검증된 NDVI 결과 제품이 아니다.

브라우저 fixture **3 passed**, 기존 실제 브라우저 시나리오는 명시 skip 상태라 이번 실행에서도 **1 skipped** (`optical-ui-recheck.log`, `optical-ui-live-recheck.log`). 현재 사용자 화면에서 실제 전체 흐름까지 재검증했다고 주장하지 않는다.

이전 개별 uvicorn 실행은 backend/.env를 로드하지 않아 AI 설정이 누락되어 있었다. 기존 `scripts/start-local.mjs`로 두 서버를 다시 시작하여 `/request/config` ready=true, missing_settings=[]를 확인했다. 새 키의 값은 출력하지 않았고 유료 OpenAI 호출은 수행하지 않았다. ready는 설정 존재 확인이며 인증·잔액·해석 성공 검증이 아니다.

## 분석 결과 가독성 정리 — 2026-11-06

구름 결과의 긴 면적 문장을 실측/추정/미해결 면적(km²)과 AOI 비율 카드로 분리했습니다. ML 상태·공간 보류 RMSE·참값 미검증 구분은 노출하고 방법/기준선 표는 접습니다. 상세 통계·계산식/출처, 기본 펼침이던 실행 기록, 작업 보관 안내, 연구 메모/저장 상세도 닫힌 details로 정리했습니다. 결과 지도·원관측/추정 구분·저장 버튼·실패 표시는 유지하고 글자 크기나 분석 로직은 바꾸지 않았습니다. 입력 QA 설명은 기본 제안값과 사용자가 입력한 적용값을 구분합니다.

TypeScript 검사 및 격리 production build 통과 (`test-results/outcome-readability-build.log`). 브라우저 fixture 5 passed (`outcome-readability-browser.log`): 390px/1440px ML 결과·접힘·ZIP/JSON 저장, 설명을 펼친 통계·메모·인용 접근, 실패 연구 기록 보존. `test-results/outcome-readability/ml-390.png`, `ml-1440.png` 화면 확인. 실제 사용자 Chrome 탭 상태를 읽거나 이번 변경에서 원본 처리/유료 AI를 호출한 것은 아닙니다.

## 실제 구름 관련 결측 ML 시연 검증 — 2026-11-06

사용자 요청에 따라 LIVE_STAC/LIVE_PROCESSING을 명시하고 실제 canonical 공개 STAC·Range 읽기로 후보를 탐색했습니다. 원본 QA·학습/검증 게이트를 바꾸거나 인공 구름을 넣지 않았습니다. 45개의 완료된 후보/QA 시험은 `test-results/real-cloud-demo/candidate-audit.json`에 보존했습니다. 이는 통과 사례를 선택한 데모 탐색이며 다지역 독립 성능 벤치마크가 아닙니다.

최종 bbox `[-115.175,35.96,-115.127,36.005]`, PC Landsat 8 목표 `LC08_L2SP_039035_20250719_02_T1`, 참조 `LC08_L2SP_039035_20250703_02_T1`, 기간 2025-07-01~31, 입력 QA **4K/1km**. 기본 2K와 구분합니다. 3K에서는 6셀, 4K에서 183셀을 추정했습니다. ML 게이트는 원래 RMSE≤2K 등으로 유지했습니다. 공간 보류 1,505개 RMSE **0.985796K**, MAE **0.767795K**, P95 **1.771291K**, 복사 RMSE **7.207810K**, 편향 보정 복사 **1.048927K**. 모든 공간 구역 오차 게이트와 전체 기준선 개선 게이트 통과.

실제 앱에서 직접 입력·검색·대상 선택·세부 분석 확정·ML/참조/QA 선택·계획·확인 실행·ZIP·연구 기록 JSON 저장을 실연결 Playwright로 **1 passed** (`browser-qa4.log`). 작업 `5460d121a518404a974e5bce987fba73`, ZIP 331,870 bytes, 추정 183셀/152,021.712m², 남은 결측 623,230.026m², 실측+추정 AOI 비율 97.1166%. ZIP 재열기 검증기도 thermal_ml 출처/단위/마스크/면적/통계를 지원하도록 보완하고 실제 브라우저 다운로드 파일에 적용해 통과했습니다. `test-results/real-cloud-demo/browser/`의 `job.json`, `real-cloud-ml.zip`, `research-record.json`, `verification.json`, `result.png`에 근거가 있습니다. 초기 브라우저 시도는 LIVE_STAC 환경 변수를 빠뜨려 안전 차단되었고 명시 후 실제 검색으로 재검증했습니다.

**범위:** 목표 AOI는 구름 그림자 및 구름 인접 결측이며 cloud/dilated/cirrus 비트 면적은 0입니다. 구름 관련 결측 0.751655km² 중 약 20.2%만 추정했습니다. 불투명 구름 전체 제거나 구름 아래 참값 정확도는 입증하지 않았습니다. 맑은 보류 오차를 실제 구름 아래 오차로 바꾸어 표시하지 않습니다. 제공처 RGB 미리보기 504는 별도 미해결 상태입니다. 유료 AI·사설 인증·mock 영상은 사용하지 않았습니다. 최종 입력값/설명은 [검증된 데모 안내](docs/VERIFIED_ML_DEMO.md). 추가 thermal_ml fixture **9 passed**, TypeScript noEmit exit0. 생산 모델 코드는 변경하지 않았습니다.

## 분석 준비·실행 화면 정리 — 2026-11-06

WorkSummary 처리 요약을 분석명/촬영일/다음 행동으로 축약하고 상세 기록을 접었습니다. AnalysisSelection 전처리 설명, ProcessingExecution 처리 방식·영상 메타데이터·제품 한도·일반 주의사항, ResearchGuide를 접습니다. 실행 입력·QA 기준·계획 확인/실행/다운로드·미지원/실패 표시는 유지합니다. 구름 전처리 미사용 시 다른 날짜 보충 설명이 나오던 문맥 오류도 수정했습니다. 글자 크기·처리 엔진은 변경하지 않았습니다.

TypeScript/최종 격리 production build 통과 (`test-results/processing-cleanup-build.log`). 초기 회귀 25 passed/2 failed는 접힌 상세의 버튼을 바로 누르던 테스트였으며 펼친 후 접근하도록 수정했습니다 (`processing-cleanup-browser.log`). 최종 처리/안내 11 passed (`processing-cleanup-final.log`): 1440px/390px 계획 확인→실행→ZIP 수신·해시·TIFF 재열기, 조건 변경 경합, 실패, 복원, 수집 복귀 검사. `test-results/processing-cleanup/`에 요약/설정 화면 저장 및 확인. 모두 TEST ONLY fixture이며 실제 위성 원본·유료 AI 호출은 없습니다.

## 분석 필수 밴드 자동 포함 — 2026-11-06

서버 분석 카탈로그의 제품별 required_keys 및 변수 매핑을 사용해 지원되는 선택 장면의 필수 밴드·QA를 자동 추가합니다. 분석 페이지 진입·복원·분석/장면 변경에 적용하며 기존 사용자 선택은 보존합니다. 존재하는 Asset만 포함하고 없는 필수 QA는 미제공·미확인으로 차단합니다. 자동 전송·처리는 없습니다.

TypeScript noEmit/격리 production build 통과 (`test-results/automatic-bands-build.log`), 분석 선택 브라우저 회귀 8 passed (`automatic-bands-browser.log`), PC Landsat qa/cdist 자동 포함·기존 선택 보존·반복 적용 불변·없는 Asset 차단 검사 1 passed (`automatic-bands-contract.log`). 실제 원본·유료 AI 호출 없이 fixture와 로컬 카탈로그로 검증했습니다.

## 세부 분석 선택 설명 정리 — 2026-11-06

AnalysisSelection의 각 라디오에서 반복되던 입력·추가 조건·산출물·엔진 설명을 선택한 분석의 닫힌 details 한 곳으로 이동했습니다. 분석 변경 시 다시 접히며 라디오 label 안에 상호작용 요소를 넣지 않았습니다. 실행 전 확인 항목도 details에 보관하고 자료 부족·미지원 경고와 확인 버튼은 유지합니다. 글자 크기와 처리 로직은 변경하지 않았습니다.

기존 분석 선택 회귀 8 passed (`test-results/analysis-disclosure-browser.log`), 추가 키보드 펼침·분석 전환 시 접힘·모바일/데스크톱 가로 넘침 검사 1 passed (`test-results/analysis-disclosure/interaction.log`). 같은 폴더의 `selection-390.png`, `selection-1440.png` 화면 증거. TypeScript noEmit, 격리 production build 통과 (`test-results/analysis-disclosure-build.log`). 검색·AI는 fixture이며 실제 유료 AI·원본 전송은 없습니다.

## 미리보기 반복 시간 초과 재확인 — 2026-11-06

사용자가 확인한 라스베이거스 `LC08_L2SP_039035_20250719_02_T1`의 공개 canonical STAC 조회는 성공했으나, canonical rendered_preview는 15.99초 후 HTTP 504 / `upstream request timeout`을 반환했습니다. `max_size=256` 요청도 15.97초 후 같은 오류였습니다(클라이언트 제한 35초). 근거: `test-results/preview-diagnosis-20261106/recheck.json`. 제공처 내부 원인·복구 시점은 미확인이고 미리보기 이미지를 복구한 것은 아닙니다. 원본 래스터·유료 AI 호출은 없었습니다.

ProviderPreview는 실제 HTTP 504와 앱의 제공처 응답 대기 timeout을 구분해 표시하며, 재시도/다른 날짜 선택과 원본·분석 별도 확인을 안내합니다. Earth Search 대체 PC 미리보기 timeout도 앞에 표시하되 원래 접근 실패는 상세에 보존합니다. 브라우저 fixture 7 passed / LIVE 1 skipped (`test-results/preview-repeat-browser.log`), TypeScript noEmit 및 격리 production build 통과 (`test-results/preview-repeat-build.log`).

## 데이터 수집 설명 간소화 — 2026-11-06

WorkSummary 수집 요약, 복원/추천 설명, Results 조회 통계·후보 해석을 native details로 접었습니다. 실패·부분 조회·제한 내역은 자동으로 열고 다음 행동과 다운로드 실패 안내는 밖에 유지합니다. 분석 페이지의 처리 설명/계산 엔진은 변경하지 않았습니다.

검증: TypeScript noEmit 및 격리 production build 통과 (`test-results/collection-disclosure/typecheck.log`, `build.log`). 기존 선택/미리보기/카드/추천 회귀는 24 passed, 3 skipped, 1 failed (`test-results/collection-disclosure-browser.log`). 실패는 직접 입력 모드에서 숨겨진 자연어 입력란으로 스크롤하던 기존 테스트로, 보이는 시작일 입력란을 사용하도록 수정 후 **1 passed** (`preview-scroll.log`). 추가 1440px/390px 접기·키보드 Enter·다음 링크·부분 조회 자동 펼침 **3 passed** (`disclosure.log`). 초기 추가 테스트의 스크린샷 locator는 숨겨진 분석 페이지 요약까지 중복 선택해 실패했으며, 접근성 region으로 범위를 좁힌 뒤 통과했습니다. `summary-390.png`, `summary-1440.png`에 화면 증거를 보관했습니다. 브라우저 영상/전송은 TEST ONLY fixture, 실제 원본 다운로드·유료 AI 호출·LIVE STAC 검증은 수행하지 않았습니다.

## Landsat ML 구름 결측 추정 — 2026-11-06

`thermal_ml`을 현재 지표면 온도 흐름에 선택형으로 추가했습니다. 기존 `thermal_gapfill`은 실제 다른 날짜 관측 선택, 새 방법은 목표 날짜 온도의 **ML 추정**입니다. NumPy ridge, 참조 온도·위치·상호작용 5변수, 학습 전용 표준화, 120m 간격 표본/공간 완충, 4구역 보류 검증을 사용합니다. 각 구역/전체 RMSE·MAE·95백분위 기준과 전체 단순 복사·중앙값 차이 보정 복사 대비 개선을 통과해야 합니다. 실패 시 상세 검증을 남기고 추정 ZIP은 생성하지 않습니다. 관측값 보존·학습 범위 및 2km 지지 제한·추정/실측/미해결·참조 날짜 분리, 모델 지문과 오차를 결과/연구 기록에 보존합니다. 명시적인 계획 확인 뒤 실행하며 유료 AI 호출은 없습니다.

검증 근거 `test-results/thermal-ml-20261106/`: 전체 backend **689 passed / 29 skipped** (`backend.log`), 기존 제품 및 신규 ML 모바일/데스크톱 브라우저 **20 passed** (`browser.log`), 격리 production build **exit0** (`build.log`). 추가 요청 장면 수/AOI 한도 검사 및 연구 기록 민감 필드 제거 검사는 `ml-final.log`, `browser-ml-final.log`; 최종 TypeScript는 `typecheck.log`. 초기 핵심/회귀 검사는 111 passed. 테스트 TIFF로 가린 정답값의 학습 제외, 실측 불변, 부족한 표본/참조/구름 부재/기준선 미개선/학습 범위 밖 차단, TIFF/출처/실행 기록 재열기를 확인했습니다.

**실제 자료 + 시험용 인공 구름**: LIVE_STAC=1/LIVE_PROCESSING=1, PC 공개 canonical Item 및 Range 읽기, Las Vegas bbox `[-115.17,36.14,-115.13,36.18]`, 목표 `LC08_L2SP_039035_20250719_02_T1`, 참조 `LC08_L2SP_039035_20250703_02_T1`. 실제 래스터를 읽은 뒤 테스트에서만 중앙 20%×20% 구역을 구름처럼 가리고 학습에서 제외했습니다. 공간 보류 791개 RMSE **0.6523K**, MAE **0.5189K**, 95백분위 **1.2573K**. 동일 보류 위치의 원본 복사 RMSE **8.0763K**, 편향 보정 복사 **1.1530K**. 별도 인공 가림 영역의 추정 725개를 보관한 실제 원관측과 비교한 RMSE **0.6579K**, MAE **0.5655K**. 전송 1,163,264bytes/46requests; 테스트 1 passed (`live.log`). 상세 지표·계수·분할·정책은 `public-simulated-cloud.json`, 테스트 전용 ZIP은 `public-simulated-cloud.zip`입니다. **실제 구름 아래 정답, 다른 지역·시기 정확도, 온도 변화 분석 적합성은 미검증**입니다. 사용자 실제 원본이나 QA를 수정한 것이 아니며 생산 코드에 인공 마스크/fallback이 없습니다. [방법 계약·출처](docs/THERMAL_ML_METHOD.md).

## 불필요한 처리 경고 제거 — 2026-11-06

`WorkflowWorkspace`의 processingStale은 실제 과거 결과 유무와 무관하게 밴드·설정·세부 분석 선택 시 true가 되어 첫 입력에도 경고를 표시했습니다. 해당 배너와 배너 전용 상태를 제거했습니다. 품질·지도 무효화와 작업별 context 불일치 안내는 유지했습니다. 기존 analysis-selection 브라우저 회귀 8 passed, TypeScript noEmit exit0, 격리 production build exit0. 근거: `test-results/stale-banner-20261106/`. 실제 유료 AI·위성 원본 호출 없이 검증했습니다.

## 구름 결측 전처리 — 2026-11-05

최종 backend **681 passed / 28 skipped**, 기존 브라우저 회귀 **38개 통과**(37개 최초 통과 + 서버 재시작과 겹친 연결 거부 1개 재실행 통과), 실제 공개 자료 브라우저 **1 passed**. TypeScript noEmit·격리 production build exit0. 근거: `test-results/cloud-preprocessing-20261105/`의 `backend-final.log`, `browser-regression.log`, `browser-retry.log`, `browser-live-verified.log`, `typecheck.log`, `build-final.log`.

`thermal_gapfill`을 지표면 온도 전처리에 명시 선택으로 연결했습니다. 테스트 TIFF는 원관측 보존·구름/그림자/구름 거리 탈락 보충·보충 QA 실패·두 날짜 구름·일반 NoData·불확실성 단독 실패의 결측 유지·출처 인덱스/날짜·독립 저장/재열기를 확인합니다. 동일 플랫폼/L2SP·서로 다른 날짜/31일·기존 한도와 파일 검증을 유지합니다. 화면과 연구 기록은 날짜별 통계·보충 면적·남은 결측을 구분합니다. [방법 계약](docs/THERMAL_CLOUD_PREPROCESSING.md).

실제 연결: LIVE_STAC=1/LIVE_PROCESSING=1, PC 공개 검색과 Range 읽기. Las Vegas bbox `[-115.17,36.14,-115.13,36.18]`, 대상 `LC08_L2SP_039035_20250719_02_T1`, 보충 `LC08_L2SP_039035_20250703_02_T1`. 실제 픽셀 작업→브라우저 ZIP 다운로드→모든 TIFF/CRS/격자/NoData/단위/해시/출처 날짜/수치 검증→연구 기록 JSON 저장을 통과했습니다. 이 표본은 구름 결측이 없고 주로 ST 불확실성 탈락이어서 **보충 0 m²**, 원래 유효 11,806,765.79 m², 유효율 73.9069%, 남은 결측 4,168,420.96 m²입니다. 이 실제 표본을 구름 제거 개선 실증으로 표현하지 않습니다. 구름 채우기는 테스트 전용 TIFF에서 확인했으며 구름 아래 참값 정확도는 미검증입니다. 결과 ZIP·연구 기록·검증 JSON·화면은 `live-delivery/thermal_gapfill/`에 보존했습니다. 유료 OpenAI는 호출하지 않았습니다.

초기 검증 문제도 기록합니다. 루트에서 실행한 전체 pytest의 자식 프로세스 4건은 app import 경로 문제였으며 backend 작업 디렉터리에서 전부 통과했습니다. 새 방법의 공통 exclusion_mask 계약 누락 1건은 파일을 추가해 수정했습니다. 브라우저 검증기의 출력 경로 변수와 ndarray 이름 충돌을 수정했습니다. 실제 표본에 보충 면적 >0을 요구한 테스트 가정은 원본 QA 제외 사유와 맞지 않아 제거하고, 보충 0 및 결측 유지 안내·연구 기록 보존을 검사하도록 바꿨습니다.

---

## 분석 장소 직접 수정 — 2026-11-05

최종 브라우저 **16 passed**, TypeScript noEmit·production build **exit0**.

기존 ‘분석 장소’가 readOnly여서 확인된 구미 지명을 수정할 수 없었다. 보이는 입력란을 기존 직접 지명 조회 상태와 연결하고 ‘장소 찾기’를 추가했다. 확인한 위치 선택·복원 시 입력값을 동기화하고 지우기·새 지명 입력을 허용한다. 입력만으로 AI/위치 조회를 호출하지 않으며 버튼 또는 조합 완료 후 Enter로 조회한다. 기존 좌표·확정 AOI는 보존하고, 새 입력과 마지막 확인 위치를 구분해 표시한다. 해외 지역은 좌표 직접 지정도 가능하다.

검증 근거: `test-results/place-edit-20261105/`. `place-edit.spec.ts`는 확인된 장소 수정·빈 문자열·새 장소 조회/선택·기존 AOI 보존·추가 AI 무호출을 fixture로 검사한다. 기존 `ai-camera.spec.ts`, `ai-conditions.spec.ts`도 함께 실행한다(`browser.log`). TypeScript noEmit·격리 production build 결과는 `types.log`, `build.log`에 기록한다. 실제 유료 OpenAI·Kakao 조회는 하지 않았다. 프런트 개발 서버에 반영했으며 사용자의 입력값을 대신 변경하거나 검색을 실행하지 않았다.

---

## 위성 선택과 검색 대기 이유 구분 — 2026-11-05

최종 Playwright **7 passed / 6 LIVE skipped** (`release.log`), TypeScript·격리 production build **exit0**. 최초 추가 회귀 검사는 열환경 목적에서 지원하지 않는 S2 카드를 고르도록 작성되어 중단했고, 사용자의 실제 흐름에 맞는 Landsat 카드로 고친 뒤 전체 대상 파일을 재실행했다. 사용자 VS Code 화면에서도 선택 제품·미확정 사유·직접 입력 전환 버튼이 동시에 표시되는 것을 확인했다.

사용자 화면에서 Landsat L2SP 카드가 이미 선택되고 검색 컬렉션도 landsat-c2-l2로 반영되어 있음을 확인했습니다. 검색 차단은 과거 AI 해석 결과 미확정 상태였습니다. 선택한 제품·최종 컬렉션을 접힌 설명 밖으로 옮기고, 검색 버튼 바로 위에 구체적인 대기 이유와 ‘현재 조건으로 직접 입력 전환’을 표시합니다. 전환은 AI를 재호출하지 않으며 제품 선택을 유지합니다. 목적·날짜·AOI 확정은 별도입니다.

근거: `test-results/search-selection-20261105/`. 실제 VS Code 내장 브라우저의 접근성 정보에서 선택 제품 L2SP·landsat-c2-l2·카드 선택 상태와 ‘해석 결과 확인 필요’를 함께 확인했다. 위성 선택 저장 결함으로 단정하거나 AI 확인을 자동 우회하지 않았다. `WorkflowWorkspace.tsx`는 기존 검색 차단 조건을 유지하고 안내·명시 전환 버튼·aria-describedby만 변경했다.

`ai-recovery.spec.ts`에 미확정 복원 → 제품 카드 선택 반영 → 검색 대기 이유 표시 → 명시 직접 입력 전환·AOI 확정 → 검색 활성화·제품 선택 유지·추가 AI 무호출 회귀 검사를 추가했다. `ai-recovery.spec.ts provider-activation.spec.ts`의 최종 결과는 `browser.log`, TypeScript noEmit은 `types.log`, 격리 production build는 `build.log`에 기록한다. AI 응답은 fixture이며 실제 유료 AI·STAC 검색은 실행하지 않았다. 프런트 변경은 실행 중 로컬 개발 서버에 반영된다. 사용자의 현재 입력·선택은 조작하지 않았다.

---

# USGS M2M 원본 바로 다운로드 — 2026-11-05

사용자가 M2M 승인 메일과 EarthExplorer 링크 화면을 제공하고 앱에서 직접 다운로드하도록 요청했다. 기존 서버는 USGS 활성·정책 검토·자격 등록 상태였으며 자격/정책/쿼터를 바꾸지 않았다. 근거: `test-results/usgs-direct-20261105/`.

## 결함과 수정

실제 `/media/inspect`가 `LC08_L2SP_115035_20260711_02_T1`의 `qa_pixel`을 `operator_file_unavailable`로 반환했다(`probe.json`). M2M scene-metadata에서 정확한 처리제품 `LC08_L2SP_115035_20260711_20260720_02_T1`이 확인됐으며 download-options는 같은 파일을 네 부모 목록에 반복 반환했다(`options.json`, 비밀값 제외). 기존 후보1개 검사가 이를 다른 파일로 오인했다.

`operator_adapters.py`는 secondary file의 entityId+productId가 같은 경우만 중복 제거한다. 다른 식별자·상충 checksum/filesize·누락 식별자는 거절한다. 정확한 제품/파일명·허용 호스트·인증 분리·전체 수신 검증을 보존한다. 번들로 대체하거나 AWS requester-pays를 활성화하지 않았다.

`ManagedAssetAccess`의 밴드별 **바로 다운로드**는 클릭한 파일 하나의 canonical 접근을 확인한 뒤 기존 수신 함수로 저장한다. 초기 화면·선택만으로 원본을 받지 않는다. 오류·진행·완료 상태, 중복 클릭 방지, 선택/인증 변경 취소, 만료 접근1회 갱신과 기존 파일 상한을 유지한다. 기존 일괄 접근 확인도 유지하며 Landsat 안내는 USGS 서버 경로를 설명한다.

## 실제 파일과 브라우저

- API에서 QA_PIXEL GeoTIFF 전체 **3,968,136 bytes** 수신(`probe-final.json`, `download-result.json`). rasterio 재열기: GTiff, EPSG:32652, 7771×7891, 단일 밴드, 실제8×8 픽셀 읽기 성공.
- `LIVE_STAC=1` Playwright `direct-download.spec.ts --grep 'LIVE USGS'`: **1 passed**. 수동 목적·2026년7월·구미 중심10×10km → 실제 Earth Search 검색 → 같은 장면 QA_PIXEL만 선택 → 바로 다운로드 → 브라우저 저장. AI는 runtime에서 차단했다. EarthExplorer 이동 없이 성공했다(`live-browser.log`, `live-browser/`).
- 브라우저 저장 SHA-256 **1ce0c1cd79236089dbcc8ffdf82c512a4cec11a2ffc2a0e0bf0a544a44eaecce**, API 파일과 바이트·해시 일치, GeoTIFF 재열기 성공(`browser-file-verification.json`). 실제 검증은 이 장면의 QA_PIXEL이며 모든 밴드·장면 성공을 뜻하지 않는다.

## 회귀와 빌드

- backend cwd에서 `pytest tests/test_usgs_duplicate_options.py tests/test_operator_access.py -q --disable-warnings`: **36 passed**, 경고1 (`backend-final.log`). 최초 루트 cwd 실행은 child process의 app import 경로 때문에1실패/35통과였고 올바른 backend cwd로 전체 재실행했다. 새6건은 중복·충돌·미제공 fixture 검사다.
- `media-access.spec.ts`: **16 passed / 1 LIVE skipped** (`browser.log`). `workflow-pages.spec.ts`: **7 passed** (`browser-final.log`). 함께 실행한 신규 테스트는 Edge 자체 다운로드 화면을 외부 페이지로 오인해 실패했다. 이미지로 확인한 뒤 외부 HTTP(S) 이동만 검사하도록 수정했다. 최종 `direct-download.spec.ts --grep 'TEST ONLY'`: **2 passed** (`direct-final.log`). 성공·권한 거절·클릭 전 무수신·390px 넘침 없음을 확인했다. 실제1건은 위 기록과 구분한다.
- 최종 TypeScript noEmit·격리 Next.js production build 각각 **exit0** (`typecheck-final.log`, `build.log`). 실행 중 dev 캐시는 건드리지 않았다.
- 수정 반영 후 서버 재시작, backend health·첫 화면·processing HTTP200 (`health.json`, `main-pid.txt`, `logs/20261105-usgs-direct-*.log`).

[USGS M2M 설명](https://www.usgs.gov/landsat-missions/landsat-data-access)·[Application Token](https://www.usgs.gov/media/files/m2m-application-token-documentation)·[Landsat 사용·재배포 정책](https://www.usgs.gov/faqs/are-there-any-restrictions-use-or-redistribution-landsat-data)을 확인했다. JSON 문서는 로그인으로 리다이렉트되어 열리지 않았고 실제 계정의 제한된 endpoint 응답으로 중복 파일 구조를 확인했다. 키·세션 토큰·서명 URL은 출력/기록하지 않았다. 같은3.97MB 파일을 API1회·브라우저1회 수신했고 임의 일괄 다운로드는 하지 않았다.

---

# 직접 입력 간소화·설정 한도·승인된 AI 진단 1회 — 2026-11-05

근거 폴더: `test-results/manual-ai-settings-20261105/`.

## 실제 진단 결과

사용자가 “비용이 발생할 수 있는 진단 1회 허용”으로 승인했다. `diagnose_once.py`는 exclusive 실행 마커로 중복 실행을 막고, 설정 반영 후 현재 모델 gpt-4o로 “2026년 7월 충남의 집중호우 전후 침수 범위를 분석하고 싶어.”를 정확히 한 번 전송했다. 재시도하지 않았다. 응답은 **HTTP429 / credit_balance_exhausted / quota_exceeded**였다(`diagnosis-result.json`, `diagnosis.log`, `diagnosis-started.json`). 목적·날짜 추출 성공이 아니며, 보고 토큰0은 무료 청구를 증명하지 않는다(`unknown_usage_calls=1`).

[OpenAI 공식 오류 문서](https://developers.openai.com/api/docs/guides/error-codes)에 따라 선불 크레딧 소진으로 분류했다. 운영자의 API Billing 충전이 남아 있다. 키·모델 교체, 잔액 구매, 계정 예산 변경은 하지 않았다. 화면도 이 코드에 한해 선불 크레딧 소진·충전 필요를 구체적으로 안내하도록 수정했다. 다른429는 기존 분류를 유지한다. 서버 재시작으로 요청 집계가0이 되어도 계정 잔액 회복을 의미하지 않는다.

## 변경과 검증

- 직접 입력에서는 자연어 textarea·중복 분석 분야를 숨기고, 한 줄 안내·전환 버튼·접힌 과거 오류만 유지한다. 목적·날짜·AOI 선택과 새로고침 복원을 보존한다. 자연어 모드로 돌아오기만 해서는 전송하지 않으며, 미처리 기존 문장은 명시적 재시도를 안내한다.
- 서버 전용 환경변수 `AI_NL_TIMEOUT_SECONDS=45`, `AI_NL_MAX_OUTPUT_TOKENS=4000`, `AI_NL_REQUESTS_PER_MINUTE=6`, `AI_NL_REQUESTS_PER_PROCESS=100`을 실제 backend/.env와 예시에 설정했다. 런처 allowlist를 연결하고 프런트 환경에서는 계속 제거한다. 비밀값은 출력·백업하지 않았다. 서버 기본값12초/2000토큰은 유지하며 설정 범위는 각각10–90초/1000–8000토큰/1–20회/1–1000회다. 브라우저 대기는 서버+5초로 맞춘다. 앱 제한은 OpenAI 계정 제한과 별개다.
- `pytest backend/tests/test_ai_config_limits.py backend/tests/test_ai_interpretation.py backend/tests/test_ai_provider_errors.py -q --disable-warnings`: **42 passed**, 경고1개 (`backend.log`). 모든 응답은 fixture이며 추가 유료 호출은 없다.
- `node --test scripts/server-env.test.mjs`: **19 passed** (`env-tests.log`). 실제 서버의 공개 config에서45초/4000토큰 적용을 확인했다.
- Playwright `manual-compact.spec.ts ai-recovery.spec.ts ai-conditions.spec.ts ai-camera.spec.ts workflow-pages.spec.ts search.spec.ts --workers=1`: **32 passed / 1 skipped** (`browser.log`). AI·위치는 fixture, 실제 STAC 테스트는 LIVE_STAC 미설정으로 생략했다.
- 마지막 자연어 전환 안내 변경 후 `manual-compact.spec.ts`: **3 passed** (`browser-final.log`). 390/1440px에서 간소화·수동 검색 준비·복원·가로 넘침 없음·AI 무호출을 확인하고 두 크기 스크린샷을 점검했다. 17초 지연 fixture로 이전15초 조기 실패가 발생하지 않음을 확인했다.
- 최종 TypeScript noEmit / 격리 production build: 각각 exit0 (`typecheck-final.log`, `build-final.log`). 격리 복사 시 최초 상대경로 오류가 있었고, 정확한 경로로 최신 파일을 다시 복사한 뒤 최종 build를 실행했다. 실행 중 dev 캐시는 건드리지 않았다.

로컬 서비스 최종 재시작·상태는 `main-pid-final.txt`, `health-final.json`, `logs/20261105-manual-ai-final-*.log`에 기록한다. AI 실제 성공 검증은 크레딧 충전 전 불가이며 이번 승인1회는 이미 소진했다. 영상 처리 엔진은 변경하지 않았다.

---

# ResearchRecord 모듈 해석 오류 신고·재빌드 — 2026-11-05

사용자가 Next.js16.4.3 Webpack의 `ProcessingExecution.tsx → ./ResearchRecord` 모듈을 찾지 못하는 오류를 신고했다. 현재 소스의 `frontend/src/components/ResearchRecord.tsx`, export default, 상대 import의 이름·위치를 확인했고 실행 서버도 이 workspace를 사용하고 있었다. 조사 시점 `/processing`은 HTTP200이었고 현재 서버 로그에는 해당 오류가 없었다. **신고 오류는 현재 상태에서 재현되지 않았으며 오래된 개발 빌드/브라우저 상태 가능성은 추정이다.**

진행 중 처리 worker가 없음을 확인한 뒤 해당 로컬 launcher만 종료했다. 정확히 확인한 workspace의 `frontend/.next`를 `test-results/module-resolution-20261105/next-cache-before/`로 이동·보존했다. 소스를 복사한 격리 폴더가 아니라 **실제 frontend 작업 폴더**에서 `next build --webpack`을 새 캐시로 실행했고 compilation·TypeScript·페이지 생성이 모두 exit0으로 통과했다. `ResearchRecord`·직렬화 helper·호출 컴포넌트의 SHA-256은 작업 전후 동일하다. 정상 파일을 빈 구현으로 대체하거나 기능을 제거하지 않았다.

로컬 서비스를 재가동했다. 기존 `product-engines.spec.ts --grep 'researcher|failed research' --workers=1`은 **3 passed**: 모바일390px/데스크톱1440px 결과 표시와 연구 기록 JSON 저장, 실패/과거 작업의 기록 저장을 실제 브라우저에서 검증했다. 명시 fixture이며 유료 AI나 실제 제공처 처리를 호출하지 않았다. 루트·처리 페이지·백엔드 health HTTP200, 모듈 누락 문구 없음까지 확인했다.

근거: `test-results/module-resolution-20261105/build.log`, `browser.log`, `browser/`, `source-before.json`, `health.json`, `main-pid.txt`; 실행 로그 `logs/20261105-module-restart-*.log`. 이전 캐시는 보존했다. 브라우저에 이전 오류 오버레이가 남아 있으면 해당 페이지를 새로고침해야 한다. AI 계정의 이전429 해제 여부와는 별도 검증이다.

---

# 반복 AI 실패: 제공처 한도·복원 원인 표시 수정 — 2026-11-05

사용자가 ‘2026년 7월 충남의 집중호우 전후 침수 범위를 분석하고 싶어.’를 입력한 화면에서 AI 해석 실패와 ‘해석 도중이거나 미확정인 문장을 복원했습니다’가 나타나는 문제를 신고했다. 근거 폴더: `test-results/ai-recovery-20261105/`.

## 확인된 원인

1. **실제 제공처 실패:** 수정 전 실행 서버의 공개 `/request/config`는 설정 준비 true, 모델 `gpt-4o`, 실제 AI 요청1/성공0/실패1, 마지막 상태 `limited`, 청구량 미확인1이었다. 이 상태는 해당 코드 경로에서 OpenAI HTTP429 응답을 뜻한다. 앱 자체 분당6회/프로세스100회 제한에 도달한 요청 수가 아니다. 기존 구현이 제공처 오류 본문의 코드를 버려 **크레딧·예산·할당량 부족인지 일시적인 요청률 제한인지는 확인 불가**다. `server-config-before.json`, `server-config-before-restart.json`에 같은 상태를 보존했다. 서버 재시작 전후 수치를 섞어 한도가 해제됐다고 주장하지 않는다.
2. **복원 오류:** 작업 보관은 해석 결과·실패 원인을 저장하지 않고 `inputConfirmed` 한 값만 보관했다. AI 성공 뒤에도 지역 후보/기준일 확인이 남으면 false이므로 새로고침 후 모두 failed로 바꾸고 원래 오류를 일반 복원 메시지로 덮었다. 사용자 화면의 문구는 이 경로에서 생성된다. 실제 해석이 성공했지만 확인이 남은 경우와 실제 API 실패 두 시나리오를 브라우저 fixture로 재현해 수정 전 둘 다 실패했다(`before.log`).

## 수정

- 문장과 연결된 해석 상태·제안·원래 오류·명시 수동 모드·수동값 유지 확인을 보관한다. 새로고침 시 AI 성공과 미해결 조건을 보존하고 자동 AI/위치 재호출을 하지 않는다. 정상 AI 결과를 직접 입력 모드로 바꾸지도 않는다.
- AI 결과가 없거나 진행 중에 화면을 벗어난 경우는 ‘해석 결과 확인 필요’로 표시한다. 오래된 기록의 잃어버린 오류는 미확인으로 남긴다. 다른 문장의 해석을 현재 문장에 적용하지 않는다.
- AI 추출 이후 위치 조회만 중단됐다면 추출 목적·기간을 유지하고 위치 확인만 다시 하도록 안내한다. 기존 검색 차단·AOI·수동 날짜 보호는 유지한다. 사건 기준일이 필요한 상태는 AI 실패로 표시하지 않는다.
- OpenAI 비정상 응답을 64KiB까지만 읽고 공개 allowlist 오류 코드만 보존한다. `insufficient_quota`, 크레딧 소진, 조직/프로젝트 지출 한도 및 조직 사용 한도는 `quota_exceeded`로 분리하고 운영자의 API Billing·Limits 확인을 안내한다. 요청률 제한·slow_down 및 알려지지 않은429는 따로 표시하며 알 수 없는429를 잔액 부족으로 단정하지 않는다. 제한된 Retry-After 초 값이 있으면 안내한다. 원문 오류·키·헤더는 반환하지 않는다. 자동 유료 재시도는 추가하지 않았다.

분류 근거는 [OpenAI 공식 오류 코드 문서](https://developers.openai.com/api/docs/guides/error-codes)에서 429의 원인별 코드·조치·Retry-After를 확인했다. OpenAI Docs 스킬을 적용했다. 모델·API 키·유료 호출 한도를 변경하지 않았고 실제 유료 AI 요청은 실행하지 않았다.

## 검증

| 검사 | 결과 | 근거 |
|---|---|---|
| 수정 전 성공/실패 복원 재현 | 예상한 2 failed | `before.log`, `before/` |
| `pytest backend/tests/test_ai_provider_errors.py backend/tests/test_ai_interpretation.py -q --disable-warnings` | **38 passed**, 경고1건 | `backend.log` |
| 최종 Playwright `ai-recovery.spec.ts ai-conditions.spec.ts ai-camera.spec.ts workflow-pages.spec.ts --workers=1` | **27 passed**, 모두 명시 AI/위치 fixture | `release.log`, `release/` |
| TypeScript noEmit / 격리 production build | 각각 exit0 | `typecheck.log`, `build.log` |
| 로컬 서비스 재시작 후 첫 화면·프런트/백엔드 health | HTTP200 | `health.json` |

브라우저는 원래 오류 보존·새로고침 무호출·지역 후보/기준일 확인 유지·AI/수동 출처·수동 날짜 보존·중단된 위치 조회·과거/다른 문장 상태를 검사한다. 390px의 복원 후 확인/할당량 안내 스크린샷을 확인했다. 백엔드는 제공처 코드 allowlist, 알려지지 않은429, 과대/깨진 본문, 비밀 원문 미반환, bounded Retry-After, 기존 실제 날짜/근거 검증·실패 fallback 금지를 검사한다. 초기 새 transport 테스트1건은 공통 테스트의 유료 호출 차단 장치 때문에 실패했으며, 명시 httpx.MockTransport를 사용하는 로컬 전송 함수 검사로 고친 뒤 전체38건 통과했다. 외부 호출을 허용해 통과시킨 것이 아니다.

수정은 로컬 서비스3000/8000에 반영했다(`main-pid.txt`, `logs/20261105-ai-recovery-*.log`). 재시작 후 프로세스 AI 요청 수0은 집계 초기화이며 이전 OpenAI429의 해결 근거가 아니다. **OpenAI 계정 크레딧·예산/요청 제한의 실제 해제와 유료 해석 성공은 아직 미검증**이다. 이전 화면에 이미 사라진 상세 오류 코드도 소급 복구하지 못한다. 앞으로 받은 실패는 원인과 상태를 보존한다. 연구 QA/래스터 엔진은 이번 변경 대상이 아니다.

---

# 대학원생 관점의 연구 해석·재현 흐름 개선 — 2026-11-05

사용자가 ‘의문’은 단순 오류 안내가 아니라 **대학원생이 사이트를 직접 쓰면서 생기는 연구상의 질문**이라고 명확히 했다. 기존 구미 중심부 약 10×10km·2026년 7월·지표면 온도 사례를 기준으로 실제 검색→장면 선택→분석 조건 화면을 다시 사용하고, 성공 결과·실패 결과는 구분된 실제 TIFF fixture로 검증했다. 근거: `test-results/graduate-review-20261105/`.

## 연구자의 질문과 반영

| 사용 중 드는 의문 | 확인한 상태·수정 |
|---|---|
| 왜 이 센서이며 30m 온도 지도는 30m 독립 관측인가? | 기존 추천 카드에 제품·필수 밴드·원관측/출력 격자 근거가 있었다. 실행 위치에 100m 열관측/30m 제품 격자, 타일 수≠촬영 수, 지표면 온도≠기온 해석을 연결했다. 새 추천 규칙을 만들지 않았다. |
| 2K·1km가 논문에 쓸 공식 통과 기준인가? | 앱 운영값과 제공처 QA 밴드 정의를 구분했다. 지역 평균의 ±2℃ 신뢰구간이나 실제 오차 보장으로 해석하지 않으며 기준 채택 이유·별도 조건 비교를 남기도록 안내했다. 온도 민감도/신뢰구간 자동 계산은 구현하지 않았다. |
| 성공했는데 평균은 어디에 있고 무엇의 평균인가? | JSON에 묻힌 온도·지수 평균/최솟값/최댓값을 수치 카드로 표시한다. 공통 유효 영역만의 평균, 제품 엔진의 AOI 교차 면적 가중, 최솟값/최댓값≠신뢰구간을 설명한다. 두 영역 비교는 차감 방향·각 영역 유효율, 수역 변화는 후보 증가/감소를 표시한다. 기존 계산을 바꾸지 않았다. |
| 두 지도의 같은 색이 같은 온도·지수인가? | 실제 제품 미리보기가 각 영상의 유효 픽셀 2–98백분위로 자동 조정되지만 수치 범례가 없었다. 표시 함수가 사용한 범위·단위·실제 끝 색을 반환하고 결과와 지도에 범례를 추가했다. 일정한 값은 단일 색이며, 화면의 끝 색 제한은 TIFF 수치 절단이 아니다. |
| 일부만 유효한 결과를 도시 전체 또는 월평균으로 써도 되는가? | 현재 QA 통과 영역에 한정된 결과이며 제외 지역·다른 날짜 선택의 편향을 검토하도록 안내한다. 기존 단일 촬영일/검색 기간·bbox/행정경계 구분을 유지했다. 도시 전체나 월평균을 새로 계산하지 않았다. |
| 실패하면 ZIP이 없는데 실험 이력은 어떻게 보관하는가? | 성공·실패·취소의 연구 기록 JSON 저장을 추가했다. 해당 작업의 실제 입력·장면·QA·기록된 제외 사유, 성공 시 통계·격자·계산식·ZIP SHA-256·실행 단계, 선택 연구 메모를 저장한다. 현재 다른 장면/조건으로 바꾸어도 과거 작업 입력을 저장한다. 과거에 없는 진단은 만들지 않는다. |
| 논문에는 어떤 자료를 인용하고 무엇을 남기는가? | Landsat 8/9 Collection 2 데이터셋 DOI와 USGS ST/QA 문서를 실행 화면에 연결했다. 장면·UTC 날짜·AOI·QA·선택 근거와 함께 기록하며 성공 ZIP/manifest·원본·실행 환경을 별도 보관하도록 안내한다. JSON만으로 완전한 수치 재현이나 논문 방법 절 완성을 주장하지 않는다. |

공식 근거는 [USGS ST 제품·보정식·데이터셋 인용](https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature), [USGS QA 밴드 정의](https://www.usgs.gov/landsat-missions/landsat-collection-2-quality-assessment-bands), [Landsat 8–9 Level-2 Collection 2 DOI](https://doi.org/10.5066/P9OGBGM6)이다. 2026-11-05 원문을 확인했다. 앱 운영 임계값을 제공처의 보편적 권장 임계값으로 바꾸어 표현하지 않았다.

## 실제 이용과 fixture 검증 구분

- `LIVE_STAC=1`의 수정 전·후 실제 구미 공개 PC Landsat 검색/장면 선택을 각각 실행했다. bbox `[128.28865,36.07461,128.39985,36.16453]`, UTC 2026-07-01~31, 반환 8장면, 선택 `LC08_L2SP_115035_20260711_02_T1`. `live-search-summary.json`, `live-before.txt/png`, `live-after.txt/png`가 근거다. 자연어 새 입력·유료 OpenAI 재시도·새 실제 픽셀 처리는 하지 않았다. 테스트는 처리 작업 POST도 차단·0건 확인했다.
- 성공 결과 화면의 **29.661℃는 고정 DN=45000의 명시 TEST ONLY TIFF fixture 값**이다. 구미의 실제 온도 측정으로 보고하지 않는다. 실제 구미 두 날짜의 앞선 QA 보류와 분리한다. 이번에는 기존 제품 엔진의 TIFF 계산·ZIP 저장·브라우저 재열기와 새 연구 기록의 일치를 검사했다.
- 최종 backend: `pytest backend/tests/test_research_preview.py backend/tests/test_product_engines.py backend/tests/test_processing_failure_details.py -q --disable-warnings` → **75 passed**, 경고 887건, 5.90초 (`backend.log`). 마스크 밖 극단값 제외, 실제 색 끝점, 일정값/미관측 범례, 수치 배열 불변과 기존 제품/QA 처리를 검사했다.
- 최종 Playwright: `product-engines.spec.ts research-record.spec.ts graduate-live.spec.ts --workers=1`, `LIVE_STAC=1`, `GRADUATE_AFTER=1` → **19 passed**. **18건은 명시 fixture/로컬 기록 검증, 1건은 실제 공개 검색 UI**다 (`e2e-release.log`, `browser-release/`, `fixtures-release/`). 모바일390px/데스크톱1440px, 성공·실패 JSON 실제 다운로드, 저장 전후 조건·수치·해시 일치, 무단 실행 없음, 타 조건 혼입 방지, 기록에서 접근 필드 제외, 행정경계 출처·연도·해시 보존, 미기록값 미확인을 포함한다.
- 최초 브라우저 실행은 15 passed/2 failed: 이름을 줄 수 없는 generic 요소로 범례를 조회했다. 실제 범례를 접근성 group으로 고친 뒤 1 passed/2 failed: 연구 기록에서 `boundary_metadata`가 누락됨을 발견했다. 경계 출처를 보존하도록 수정한 후 관련4건 통과, 마지막 전체19건 통과했다. 최초 실패·중간 재검증 로그를 보존했다(`e2e.log`, `e2e-final.log`, `e2e-verified.log`).
- TypeScript noEmit 및 최신 소스 격리 production build 모두 exit0. 최종 화면의 수치/범례 PNG를 열어 확인했다. 이전 실행 수를 이번 결과로 합산하지 않았다.

로컬 서비스를 수정 코드로 재시작해 3000/8000에서 실행 중이다. 작업 worker가 없음을 확인한 뒤 기존 launcher만 종료했다(`main-pid.txt`, `logs/20261105-graduate-restart-*.log`). 처리 페이지/프런트·백엔드 health HTTP200은 `health.json`에 기록한다. 메모리 전송 예약은 재시작으로 초기화되며, 한도를 높이거나 실패한 QA 기준을 완화하지 않았다.

범례는 이번 제품 엔진의 새 결과에 붙는다. 기존 결과에 없는 수치 범례를 추정하지 않는다. 실제 유료 AI·전체 센서/지역 품질·구미 월평균·독립 참값·통계적 유의성·인증 원본·공개 배포 검증은 이번 범위 밖이다. 연구 기록은 읽기 쉬운 실행 근거 보관 기능이며 자동 연구 타당성 승인 도구가 아니다.

---

# 구미 흐름의 의문·보류 안내 개선 — 2026-11-05

사용자가 요청한 ‘해당 과정에서 생긴 의문 수정’을 앞선 구미 중심부 약 10×10km 이용 흐름에 적용했다. 새 자연어/AI 재시도는 실행하지 않았다. 근거 폴더: `test-results/workflow-questions-20261105/`.

## 수정한 동작

- **왜 제한됐고 언제 다시 시도하는가:** 개인·공용 전송 예산을 모두 검사한 뒤 예약하며, 거절 시 가장 늦게 해제되는 해당 시간 창의 재시도 시각을 반환한다. UI는 대기 중 계획 재검사를 막고 남은 시간을 표시한다. 예약량은 실제 수신 바이트와 다르고 시작한 작업의 예약은 실패해도 유지됨을 설명한다. 대기 종료는 자동 실행이 아니며 다른 이용량에 따라 재차 제한될 수 있다.
- **왜 QA에서 보류됐는가:** 모든 필수 장면·타일 읽기가 완료된 무효 픽셀 결과에만 별도 진단을 저장한다. AOI·공통 관측·유효 면적, 기본 QA·온도 불확실성·구름 거리 등의 제외 면적과 적용 기준을 보여 준다. 제외 사유는 서로 겹치며 더할 수 없다. 분석 평균·결과 유효율은 기존 null을 유지하고 ZIP/지도를 만들지 않는다. 통신/부분 읽기 실패와 과거 기록에는 없는 숫자를 만들어 넣지 않는다.
- **다음에 무엇을 하는가:** 같은 검색의 지원 제품 중 다른 촬영일을 선택할 수 있다. AOI·기간·QA 기준을 유지하며 장면 변경만 한다. 계획과 실행은 다시 명시 확인한다. 이전 조건의 실패는 구분 표시한다.
- **7월 결과가 월평균인가:** 온도 실행은 선택한 한 UTC 촬영 시점이며, 검색 기간의 월평균/기간 평균 계산이 아님을 실행 전 표시한다.

## 이번 실제 공개 원본 재검사

`LIVE_STAC=1`, `LIVE_PROCESSING=1`로 별도 로컬 API(8016)·분리 저장소에서 기존 두 입력을 그대로 재실행했다. 사용자 서버의 작업·소유권에 테스트 기록을 이관하지 않았다. bbox `[128.28865,36.07461,128.39985,36.16453]`, UTC 2026-07-01~31, 불확실성 상한 2K·구름 최소 거리 1km를 유지했다. 기존 입력과 정확한 일치도 검증했다.

| 실제 촬영일 | 검사 AOI·공통 관측 면적 | 기본 QA·필수 자료 제외 | 기본 QA 통과 영역의 불확실성 검사 제외 | 추가 구름 거리 검사 제외 | 최종 유효 면적 |
|---|---:|---:|---:|---:|---:|
| Landsat 8 / 2026-07-11 | 99.8865 km² | 13.1195 km² | 86.7670 km² | 38.3998 km² | 0 km² |
| Landsat 9 / 2026-07-12 | 99.8865 km² | 57.7680 km² | 42.1185 km² | 36.4634 km² | 0 km² |

불확실성 검사는 상한 초과·결측/비정상을 포함한다. 구름 거리와 불확실성 제외는 겹치므로 합계가 아니다. 두 장면 모두 기본 QA를 통과한 나머지 영역이 불확실성 검사에서 제외됐다. 0 km²는 확인된 유효 면적이며 지표면 온도 0℃라는 뜻이 아니다. 두 작업의 분석 결과는 null, artifact 없음이며 실제 성공 ZIP은 없다. 근거는 `live-gumi-1.json`, `live-gumi-2.json`, `live.log`, `verify_live.py`다. 나머지 검색 6장면이나 구미시 전체·물리적 참값·월평균은 검증하지 않았다.

## 이번 검증과 서비스 반영

| 검사 | 결과 | 근거 |
|---|---|---|
| `pytest backend/tests/test_processing_failure_details.py backend/tests/test_product_engines.py backend/tests/test_processing_records.py backend/tests/test_media_access.py -q --disable-warnings` | 109 passed, 경고 989건, 26.63초 | `backend.log`, `backend-exit.txt` |
| `playwright test tests/product-engines.spec.ts --workers=1` | 14 passed, 2.9분; 명시 fixture | `e2e.log`, `browser/`, `fixtures/` |
| TypeScript noEmit / 격리 소스 production build | 각각 exit 0 | `typecheck.log`, `build.log`, 각 exit 파일 |
| 실제 두 장면 QA·오류 전송·결과 null·입력 불변 | 통과, 예상된 QA 보류 2건 | `live.log`, `live-exit.txt`, `live-gumi-*.json` |
| 390px / 1440px 보류 화면 | 화면 확인, 가로 넘침 없음 | `browser/*/qa-reasons.png` |
| 반영 후 처리 화면·프런트/백엔드 health | HTTP 200 | `final-health.json` |

회귀는 무효 QA 사유별 실제 TIFF fixture, worker→부모→서명 journal 진단 보존, 타 소유자 접근 차단, 일반 부분 실패의 QA 미확인, quota 시 worker 미시작·예약 불변·재시도 시각, 대기 후 자동 실행 없음, 대체 장면 선택 후 bbox/날짜/QA 불변, 과거 실패 수치 미조작을 포함한다. 이전 전체 테스트 수를 이번 실행으로 합산하지 않았다.

검증 API는 종료했다. 기본 서비스는 수정 코드로 재시작해 3000/8000에서 실행 중이다(`main-pid.txt`, `logs/20261105-questions-restart-*.log`). 메모리 전송 예약 집계는 이 재시작으로 초기화되며, 이를 시간 경과에 따른 복구로 주장하지 않는다. 기존 실패 기록에는 상세 QA를 소급 생성하지 않는다. 새 실제 검사부터 진단을 저장한다. 유료 AI·인증 원본·공개 배포·다중 이용자 부하 시험은 미실행이다.

---

# 사용자 자연어 입력 이후 구미 실제 흐름 — 2026-11-05

사용자가 직접 입력한 `2026년 7월 구미시의 지표면 온도를 알고싶어.`의 해석 완료 화면을 기존 VS Code 내장 브라우저에서 이어받았다. 새 자연어 입력/AI 재시도는 실행하지 않았다. 사용자가 추가로 승인한 **구미시 중심부 약 10×10km**만 시험했다. 근거: `test-results/gumi-journey-20261105/`.

## 실제 화면·제공처 결과

- 지명 후보 `경북 구미시`를 선택해 지도 중심만 이동했다. 별도 확정 bbox는 `[128.28865,36.07461,128.39985,36.16453]`, 기간은 UTC `2026-07-01~31`이다. 행정경계 전체나 월평균 결과가 아니다.
- `planetary-computer / pc-landsat-c2-l2 / L2SP`로 실제 검색 **8건**을 받았다. 촬영 범위의 기하 중첩과 실제 픽셀 품질을 구분했고, 온도 분석 진입 시 ST_QA/CDIST를 포함한 필수 5개 Asset이 선택됐다.
- 최초 7월 11일 작업 `84cdca49a8884fcea90473aae63b4dc9`은 이전 개발 테스트가 사용한 공용 **512MiB/시간 예약 예산** 때문에 원본 픽셀 읽기 전에 거절됐다. 실패 결과/유효율은 null, artifact 없음으로 유지됐다. 실제 사용 바이트가 아니라 최대 입력 예산의 예약 방식임을 구분한다.
- 코드 반영을 위해 로컬 launcher를 재시작했다. **메모리 사용량 집계는 이 재시작으로 초기화됐다.** 이를 시간 경과에 따른 한도 복구나 한도 오류 수정만의 효과로 표현하지 않는다. 한도 512MiB, 작업별 최대 256MiB, 실제 실행 실패의 예약 유지 정책은 변경하지 않았다. 기존 사용자 조건·선택·실패 기록이 복원됐으며 자동 검색/AI/처리 실행은 없었다.
- 같은 bbox·기간·운영 QA 기준(불확실성 상한 2K, 구름 최소 거리 1km)으로 9타일·334×334 계획 후 실제 처리했다. `LC08_L2SP_115035_20260711_02_T1` 작업 `c7d9d443d05c4a518fb66c4e102d9751`, 대체 `LC09_L2SP_114035_20260712_02_T1` 작업 `290c3c799e2b4588bc0807898190e8e3` **모두 관측은 있으나 QA/수치 조건을 통과한 공통 유효 픽셀 없음으로 실패/분석 보류**했다.
- 두 장면의 전체 장면 구름량은 각각 16.65%, 36.11%였지만 이를 AOI 품질로 사용하지 않았다. 평균을 0으로 채우거나 ZIP/성공 지도를 생성하지 않았다. 장면 전환 시 이전 실패는 ‘이전 조건의 작업’으로 표시됐다. 나머지 6장면은 실제 QA 미검사다. 이번 구미 흐름에서는 다운로드할 성공 산출물이 없어 ZIP 수신·재열기를 완료했다고 주장하지 않는다. 아래 이전 공개 표본 다운로드 검증과 분리한다.

## 발견한 오류와 수정

1. `processing.py`가 개인 예산을 먼저 차감한 뒤 공용 한도를 검사해, 공용 거절만으로 개인 예산도 소진됐다. `media_access.charge_many()`에서 같은 lock 안에 모든 한도를 검사하고 함께 차감하도록 수정했다. 처리 시작과 처리 결과 다운로드에 적용했다. 이미 허용된 실행의 실패 예산을 돌려주거나 상한을 올리지 않았다. 공용 한도 거절 시 어느 예산도 바뀌지 않음, 두 동시 요청 중 한도 내 한 건만 허용됨을 회귀 검사했다.
2. 서버 추천에 명시 purpose_type을 전달하는 기존 계약 때문에 AI 자동 설정도 화면에 `사용자 직접 선택`으로 표시됐다. `WorkflowWorkspace`가 보존된 폼 출처를 사용해 `AI 해석으로 설정`과 `사용자 직접 선택`을 구분하도록 수정했다. AI 설정 뒤 수동 목적 변경을 브라우저 fixture로 확인했고, 실제 복원 화면에서도 AI 출처를 확인했다.

## 이번 추가 검증

| 실행 | 결과 | 근거 |
|---|---|---|
| `pytest backend/tests/test_media_access.py backend/tests/test_processing_records.py backend/tests/test_processing_foundation.py -q --disable-warnings` | **69 passed**, 경고 802건, 236.95초 | `backend-check.log` |
| `ai-conditions.spec.ts --workers=1` | **10 passed**, 2.0분. AI 응답은 명시 fixture이며 유료 AI 실호출 검증 아님 | `ai-fixtures.log`, `browser/` |
| TypeScript `--noEmit` | 통과 | `typecheck.log` |
| 별도 최신 소스 복사본 `next build --webpack` | production build exit 0 | `build.log`, `build-exit.txt`, `staged-frontend/` |
| 실제 기존 사용자 UI → 공개 원본 QA | 8건 검색, 2개 촬영일 실제 QA 보류, 허위 결과/파일 없음 | `scenario.json`, `actual-jobs.json` |
| 최종 `/processing`, frontend `/api/health`, backend `/health` | 모두 HTTP 200, 3000/8000 계속 실행 | `final-health.json` |

`actual-jobs.json`은 실제 서버 journal의 작업·입력·오류·진행 기록에서 소유권/서명 정보를 제외한 사본이다. 오프라인 검사로 세 작업 모두 동일 bbox·기간, artifact 없음, 유효율 null, 해당 작업의 ZIP 없음까지 확인했다. `server-jobs-before-restart.json`은 앞선 사용량의 작업 이력이며, `changes.diff`·`changed-source-hashes.json`·`backup/`에 수정 근거가 있다. 재시작 전 전체 로그의 `/request/interpret` 횟수는 이전 작업을 포함하는 API 요청 횟수로, OpenAI 유료 호출 횟수가 아니다. 재시작 후 해당 API 요청은 0건이다.

이번 추가 작업은 위 구미 표본과 관련 회귀에 한정된다. 앞선 641개 전체 backend/전체 브라우저 실행을 이번 새 실행으로 합산하지 않았다. QA 기준 완화, 나머지 촬영일 품질, 물리적 참값, 동시 다중 이용자 운영 부하, 실제 인증 원본, 구미 성공 ZIP 다운로드는 검증하지 않았다.

---

# 실제 이용자 흐름 검증·수정 — 2026-11-05

처음 방문한 브라우저의 조건 입력 → 제품 추천 → 검색 → 지도/촬영일/장면 선택 → 세부 분석 → 계획 확인 → 실행 → ZIP 저장 → 새로고침·보관함 재다운로드를 점검했다. 입력 오류, 늦은 응답, 실패 후 재시도, 모바일, 다른 브라우저의 접근도 구분했다. 근거는 `test-results/user-journey-20261105/`에 있다. 아래 과거 실행 수를 이번 결과로 재사용하지 않았다.

## 재현한 문제와 수정

| 문제 | 근거 | 수정·재검증 |
|---|---|---|
| 보관함 목록을 본 뒤 파일이 만료되면 화면 안에 오류·복구 안내가 없음 | `archive-before.log`의 HTTP 410 재현 실패 | 직접 링크를 제한된 수신 흐름으로 바꿨다. 만료/누락·세션 만료 안내 후 보관함 재조회와 재시도를 제공한다. |
| 보관함 다운로드는 분석 직후 다운로드와 달리 크기·해시를 확인하지 않음 | 동일 길이지만 내용이 다른 ZIP fixture에서 SHA-256 오류 안내가 없음 | 16 MiB 상한, MIME, 전체 크기, SHA-256을 확인한 뒤 저장한다. 실패한 응답·손상된 바이트는 저장하지 않으며 중복 수신을 막는다. |
| 잘못된 보관함 응답(`jobs:null`)으로 페이지가 깨짐 | 수정 전 세 번째 회귀 실패 | 응답 구조 검사와 재조회 가능한 오류 안내를 추가했다. 수정 후 3개 오류/복구 테스트 통과. |
| 실제 결과의 면적·유효율이 좁은 열에서 글자 단위로 꺾임 | `live-delivery/vegetation_index/panel.png` 수정 전 화면 | 공통 `dl div`의 가로 배치 영향을 해당 결과 카드 안에서 해제했다. 390/1440px 레이블·수치 위치 검사와 수정 후 실제 결과 화면을 확인했다. |

앱 변경은 `frontend/src/components/ResultArchive.tsx`, `frontend/src/app/globals.css`다. 백엔드 과학 계산·설정·자격증명은 변경하지 않았다. `result-archive.spec.ts`를 추가하고 `processing-foundation.spec.ts`의 결과 레이아웃 회귀를 보강했다.

## 이번 실행 결과

| 실행 | 결과·종료 코드 | 근거 |
|---|---|---|
| backend: `python -m pytest -q --disable-warnings`, LIVE=0 | **641 passed / 28 skipped**, exit 0. 경고 3389건 포함 | `pytest-baseline.log` |
| 루트: `node frontend/node_modules/typescript/bin/tsc --noEmit -p frontend/tsconfig.json` | 통과, exit 0 | `typecheck-final.log` |
| 최신 앱 소스의 별도 복사본: `node node_modules/next/dist/bin/next build --webpack` | production build 통과, exit 0 | `build-final.log`, `staged-frontend/` |
| 빌드 앱 3015: `node node_modules/@playwright/test/cli.js test --workers=2`, LIVE=0 | 247개 중 **214 passed / 32 skipped / 1 failed**, exit 1. 아래 테스트 경합 수정 후 해당 파일 8개 모두 통과 | `e2e-final.log`, `selection-recheck.log` |
| `tests/analysis-selection.spec.ts --workers=1` 재검증 | **8 passed**, exit 0. 위 실패 1건 포함 | `selection-recheck.log` |
| 보관함+지명/모바일 관련 `result-archive.spec.ts research-workflow.spec.ts --workers=1` | **15 passed**, exit 0. 전체 실행에도 포함되므로 통과 수에 중복 합산하지 않음 | `archive-after.log` |
| 실제 공개 데이터: `analysis-delivery-live.spec.ts --workers=1`, LIVE_STAC=1/LIVE_PROCESSING=1 | 최초 **8 passed / 1 failed**, exit 1. 도시지수의 전체 테스트 시간 초과; 아래 재검증에서 실제 저장까지 통과 | `e2e-live.log` |
| 실제 공개 데이터 재검증: 위 파일 `--grep 'vegetation_index\|urban_index'` | **2 passed**, exit 0. 식생의 보관함 재수신·다른 브라우저 404도 추가 확인 | `e2e-live-final.log`, `live-final/` |

브라우저 전체 실행에서 유일하게 남았던 실패는 `analysis-selection.spec.ts`가 검색 클릭 직후 아직 도착하지 않은 `requests[0]`을 읽던 테스트 경합이다. 요청 수를 기다린 뒤 검사하도록 수정했고 같은 파일 8개가 모두 통과했다. 전체 실행과 재검증을 합친 **고유 215개 일반 브라우저 사례에 통과 근거**가 있으며, 32개 LIVE/선택 실행은 생략했다. 전체 실행 자체를 exit 0이라고 표현하지 않는다. 실제 AI 조건 성공·실패 fixture는 OpenAI 실응답 검증이 아니다.

처음 dev 서버에서 실행한 전체 테스트는 수정 중 Fast Refresh/컴파일 영향을 받아 중단했다(`baseline-interruption.txt`, `e2e-baseline.log`). 이 실행은 전체 통과 수로 세지 않았다. 첫 `npx` 실행도 PowerShell 실행 정책으로 시작되지 않아 설치된 Node CLI로 실행했다. 시스템 실행 정책은 바꾸지 않았다.

도시지수 최초 LIVE 테스트는 총 180초 제한에 걸렸지만 서버의 해당 작업은 `00:30:52Z` 생성 → `00:31:04Z` 성공이었다. 성공을 테스트 통과로 간주하지 않고 재실행했다. 테스트 총 시간을 420초로, 처리 대기는 서버 계획의 `maximum_seconds`+30초(최대 300초)로 맞췄다. 실제 처리 제한이나 실패 조건을 완화하지 않았다. 재검증은 새 테스트 전용 API/보관소(8015)와 빌드 UI(3015), 명시적인 로컬 API 전달로 수행했다.

## 실제 공개 데이터·파일 근거

| 흐름 | 실제 표본·검증 |
|---|---|
| 식생지수, 수역 후보, 도시지수 | Earth Search S2 `S2B_52SBF_20210716_0_L2A`, bbox `[126.7,36.4,126.71,36.41]`, 2021-07-01~31 |
| 식생 변화, 수역 변화 | 위 장면과 `S2B_52SBF_20210726_0_L2A`, 같은 bbox/기간 |
| 지표면 온도, 고온 영역, 두 영역 온도 비교 | 공개 PC Landsat `LC08_L2SP_039035_20250719_02_T1`, bbox `[-115.15,36.16,-115.14,36.17]`, 2025-07-01~31 |
| 큰 도시 AOI 제한 | 서울 포함 bbox의 실제 검색은 유지하고 처리 계획은 422로 거절, 작업 시작 0건 |
| 재방문·소유권 | 새로고침 후 보관함 ZIP이 첫 다운로드와 바이트 단위 동일. 브라우저 SHA-256 확인. 검색 1회·작업 시작 1회 유지. 소유 브라우저 작업 조회 200, 별도 브라우저 다운로드 404 |

8개 분석 각각 실제 검색 → canonical 자료 → 공개 원본 범위 읽기/QA → 계산 → 브라우저 ZIP 저장 → Rasterio 재열기·CRS/격자/NoData/단위/해시/수치 검사를 통과했다. `live-delivery/*/run.json`·`rasterio.json` 및 재검증 `live-final/live-delivery/*/`에 있다. 브라우저가 저장한 ZIP 8종과 같은 식생 ZIP 재다운로드는 `deliverables/`, 파일 크기·SHA-256은 `deliverables.json`에 보관했다. 서명 URL·자격증명은 기록하지 않았다.

수정 전·후 실제 결과 화면은 `live-delivery/vegetation_index/panel.png`와 `live-final/live-delivery/vegetation_index/panel.png`, 보관함은 `retained-archive.png`, 모바일/데스크톱 fixture 화면은 `screenshots/metrics-390.png`·`metrics-1440.png`다. 스크린샷을 직접 확인했다. 전용 브라우저 제어 호스트가 제공되지 않아 이번 화면 검증은 프로젝트 Playwright의 독립 Edge 브라우저를 사용했다.

## 범위와 남은 검증

이 결과는 로컬 앱의 방문자 흐름과 위 공개 표본에 한정된다. 유료 OpenAI 실호출은 별도 승인이 없어 0회, NASA/USGS/CDSE 인증 원본 재검증·모든 제품/지역/날짜·동시 다중 이용자 부하·인터넷 공개 배포·QGIS/ArcGIS GUI는 이번에 수행하지 않았다. 실제 파일 수치 검사는 물리적 참값·침수 확정·도시 분류 정확도 검증이 아니다. 원관측·ML 추정 구분과 기존 QA 제한을 유지했다.

기존 앱 `http://127.0.0.1:3000/`와 backend 8000은 health HTTP 200을 확인했다(`production-health.json`). 변경 파일 해시는 `changed-code-files.json`, 실행 시각은 `run-times.json`, 수정 전 파일은 `backup/`에 보관한다.

---

# 운영자 제공처 실접근 재검증 — 2026-11-04 15:16 KST

이번 결과는 아래 이전 기록과 분리한다. 로컬 사이트의 공개 표본 Item만 사용했고, 계정 값·토큰·서명 URL은 결과 파일에 저장하지 않았다.

| 제공처 | 이번 실제 결과 |
|---|---|
| NASA Earthdata | HLS L30 `G3625879681-LPCLOUD`의 B04 범위 검사 HTTP 206, 전체 다운로드 HTTP 200·22,174,417 bytes. TIFF SHA-256 `35692d326d248ad6bb365ff2ccc5f890544fc40c42a1bf6193cdd2603379220d`. rasterio 재열기: GTiff, 3,660×3,660, EPSG:32652, int16, NoData -9999, 작은 픽셀 범위 읽기 성공. 한 파일의 성공이며 모든 NASA 제품·브라우저 저장 검증은 아니다. |
| USGS | Landsat `LC08_L2SP_039035_20250719_02_T1` red 검사 응답은 앱 HTTP 200이지만 Asset `operator_permission_denied`, `access_verified=false`. MACHINE 권한 승인/원본 다운로드는 확인되지 않았다. |
| CDSE | Sentinel-1 `S1A_IW_GRDH_1SDV_20250817T093217_20250817T093243_060574_0788C1_8F3F_COG` Product 검사 응답은 앱 HTTP 200이지만 Asset `operator_reconnection_required`, `access_verified=false`. Marine 웹 로그인 완료와 서버 OData API 인증은 별개이며 전체 파일은 받지 않았다. |

- 실행: `pwsh -NoProfile -File test-results/auth-live-verification-20261104.ps1` 종료 0(세 제공처 결과를 개별 상태로 출력); `pwsh -NoProfile -File test-results/nasa-full-download-20261104.ps1` 종료 0; `backend`에서 `..\.venv\Scripts\python.exe -c ...`로 위 TIFF를 rasterio 재열기, 종료 0. 결과 파일은 `test-results/nasa-hls-b04-20261104.tif`이다. 다운로드 완료와 브라우저의 파일 저장은 구분한다.
- **토큰 교체 필요:** 이번 점검에서 `.env` 한 줄을 가리는 진단 필터가 공백 있는 대입 구문을 놓쳐 NASA User Token이 도구 출력에 노출됐다. 값은 이 문서에 넣지 않았다. Earthdata에서 해당 토큰을 폐기하고 새 토큰을 서버 설정에 반영해야 한다. 새 토큰은 아직 검증하지 않았다.
- 이번 검증은 pytest·typecheck·build·E2E를 다시 실행한 것이 아니다. 아래 실행 결과는 해당 시점의 이력이다.

---

# 운영자 제공처 인증·실접근 점검 — 2026-11-04 추가 기록

이 기록은 아래 연구 작업 흐름 검증 이후의 **별도 변경과 실행**이다. 이전 전체 pytest/build/E2E 결과를 이번 운영자 인증 코드의 통과 근거로 재사용하지 않는다. 비밀값은 기록하지 않았다.

| 항목 | 이번에 확인한 상태 |
|---|---|
| NASA Earthdata | `backend/.env`의 운영자 User Token이 실제로 설정돼 있음을 확인했다. 기존 HLS L30 B04의 제한적 HTTP Range 응답은 206이었다. 이는 전체 원본 저장·재열기 검증이 아니다. 저장된 동일 revision의 암호화 grant를 명시 설정으로 재개하는 경로를 추가했으나 현재는 env token이 있으므로 그 fallback은 사용하지 않는다. |
| USGS | ERS Application Token으로 공식 M2M `login-token`과 `scene-metadata`의 정확한 Landsat 8 L2SP 제품 대응을 실확인했다. 같은 계정의 `download-options`는 HTTP 403을 반환했다. 사용자가 ERS의 MACHINE 역할을 신청했고 공식 신청 내역에 **Pending**이 표시됐다(ERS 화면 날짜 Nov-03-2026). 승인 전 원본 파일 다운로드 성공으로 표기하지 않는다. |
| CDSE | 운영자가 `backend/.env`를 갱신하고 revision 3으로 저장한 뒤 백엔드를 재시작했다. 실제 Sentinel-1 Product의 `/api/media/inspect`는 HTTP 200으로 응답했으나 Asset 상태는 **`operator_reconnection_required`, `access_verified=false`**였고 서버 grant도 revision 3의 `reconnection_required`였다. 인증 단계 실패이므로 원본 파일에는 도달하지 않았다. 사용자는 CDSE에 **Copernicus Marine 연동 로그인**을 사용한다고 밝혔다. 앱의 현재 `cdse-public` 직접 password grant는 이 외부 IdP의 웹 로그인과 다른 경로다. 공식 CDSE 뉴스는 웹 로그인 권한 상호 인정을 설명하지만 Marine 자격으로 OData password grant를 허용한다고 명시하지 않는다. 기기 인증은 `cdse-public` 시험에서 HTTP 400 `unauthorized_client`였다. 별도 공식 API 인증 경로가 확인될 때까지 재시도하지 않는다. |

USGS `scene-metadata`는 단수 `entityId`와 `idType=displayId`를 쓰고 반환된 정확한 displayId/entityId를 확인하도록 수정했다. 403/401 등 비 JSON 오류는 `operator_invalid_response`로 뭉개지 않고 상태별로 분류한다. 변경 파일은 `backend/app/operator_adapters.py`, `operator_access.py`, `operator_store.py`, `backend/tests/test_operator_access.py`, `scripts/server-env.mjs`, `scripts/server-env.test.mjs`와 이 보고서 및 `docs/OPERATOR_DATA_ACCESS.md`다. 로컬 `backend/.env`는 비공개 설정 파일이며 비밀값을 문서에 복사하지 않았다.

| 실행 위치·명령 | 종료 코드 | 최신 실행 결과 |
|---|---:|---|
| `backend`: `..\.venv\Scripts\python.exe -m pytest tests/test_operator_access.py tests/test_earthdata_auth.py tests/test_media_access.py -q --basetemp=..\test-results\auth-provider-mapping-20261104` | 0 | 63 passed, Starlette 경고 1개 |
| 루트: `node --test scripts/server-env.test.mjs` | 0 | 19 passed |

사용자 제출 후 ERS 신청 내역의 MACHINE 상태 **Pending**을 직접 확인했다. 개인정보를 제외한 화면은 `test-results/usgs-machine-pending-20261104.png`에 있다. 최신 백엔드를 재시작한 다음 실제 공개 Earth Search Item `LC08_L2SP_039035_20250719_02_T1`의 `red` Asset을 `/api/media/inspect`로 1회 조회했다. 프런트/세션/검사 HTTP는 각각 200/200/200이지만 Asset 상태는 `operator_permission_denied`, `access_verified=false`였다. 이는 신청 접수와 제품 파일 접근 승인을 구별하는 결과다. 전체 파일 수신은 실행하지 않았다.

CDSE 사용자는 Copernicus Marine 계정으로 연동 로그인을 선택했다. CDSE 웹사이트의 현재 화면은 **새 계정 생성 성공 후 이메일 인증 필요**이며 `test-results/cdse-email-verification-20261104.png`에 기록했다. 이 화면은 API 토큰 발급 성공이나 CDSE 계정 활성화의 증거가 아니다. 공식 [연동 로그인 공지](https://dataspace.copernicus.eu/news/2026-10-12-copernicus-data-space-ecosystem-and-copernicus-marine-service-logins-mutually)는 웹 서비스 권한 상호 인정을 명시한다. [OData 토큰 안내](https://documentation.dataspace.copernicus.eu/APIs/OData.html)는 직접 CDSE 사용자명·비밀번호 password grant와 refresh grant를 문서화하며 Marine SSO 비밀번호의 직접 grant는 설명하지 않는다. 따라서 이메일 확인 및 공식 API 경로를 검증하기 전까지 인증 가능성을 확정하지 않는다.

제한된 샌드박스의 첫 Node 테스트는 임시 파일 rename `EPERM`으로 종료 1이었다. 같은 소스의 허용된 로컬 실행에서 위 19건이 통과했다. 이번 변경 뒤 **전체 pytest·독립 typecheck·production build·전체 E2E·CDSE/USGS 원본 파일 전체 수신 및 GIS 재열기는 미실행**이다. 인증·제품 접근 오류를 실제 파일 검증과 혼동하지 않는다.

---

# 연구 작업 흐름 통합 개선 — 2026-11-04 이전 검증

이번 작업은 기존 앱·단일 Workspace·기존 과학 엔진을 재사용했다. 사용자 설정/비밀값/인증 정책/패키지를 변경하지 않았다. 과거 200건 E2E·621건 pytest·28건 LIVE 통과는 이번 새 코드의 증거로 재사용하지 않는다. 지원 범위 내 개선과 아래 실표본만 완료이며 **사이트 전체/도시 전체/모든 제품 완료가 아니다**.

## 구현과 확인된 원인

- 기존 서버는 Kakao ready=true였으나 수원은 HTTP200/no_results였다. 별도 실제 exact 조회도 REGION `경기 수원시`를 반환했고, **기존 필터 false / 수정 계층 필터 true**가 확인됐다. 키 오류/서버 실패가 아니라 `수원`과 `수원시`의 문자열 비교가 원인이었다. similar 후보 확장과 모든 요청 행정 구성요소의 순서 검증을 적용했다. 서울 강서구/부산 강서구·수원 영통구 매탄동의 부모만 반환되는 경우를 구분한다.
- AI 목적/UTC 날짜·지명 원문 추출을 유지하며 유료 AI 대신 mock으로 검증했다. 후보는 항상 사용자 선택 후 **카메라만** 이동한다. AOI/행정경계를 자동 생성·확정하지 않는다. 기존 수동 날짜/AOI, IME·취소·중복/늦은 응답 보호, 직접 지도/좌표 경로를 유지했다.
- 조건 확정 → 영상 선택 → 분석 준비·실행 → 결과 검토·저장을 표시했다. 기존 추천/검색/날짜·지도/비교/밴드·원본 흐름을 유지하고, 서버 카탈로그의 필수 밴드 초기값/명시 복원·서버 원본 입력 설명·개별 추천/접근/QA/성공/전달 상태·파일명/크기/만료/재시도를 연결했다.
- 단일 시점 allowlist 제품만 고정 core/halo 타일 처리한다. **최대200km²/600,000셀/36타일**, 타일별 원본100만셀/64MiB/128요청/60초, 전체256MiB/512요청/240초 범위 읽기/255초 프로세스/ZIP16MiB. 같은 격자에서 core가 겹치지 않으며 빈 타일은 미관측, 실패 타일은 전체 실패/게시 안 함이다. 기존 QA·NDVI 변화·MNDWI 변화50km², 합성/ML25km²는 유지한다. 숫자만 올린 전체 window 읽기가 아니다.
- 새 성공 작업은 비공개 실제 파일＋서명 journal/지속 소유권 키로 보관한다. 기본7일/1GiB, owner20개/전체100개, 메타데이터2MB, 단일 worker lease. 재시작 중 작업은 실패로 남고 자동 재실행하지 않는다. 기존 메모리 작업을 소유권 증거 없이 이관하지 않는다. 쿠키/키/파일 소실·만료, 디스크/메타데이터 한도·변조를 구분한다.

## 이번 실제 실행

| 검증 | 실제 명령 | 실행 시각(KST, +09:00) | 종료 코드 | 결과 |
|---|---|---|---|---|
| 전체 backend | `python -m pytest -q --disable-warnings` | 2026-11-04T10:45:10.9526109+09:00 ~ 2026-11-04T10:48:26.2437979+09:00 | 0 | 638 passed /28 LIVE skipped |
| 독립 TypeScript | `npm run typecheck` | 2026-11-04T10:59:45.5525011+09:00 ~ 2026-11-04T10:59:48.3118269+09:00 | 0 | 통과 |
| production build | `npm run build (isolated source copy, latest src/tests)` | 2026-11-04T10:59:37.2938057+09:00 ~ 2026-11-04T10:59:47.5580457+09:00 | 0 | 통과, 최신 source/tests 격리 복사본 |
| 전체 Playwright | `npx playwright test --workers=2 --shard=N/4 (N=1..4 sequential)` | 2026-11-04T10:53:32.6452817+09:00 ~ 2026-11-04T10:58:50.9364740+09:00 | 0,0,0,0 | 212 passed /32 skipped /0 failed; 244 unique cases |
| 새 UI 회귀 | `npx playwright test tests/research-workflow.spec.ts --workers=2 --timeout=30000` | 2026-11-04T10:41:59.8118740+09:00 ~ 2026-11-04T10:42:17.4817840+09:00 | 0 | 12 passed, 390/768/1440px |
| 기존 입력/복원 회귀 | `npx playwright test automatic-conditions ai-camera ai-conditions processing-foundation --workers=2` | 2026-11-04T10:38:07.8872036+09:00 ~ 2026-11-04T10:38:43.4396514+09:00 | 0 | 23 passed |
| 실제 소형 NDVI E2E | `LIVE_STAC=1 LIVE_PROCESSING=1 npx playwright test tests/analysis-delivery-live.spec.ts --workers=1 --grep vegetation_index` | 2026-11-04T10:46:50.5743621+09:00 ~ 2026-11-04T10:47:34.6554616+09:00 | 0 | 1 passed |
| 실제 도시 상한 E2E | `LIVE_STAC=1 LIVE_PROCESSING=1 npx playwright test tests/analysis-delivery-live.spec.ts --workers=1 --grep city` | 2026-11-04T10:54:01.0214380+09:00 ~ 2026-11-04T10:54:12.7347302+09:00 | 0 | 1 passed |
| 실제 대형/재시작 | `LIVE_STAC=1 LIVE_PROCESSING=1 python backend/tests/live_research_delivery.py evidence http://127.0.0.1:3012/api` | 2026-11-04T10:48:55.3293347+09:00 ~ 2026-11-04T10:53:31.3085813+09:00 | 0 | 공개 검색/9타일/ZIP/Rasterio/재시작 동일 소유권·해시/다른 세션404 |
| QGIS | `QGIS 4.2.2/bin/python-qgis.bat backend/tests/check_qgis_delivery.py evidence` | 2026-11-04T10:52:32.0616848+09:00 ~ 2026-11-04T10:52:39.4910835+09:00 | 0 | 실제 2 ZIP/6 TIFF, headless 읽기·렌더 |
| 현재 사이트 실제 Kakao 브라우저 | `node evidence/production-browser-kakao.mjs` | 2026-11-04T11:01:38.5037822+09:00 ~ 2026-11-04T11:01:45.2580870+09:00 | 0 | HTTP200 후보 선택/카메라 이동/기존 AOI 보존; AI0/검색0 |

모든 기본 pytest는 backend cwd, LIVE_STAC=0/LIVE_PROCESSING=0에서 실행했다. 전체 E2E는 LIVE_STAC=0/LIVE_PROCESSING=0, E2E_BASE_URL=http://127.0.0.1:3012/E2E_API_BASE=http://127.0.0.1:8012에서4 shard를 순차 실행했다. 기본32 skip은 외부 LIVE19개와 구형 대용량 원본/수동 승인 경로13개이며 통과로 세지 않았다. **전체 backend LIVE28 전수는 이번에 미실행**이다. 대신 위 선택된 공개 실제 E2E/대형 파일/현재 Kakao 실조회를 별도로 실행했다. fixture는 테스트 안에서만 사용하며 서비스 오류에 가짜 데이터를 반환하지 않는다.

`e2e-case-coverage.json`은 244개 선언의 shard 중복/누락 없음을 확인한다. 이전 polygon roi undefined는 현재 코드에서 재현되지 않았다. 요청 수신 대기 poll이 있는 현재 테스트는 관련 단독 실행과 이번 마지막 전체 shard3에서 통과했다. 이를 이전 실패가 앱의 현재 결함이었다는 근거로 사용하지 않는다.

## 실제 파일과 재현

제품 Earth Search Sentinel-2 L2A / Item `S2B_52SBF_20210716_0_L2A` / UTC2021-07-01~31 / 식생 한 시점 NDVI / red,nir,SCL.

| 사례 | AOI·전체 처리 | 실제 전달·검사 |
|---|---|---|
| 작은 AOI | bbox[126.7,36.4,126.71,36.41],20m·46×56셀 | 실제 브라우저 검색/장면 선택/QA·계산/지도/ZIP13,991bytes `saveAs`; 파일 전체 SHA/ZIP CRC/GeoTIFF·마스크·manifest CRS/transform/NoData/단위/수치 재열기 |
| 큰 AOI | bbox[126.7,36.4,126.8,36.48],79,594,684.36m²·450×444·9타일 | 실제 검색28건 중 동일 Item, ZIP326,038bytes 전체 수신·동일 Rasterio 검증; 서버 재시작 후 같은 클라이언트 쿠키로 GET/전체 다운로드 동일 SHA, 보관함 복원·다른 세션404 |
| 도시 상한 | 서울 포함 bbox[126.76,37.42,127.18,37.70],UTC2025-08-15~30 | 실제 검색 후 처리 계획422/200km² 초과·시작0건·입력 bbox 불변. 행정경계 통계가 아님 |

재현 UI: 수집에서 위 분야/UTC 기간/수동 bbox → Earth Search S2 제품 선택/명시 검색 → 날짜/Item → 세부 분석 선택으로 → 식생지수 확인 → 필수 밴드/QA 확인 → 계획 규모/정책 확인 → 체크/실행 → 실제 결과/한계 → 검증된 처리 ZIP 다운로드 → GIS 재열기. 큰 결과의 **브라우저 저장**은 별도로 수행했다고 주장하지 않는다(API 전체 수신/재열기 검증). 작은 결과는 실제 브라우저 저장을 검증했다.

QGIS4.2.2의 독립 headless profile에서 두 ZIP의 TIFF6개를 GDAL provider로 전부 읽고 과학 TIFF를 렌더했다. QGIS/ArcGIS 데스크톱 GUI는 미실행이다. 대형 S2 NDVI와 Landsat ST의 실제 고정 TIFF에서는 단일 처리/타일 core 값·마스크·격자가 일치하고 구름/NoData·실패 타일/미관측·중복 면적·저장 해시를 검사했다. 실제 물리적 참값/분류 정확도를 검증한 것이 아니다.

증거: `test-results/research-workflow-20261104-101418/`. `deliverables/ndvi-small.zip`, `deliverables/ndvi-large.zip`, `deliverables.json` 전체 SHA; `live-delivery/vegetation_index/rasterio.json`, `live-large/result.json`, `live-large/rasterio.json`, `qgis/result.json`, viewport PNG, `production-browser-kakao.json`, `production-health.json`, `kakao-exact-filter-diagnosis.json`.

## 보관/설정/현재 사이트

- 현재 사이트 http://127.0.0.1:3000/ · backend http://127.0.0.1:8000. 사용자 작업 부재/재시작 승인 후 경로·부모 프로세스를 확인한 기존 프로젝트 런처만 종료하고 `.\start.cmd`로 재시작했다. 다른 서버는 종료하지 않았다. 격리3012/8012는 검증 후 종료했다.
- 반영 뒤 웹/health/프런트 health/analysis catalog200, NDVI 한도200km², Kakao ready=true/누락없음. 실제 현재 사이트의 수원 후보1개·카메라 이동·기존 수동 bbox 불변을390px 브라우저에서 검증했다. 목적/날짜는 직접 입력했고, 문장 전체 실제 유료 AI는 호출0이다. 실제 OpenAI 모델 응답 성공을 주장하지 않는다.
- `PROCESSING_RETENTION_SECONDS`(기본604800,60~2592000), `PROCESSING_STORAGE_MIB`(기본1024,64~8192), `PROCESSING_WORKERS=1`은 시작 프로세스 환경변수다. backend/.env loader allowlist를 이번에 바꾸지 않아 이 새 설정은 PowerShell `$env:`로 넣어 시작한다. 기존 `.env`/키/모델/인증/이용조건 플래그는 변경하지 않았다.
- HttpOnly/SameSite=Strict·최대7일 소유권 쿠키와 비공개 로컬 키, HMAC journal·ZIP 전체 SHA, 다른 세션404를 유지한다. 만료 정리는 전용 UUID 폴더만 요청 시 수행하며 사용자 파일을 정리하지 않는다. 7일 넘는 파일 보관을 설정해도 쿠키는7일이므로 먼저 ZIP을 저장해야 한다. 다중 worker/서버/계정 공유 보관·재시작 간 전송 쿼터 합산은 미구현이다. 기존 프로세스 단위 전송 쿼터와 파일 저장 상한은 유지한다.


## 변경한 실제 파일

수정 전 대상 원본은 증거 `backup/`, 경로·SHA/UTC 수정 시각은 `before.json`에 보관했다. 최종 목록·해시는 `after.json`/`changed-files.json`이다. **frontend/tsconfig.json에는10:20:54에 `.next-claude-preview` 타입 경로2개가 별도로 추가된 것을 관찰했다. 이번 작업의 빌드 경로가 아니므로 사용자/다른 작업의 변경으로 보존했고 복원·덮어쓰기하지 않았다. 최신 독립 타입 검사는 이 설정에서 통과했다. `frontend/src/app/layout.tsx`의10:18:01 글꼴 변경도 이번 작업이 아닌 별도 변경으로 보존했다. `globals.css`는 그때의 디자인을 읽은 상태에서 연구 흐름에 한정된 규칙만 덧붙였다. 최신 빌드/브라우저 검증은 이 디자인 상태를 포함했다.** 나머지 패키지/Next 선언/Playwright/pytest/AGENTS 설정은 같은 SHA를 확인했다. 비밀 파일은 복사/보고하지 않았다.

| 실제 절대경로 | 역할 | 구분 |
|---|---|---|
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\README.md` | 현재 지원/실행/검증 안내 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\TEST_REPORT.md` | 이번 명령/시각/실패/성공/실제 파일 근거 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\backend\app\analysis_catalog.py` | 지명/카탈로그·타일/범위 읽기·작업/산출물/영속 소유권 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\backend\app\artifact_store.py` | 지명/카탈로그·타일/범위 읽기·작업/산출물/영속 소유권 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\backend\app\main.py` | 지명/카탈로그·타일/범위 읽기·작업/산출물/영속 소유권 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\backend\app\place_search.py` | 지명/카탈로그·타일/범위 읽기·작업/산출물/영속 소유권 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\backend\app\processing.py` | 지명/카탈로그·타일/범위 읽기·작업/산출물/영속 소유권 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\backend\app\processing_raster.py` | 지명/카탈로그·타일/범위 읽기·작업/산출물/영속 소유권 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\backend\app\processing_record.py` | 지명/카탈로그·타일/범위 읽기·작업/산출물/영속 소유권 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\backend\app\processing_repository.py` | 지명/카탈로그·타일/범위 읽기·작업/산출물/영속 소유권 | 신규 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\backend\app\product_processing.py` | 지명/카탈로그·타일/범위 읽기·작업/산출물/영속 소유권 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\backend\app\range_reader.py` | 지명/카탈로그·타일/범위 읽기·작업/산출물/영속 소유권 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\backend\app\raster_source.py` | 지명/카탈로그·타일/범위 읽기·작업/산출물/영속 소유권 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\backend\app\work_sessions.py` | 지명/카탈로그·타일/범위 읽기·작업/산출물/영속 소유권 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\backend\tests\check_qgis_delivery.py` | 계층·실제 TIFF/타일·소유권/저장·실연결 검증 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\backend\tests\live_research_delivery.py` | 계층·실제 TIFF/타일·소유권/저장·실연결 검증 | 신규 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\backend\tests\test_admin_boundaries.py` | 계층·실제 TIFF/타일·소유권/저장·실연결 검증 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\backend\tests\test_place_search.py` | 계층·실제 TIFF/타일·소유권/저장·실연결 검증 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\backend\tests\test_processing_foundation.py` | 계층·실제 TIFF/타일·소유권/저장·실연결 검증 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\backend\tests\test_processing_records.py` | 계층·실제 TIFF/타일·소유권/저장·실연결 검증 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\backend\tests\test_product_engines.py` | 계층·실제 TIFF/타일·소유권/저장·실연결 검증 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\backend\tests\test_research_workflow.py` | 계층·실제 TIFF/타일·소유권/저장·실연결 검증 | 신규 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\backend\tests\test_work_sessions.py` | 계층·실제 TIFF/타일·소유권/저장·실연결 검증 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\docs\AI_PLACE_CONDITIONS.md` | 계약/이력 분리·출처/재현/상한 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\docs\ANALYSIS_SELECTION.md` | 계약/이력 분리·출처/재현/상한 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\docs\PROCESSING_FOUNDATION.md` | 계약/이력 분리·출처/재현/상한 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\docs\PRODUCT_ANALYSIS.md` | 계약/이력 분리·출처/재현/상한 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\docs\RESEARCH_WORKFLOW.md` | 계약/이력 분리·출처/재현/상한 | 신규 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\docs\WORKFLOW_PAGES.md` | 계약/이력 분리·출처/재현/상한 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\frontend\src\app\globals.css` | Workspace·카메라 전용 위치·연구/처리/보관 표시 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\frontend\src\app\layout.tsx` | 별도 글꼴 변경을 보존 · 이번 수정 파일 아님 | 관찰·보존 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\frontend\src\components\AutomaticConditions.tsx` | Workspace·카메라 전용 위치·연구/처리/보관 표시 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\frontend\src\components\ProcessingExecution.tsx` | Workspace·카메라 전용 위치·연구/처리/보관 표시 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\frontend\src\components\ProcessingOutcome.tsx` | Workspace·카메라 전용 위치·연구/처리/보관 표시 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\frontend\src\components\ResultArchive.tsx` | Workspace·카메라 전용 위치·연구/처리/보관 표시 | 신규 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\frontend\src\components\WorkflowWorkspace.tsx` | Workspace·카메라 전용 위치·연구/처리/보관 표시 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\frontend\src\lib\types.ts` | Workspace·카메라 전용 위치·연구/처리/보관 표시 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\frontend\src\lib\useConditionInput.ts` | Workspace·카메라 전용 위치·연구/처리/보관 표시 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\frontend\tests\ai-camera.spec.ts` | 위치 후보/모바일/수동 보호·기존 회귀 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\frontend\tests\ai-conditions.spec.ts` | 위치 후보/모바일/수동 보호·기존 회귀 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\frontend\tests\ai-primary-fixtures.ts` | 위치 후보/모바일/수동 보호·기존 회귀 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\frontend\tests\automatic-conditions.spec.ts` | 위치 후보/모바일/수동 보호·기존 회귀 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\frontend\tests\boundary-conditions.spec.ts` | 위치 후보/모바일/수동 보호·기존 회귀 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\frontend\tests\collection-readability.spec.ts` | 위치 후보/모바일/수동 보호·기존 회귀 | 수정 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\frontend\tests\research-workflow.spec.ts` | 위치 후보/모바일/수동 보호·기존 회귀 | 신규 |
| `C:\Users\aicam\Documents\ChatGPT\바이브코딩\frontend\tsconfig.json` | 별도 생성된 preview 타입 경로 추가를 보존 · 이번 수정 파일 아님 | 관찰·보존 |

영속 보관은 새 공통 `/processing/jobs` 경로에 한정한다. 기존 `/cloud/jobs`·`/estimate/jobs` 및 직접 반환하는 구형 A4 결과는 기존 메모리/임시 보관을 유지하므로 즉시 다운로드해야 한다. 같은 QA/NDVI 변화/관측 합성/제한 ML도 공통 처리 방법에서 실행한 작업만 새 보관함·재시작 복원 대상이다.

## 실패 이력과 남은 한계

초기 전체 pytest를 저장소 루트에서 호출해 기존 fresh-process 테스트4건의 `import app`이 실패했다. 이후 문서화된 backend cwd로 재실행했다. 또 옛15분 TTL/세션 쿠키/메모리 소실·경계 자동 부착 기대를 새 계약에 맞게 보완했다. 마지막 전체638/28/0만 현재 결과로 사용한다.

처음 전체 E2E는 **207통과/32생략/5실패**였다. 모두 지명 선택만으로 AOI가 생성되거나 위치까지 자동 선택됐다고 기대한 옛 계약 테스트였다. 실제 candidate 클릭·카메라 이동·수동 AOI·수정 보호로 검증을 바꾼 뒤 **전체244개를 다시 실행**했다. polygon 테스트는 이 두 전체 실행 모두 통과했다. 새 테스트 작성 중 버튼 이름 불일치 실행은 중단했고 이름을 실제 코드로 수정한 새12건과 마지막 전체에 포함했다. 빌드 중 nullable mentioned_text의 TypeScript 오류도 발견·수정했고 마지막 독립 검사/정식 빌드는0이다. 실패 로그를 삭제하거나 합쳐 통과로 바꾸지 않았다.

**실제 완료:** 이번 S2 소형/79.6km² 대표 파일 흐름, 소유권/재시작 파일 복원, 현재 실제 Kakao/모바일 카메라·AOI 분리. **조건부:** 서버 allowlist 내8개 계산과 제품별 입력·QA·지수/온도 한계, 큰 단일 시점 최대치·출력/전송 제한. 큰 Landsat 실연결/200km² 근처 성능은 이번 미검증이며 과거 소형 성공으로 대체하지 않는다. **미구현:** 침수 확정·토지피복 확정 분류·HLS/VIIRS/SAR/PC S2 픽셀 엔진·범용 ML·로컬 TIFF 업로드·도시 전체 무제한 처리. **미실행/외부 조건:** 실제 유료 AI·NASA/CDSE/USGS 인증 원본·대용량 원본 전체 다운로드·QGIS/ArcGIS GUI. MNDWI는 수역 후보, ML은 별도 추정이며 구름 아래 참값/침수 확정으로 표시하지 않는다.

실행 API/과학식 변경의 세부 계약과 공식 Kakao 문서 링크는 `docs/RESEARCH_WORKFLOW.md` 및 기존 PRODUCT_ANALYSIS를 따른다. 배포·push·새 계정·비용 동의·인증 설정 변경은 없다.

---

# 최신 전체 검증 — 2026-11-04 (실제 완료 범위 제한)

**사이트 전체 완료가 아니다.** 이번 새 실행에서 8개 계산 분석의 공개 표본은 실제 검색 → Item/필수 자료 선택 → 서버 QA/계산 → 실제 브라우저 결과 ZIP 저장 → Rasterio 재열기/수치/체크섬 → QGIS headless 읽기/렌더를 통과했다. 인증 원본·모든 제품/날짜·GUI GIS·실제 OpenAI/Kakao·도시 전체 처리를 완료했다고 표시하지 않는다. 아래 과거 보고서의 통과 수를 현재 증거로 재사용하지 않았다.

증거: `test-results/full-validation-20261104-090758/`. `before.json`은 수정 전 실제 경로·SHA-256·UTC 수정 시각, `backup/`은 변경 대상 원본이다. 계산 엔진·제품 allowlist·페이지/지도·인증·환경파일·패키지 설정은 변경하지 않았다. 변경은 검증 helper/E2E의 명시 LIVE 게이트·기존 fixture 준비와 README/본 보고서에 한정한다. 테스트 소스 변경과 앱 소스 변경은 최종 `after.json`에서 구분한다.

## 1. 이번 실행 명령·시각·종료 코드

모든 시각은 KST다. 실행별 전체 stdout/stderr와 종료 코드 JSON을 같은 증거 폴더에 보존한다.

| 실행 | 실제 명령 / 시각·종료 | 결과·해석 |
|---|---|---|
| backend 전체 기본 | backend cwd `../.venv/Scripts/python.exe -m pytest -q`, LIVE_STAC=0/LIVE_PROCESSING=0; 09:08:01–09:10:57 KST / **exit 0** | **621 passed /28 LIVE skipped**, 이번 새 실행 |
| 독립 typecheck | frontend cwd `npm run typecheck`; 10:06:10–10:06:15 KST / **exit 0** | 독립 실행, build 통과와 별개 |
| 정식 production build | `node evidence/build-staged.mjs` → 복사본에서 `npm run build` (prebuild 포함); 10:06:15–10:06:30 KST / **exit 0** | 실제 Next build. 설치된 node_modules junction 재사용·설치 없음, `.env` 복사 없음 |
| Playwright 전체 기본 | frontend cwd `npx playwright test --workers=2 --shard=N/4` (N=1,2,3,4 순차), LIVE_STAC=0/LIVE_PROCESSING=0; 09:56:59–10:05:28 KST / **exit 0** | **200 passed /32 skipped /0 failed**, 36개 spec/232개 선언 전체 실행. mock 없는 실제 검색은 테스트 오류로 강제. `e2e-case-coverage.json`으로 shard 중복/누락 없이232개 확인 |
| backend 별도 LIVE | 아래 8파일, LIVE_STAC=1/LIVE_PROCESSING=1; 09:12:47–09:16:50 KST / **exit 0** | **28 passed**. fixture 통과로 실제 제공처 오류를 대체하지 않음 |
| 대표 목적별 LIVE E2E | `LIVE_STAC=1 LIVE_PROCESSING=1 npx playwright test tests/analysis-delivery-live.spec.ts --workers=1`; 09:17:44–09:20:38 KST / **exit 0** | **9 passed** = 계산8종 + 큰 AOI 제한1. 실제 파일/수치 검사 |
| LIVE 카드/수동 검색 | `LIVE_STAC=1 npx playwright test tests/provider-activation.spec.ts tests/search.spec.ts --workers=1 --grep '현재 웹 실제 검색\|실제 검색: 지도'`; 09:22:04–09:23:20 KST / **exit 0** | **7 passed**. 공개 메타데이터/UI, 픽셀/원본 전체 완료 증거 아님 |
| LIVE A2·다중 제공처 | `LIVE_STAC=1 npx playwright test tests/analysis-conditions.spec.ts tests/providers.spec.ts --workers=1 --grep 'A2 실제 원본\|실제 공개 다중'`; 09:31:36–09:32:06 KST / **exit 0** | **2 passed**, A2 HEAD/기하와 픽셀 QA는 구분 |
| LIVE 목적 추천 카드 검색 | `LIVE_STAC=1 npx playwright test tests/sensor-recommendations.spec.ts --workers=1 --grep '실제 카드 검색'`; 09:44:05–09:45:05 KST / **exit 0** | **1 passed**, 선택 조건/실검색·밴드 연결 |
| 전체 제공처 공개 접근 | `LIVE_STAC=1 python backend/tests/provider_access_live.py http://127.0.0.1:3012 evidence/provider-access-valid`; 09:17:12–09:18:22 KST / **exit 0** | 9컬렉션 검색·8실제 browse 전체 디코딩·1정확한 미제공. 인증/Range/전체 수신은 아래에서 분리 |
| 실제 작업 제어 | `LIVE_STAC=1 LIVE_PROCESSING=1 python backend/tests/live_job_controls.py evidence`; 09:39:38–09:39:40 KST / **exit 0** | 실제 canonical 계획/running 관찰/취소·같은 idempotency job·다른 세션404·취소 후 다운로드409 |
| 저장 파일 재검사 | `python evidence/reverify.py`; 09:40:34–09:40:36 KST / **exit 0** | 실제 브라우저 ZIP8개 오프라인 재열기·전체 해시/수치·범주 카운트. 새 네트워크 결과를 만든 것이 아님 |
| QGIS | 설치된 `QGIS 4.2.2/bin/python-qgis.bat backend/tests/check_qgis_delivery.py evidence`; 09:21:02–09:21:22 KST / **exit 0** | **8분석·30 TIFF** 실제 QGIS provider 읽기·렌더, 독립 headless 프로필. **데스크톱 GUI 미실행** |

별도 backend LIVE 명령 (backend cwd):

```text
LIVE_STAC=1 LIVE_PROCESSING=1 python -m pytest tests/test_live.py tests/test_providers_live.py tests/test_pixel_quality_live.py tests/test_change_analysis_live.py tests/test_cloud_composite_live.py tests/test_cloud_estimate_live.py tests/test_processing_live.py tests/test_product_live.py -q -s
```

LIVE_PROCESSING 없이 검색만 통과한 경우와 실제 픽셀/파일 통과를 같은 상태로 기록하지 않는다. 기본 pytest의 28 skip은 별도 LIVE 실행에서 28개 통과했다. 기본 E2E의 생략에는 명시 LIVE 조건 및 구형 대용량 원본 전체 확보 전제 테스트가 포함된다. 대표 새 공통 경로는 원본 전체 다운로드 없이 8종을 별도 실제 검증했다. 실제 OpenAI·Kakao는 실행하지 않았으며 자연어/수동 수정 보호/지도 자동 조건은 mock 회귀다.

## 2. 분석 ID별 지원·실제 산출물 증거

공통 필수 입력은 확정 AOI(bbox/폴리곤 출처), 허용 UTC 기간, canonical 제공처/컬렉션/Item, 필수 밴드/QA 선택과 QA 정책 버전이다. 단일 Workspace와 서버 분석 카탈로그를 재사용했다. 코드 계약상 S2A/C·Landsat9 지원과 이번 실제 계산 플랫폼(S2B/L8)은 다르므로 다른 플랫폼을 이번 LIVE 완료라고 표시하지 않는다.

| 분석 ID / 방법 | 지원 제품·추가 필수 조건 | 이번 실제 브라우저 저장 파일 | 범위/상태 |
|---|---|---|---|
| vegetation_index / ndvi | ES S2 L2A red/nir/SCL; PC Landsat C2 L2 red/nir08/QA_PIXEL·RADSAT | NDVI·valid/exclusion mask·manifest, **13,752bytes /3 TIFF** | **실제 완료**: S2B 브라우저, PC L8 backend LIVE |
| vegetation_change / ndvi_change | 같은 S2 플랫폼/제품 기준선, 서로 다른 두 날짜 앞→뒤, red/nir/SCL, 공통 유효 픽셀 | 전/후/차이3밴드·마스크·manifest, **27,180bytes /3 TIFF** | **실제 완료**: S2B 두 날짜 |
| water_extent / mndwi | 위 광학 제품 green/SWIR1/QA; 사용자 임계값·근거(시험0) | MNDWI·수역 후보·마스크·민감도·manifest, **14,881bytes /4 TIFF** | **실제 완료**: 맑은 유효 관측만 사용. 침수 확정 아님 |
| water_change / mndwi_change | 같은 광학 제품/플랫폼 두 날짜·공통 유효·사용자 기준 | 전/후/차이·수역 후보 유지/증감 mask·manifest, **22,622bytes /4 TIFF** | **실제 완료**: S2B 브라우저, PC L8 두 날짜 backend LIVE |
| urban_index / ndbi | 위 광학 제품 SWIR1/NIR/QA | NDBI·마스크·manifest, **13,842bytes /3 TIFF** | **실제 완료**: S2B 브라우저, PC L8 backend LIVE. 피복 분류 아님 |
| surface_temperature | PC Landsat8/9 L2SP lwir11/qa_pixel/qa_radsat/qa/cdist; ST_QA≤2K·CDIST≥1km를 명시 확인 | 온도 K/degC·품질 K/km·마스크·manifest, **17,118bytes /4 TIFF** | **실제 완료**: 이번 실제 계산 L8. L9 계산은 이번 미검증 |
| hotspots | 위 ST + 사용자 섭씨 기준/근거(시험40℃) | 온도/품질·기준 초과 mask·manifest, **17,937bytes /5 TIFF** | **실제 완료**: 명시 기준에 한정, 앱의 보편적 임계값 아님 |
| temperature_comparison | 위 동일 ST 관측/QA + AOI 안의 비중첩 확정 영역2개·이름 | 온도/품질·면적 가중 평균/차이·manifest, **17,391bytes /4 TIFF** | **실제 완료**: 두 테스트 영역. 실제 도시/주변 분류 근거 아님 |
| flood_extent | 사건 기준일·호환 전후·검증/별도 SAR 보정 등 필요 | 확정 침수 파일 없음 | **미구현**. 수역 후보·SAR 검색을 침수 엔진으로 표시하지 않음 |
| landcover_change | 분류 체계·정답 자료·독립 검증 필요 | 확정 피복 변화 파일 없음 | **미구현**. NDBI로 확정 분류를 가장하지 않음 |

정리된 실제 브라우저 ZIP8개는 `deliverables/<analysis_id>.zip`에 복사했고 원래 `download.saveAs` 산출물도 `e2e-live-artifacts/`에 보존한다. SHA-256 전체값/Item/범위/크기는 `analysis-deliveries.json`, 개별 파일 SHA·CRS/NoData/밴드/단위·그리드와 재계산 통계/카테고리 카운트는 `live-delivery/<analysis_id>/rasterio.json`이다. 원본/미리보기/처리 결과를 바꾸거나 가짜 이미지를 생성하지 않았다. 링크만 생긴 것을 전달 완료로 세지 않았다.

독립 파일 검사는 ZIP CRC/모든 manifest 파일 크기·SHA256, 모든 GeoTIFF CRS·transform·크기·자료형·NoData·단위, 유효/제외 마스크 일치, 지수 범위/유한값·전후 차이, K−℃=273.15, QA 기준, 사용자 임계값 후보 코드와 면적 가중 평균/두 영역 차이를 재계산했다. 공식 scale/offset·고정 DN 기대값·0분모·QA 결측·NoData·전부 무효 등은 별도의 pytest 고정 래스터 검사다. 이 검사는 물리적 참값/지표 분류 정확도 검증이 아니다.

기존 S2 실제 QA·관측 합성·제한 ML은 backend LIVE에서 실제 ZIP/마스크/기록 재열기를 새로 통과했다. 대표8종 브라우저 LIVE와 별개라서 **조건부**로 표시한다. 관측 합성은 타 날짜 실측 선택, ML은 관측604,154.05m²/추정237,513.87m²/잔여153,706.48m²를 구분했다. 맑은 공간 보류 오류는 구름 아래 정확도나 확정 복원의 증거가 아니다.

## 3. 제공처/컬렉션별 실제 접근 상태

다음은 **인증을 로드하지 않은 격리 공개 모드**의 이번 새 실제 요청이다. 206은 작은 원본 Range/형식 접근 확인이지 전체 원본 다운로드 완료가 아니다. preview는 실제 전체 이미지 디코딩이며 픽셀 QA가 아니다. probe의 exit0는 검사 완료이지 모든 접근 성공을 뜻하지 않는다. 현재 운영 서버의 기존 키/토큰 유효성을 이 결과로 추정하지 않는다.

| 제공처 / 컬렉션 | 검색 | 실제 browse 전체 수신·디코딩 | 원본 접근 표본 | 앱 픽셀/내보내기 |
|---|---|---|---|---|
| Earth Search / sentinel-2-l2a | 200/2건 | 성공26,038bytes | 공개 Range206 | 위 검증 S2B QA/지수·변화/합성/제한 ML |
| Earth Search / landsat-c2-l2 | 200/1건 | 동일 제품 PC 출처 성공1,239,292bytes | **USGS 로그인302**, requester-pays 별도 | 이 제공처 선택은 픽셀 미지원. PC와 몰래 교체하지 않음 |
| CDSE / sentinel-1-grd | 200/1건 | 성공109,624bytes | **provider_authentication_required** | SAR 보정/침수 엔진 없음 |
| NASA CMR / viirs-vnp09ga-002 | 200/2건 | 성공70,963bytes | **earthdata_not_configured**(격리 모드) | QA/NDVI 처리 미지원 |
| PC / pc-sentinel-2-l2a | 200/2건 | 성공2,190,270bytes | 공개 SAS Range206 | 보정 메타데이터/검증 어댑터 조건 미충족, 계산 미지원 |
| PC / pc-landsat-c2-l2 | 200/1건 | 성공1,239,292bytes | 공개 SAS Range206 | 위 L8 실제 계산/내보내기. L9 원본 Range와 L9 계산 완료는 다름 |
| NOAA NODD / noaa-viirs-ndvi-cdr | 200/2건 | **missing_asset 정상 미제공** | 공개 NetCDF Range206 | 전 지구 격자를 AOI 유효 픽셀로 간주하지 않음. 앱 처리 미지원 |
| NASA CMR / hls-l30-002 | 200/1건 | 성공177,916bytes | **earthdata_not_configured**(격리 모드) | HLS 광학30m, 픽셀 엔진 미연결 |
| NASA CMR / hls-s30-002 | 200/2건 | 성공143,029bytes | **earthdata_not_configured**(격리 모드) | S2 원본10m/온도/구름 복원이 아님 |

정확한 Item ID·실행 시각·HTTP/형식·상태는 `provider-access-valid/providers.json`에 있다. 기존 HLS browse HTTP400이 이 표본에서는 재현되지 않았지만 사용자 자신의 장면/인증 원본 문제가 해결됐다고 단정하지 않는다. NASA 인증 원본·CDSE/USGS 계정 경로는 별도 승인된 기존 서버 정책 안에서 후속 검증해야 하며 새 자격증명을 요구하거나 발급하지 않았다. USGS 토큰으로 AWS 비용 경로를 우회하거나 Earthdata로 USGS를 해결하지 않았다.

## 4. 재현·공간 범위·보관

- S2B 표본: ES S2 L2A, bbox `[126.7,36.4,126.71,36.41]`, UTC2021-07-01~31, `S2B_52SBF_20210716_0_L2A`; 변화는 `S2B_52SBF_20210726_0_L2A` 추가. 한 시점 유효604,154.05m², 두 날짜 공통 유효436,928.95m². 구름/결측을 제외한 실제 유효 영역에 한정한다.
- ST 표본: PC Landsat L2SP, bbox `[-115.15,36.16,-115.14,36.17]`, UTC2025-07-01~31, `LC08_L2SP_039035_20250719_02_T1`; 유효718,273.86m². 고온은 명시40℃, 두 영역은 서쪽/동쪽 직사각형 테스트 구역으로 도시 유형이나 행정경계가 아니다.
- UI 순서: 수집에서 목적/위 제품·기간·AOI 입력 → 추천 카드 선택/명시 검색 → 해당 UTC 날짜/Item → 세부 분석 선택으로 → 분석 의도 확인 → 필수 밴드·QA(온도 qa/cdist 추가)/기준/영역 → 계획 검사 → 확인 체크/실행 → 실제 지도/수치·한계 → 처리 ZIP 다운로드. 자동 원본 수신·유료 AI·범위 축소는 없다.
- 도시 규모: 서울 포함 bbox `[126.76,37.42,127.18,37.70]`, UTC2025-08-15~30에서 실제 L2SP 검색4건, 선택 `LC09_L2SP_116034_20250824_02_T1`, **동일 bbox 계획422/50km² 초과, 작업 시작0건**. 확정 서울 행정경계 폴리곤 통계가 아니며 작게 잘라 성공시킨 것이 아니다.
- 새 공통 QA/NDVI/제품 지수/ST의 코드 상한50km²·150,000셀과 기존 합성/ML25km²를 유지했다. 이번 실제 계산 표본은 약1km²이며 상한 근처 성능/도시 전체 분할 처리를 검증한 것이 아니다.
- 결과는 브라우저 원본 TIFF를 입력으로 쓰지 않고 canonical 서버 Asset 범위 읽기를 사용한다. 원본 전체 수신 기록은 서버 접근 증거가 아니다. 로컬 TIFF 업로드는 미구현이다.
- 소유권/15분 보관·단일 worker·서버 재시작 시 이전 작업 복원 불가를 유지한다. 브라우저 이동/새로고침은 GET 상태 복원이며 재실행하지 않는다. 실제 취소 작업은 다른 세션404/결과409/중복 시작 동일job을 통과했다. 증거용 파일 사본은 테스트 산출물이지 만료 서버 URL을 공유하는 우회 경로가 아니다.

## 5. 실패 이력·미구현·남은 한계

- 초기 전수 실행에는 이전 LIVE 게이트가 없는 실제 검색들이 섞였다. 실제 검색을 명시 LIVE로 옮기고 fixture의 mock 없는 검색을 테스트 오류로 강제했다. 마지막 감지된 실제 카드 검색1건은 **200통과/31생략/1실패**로 남았으며 해당 LIVE를 별도로 실행했다. 실패/중단 로그를 삭제하거나 성공 수로 바꾸지 않았다.
- 전수에서 드러난 옛 `next-work` 정상 QA fixture는 큰 충남 예시 AOI를 사용해 실제 처리 상한에 걸렸다. 정상 조건 fixture만 약1km²·명시 좌표 확인으로 수정했고 큰 AOI 거절은 실제 도시 LIVE로 유지했다. 최신 수집 입력 가독성 계약(입력 옆 단일 검색/추천 카드 선택은 자동 검색 안 함)에 맞춰 오래된 DOM 순서 기대를 갱신했다. 실제 필수 자료/QA/제한을 느슨하게 하지 않았다.
- `cloud-workflow`의 요청 캡처 직후 값 검사 race를 실제 요청 도착까지 poll하는 결정적 검사로 바꿨다. 제공처 probe 초기에는 미설치 PIL/import 및 잘못된 미디어 Origin/쿠키 경로403을 만났고, 설치 없이 기존 Rasterio와 정상 프런트 경로로 수정한 뒤 새 실행했다. 이를 제공처 장애로 분류하지 않았다.
- 그 뒤 단일 전수는 **199통과/32생략/1실패**였고, polygon 복원 테스트가 비동기 요청 캡처 전 `undefined.roi`를 읽은 경합이었다. 요청 도착을 poll하도록 보완한 뒤 해당 파일5개 통과, 이어 동일 전체를4 shard로 다시 실행했다. 마지막 전체 결과는 위 표만 사용한다. 첫 shard 호출의 PowerShell 인수 전달 오류4건은 테스트가 시작되지 않은 CLI 오류로 `shard-startup-errors/`에 보존했고 실행 수에 넣지 않았다.
- 원본 전체 파일은 이번에 내려받지 않았고 결과 ZIP만 완전 수신했다. 단기 SAS/권한 거부/만료·0건·부분 실패·NoData·QA 누락·늦은 응답은 fixture/단위 검증과 실제 표본을 구분한다. 다중 worker·영속 큐/공개 운영·도시 규모 엔진·침수 확정/피복 분류·HLS/VIIRS/SAR/PC S2 픽셀 처리는 **미구현**이다.
- MNDWI 임계값/민감도와 NDVI/NDBI를 독립 참값 검증으로 오해하지 않는다. 나지/시가지 혼동·계절/대기/관측 차이, 구름 주변 온도 오차·ASTER/NoData 결측이 남는다. Landsat ST DN×0.00341802+149K, ℃=K−273.15를 한 번 적용하며 열관측100m와 제품 격자30m를 분리한다. S2 공통20m/제품별 QA/보정은 manifest의 버전·출처를 따른다. 공식 근거/정책은 `docs/PRODUCT_ANALYSIS.md`에 보존한다.
- 실제 OpenAI·Kakao, 현재 운영자 토큰/권한의 유효성·NASA/CDSE/USGS 인증 원본 전체 수신, QGIS/ArcGIS 데스크톱 GUI, S2A/C·L9 계산 표본, 상한 근처/도시 전체의 성능은 **실패/미검증** 영역으로 남긴다. 공개 browse/Range 성공이나 fixture 통과로 대체하지 않는다.

## 6. 변경/보존·정리

새 검증: `frontend/tests/analysis-delivery-live.spec.ts`, `backend/tests/verify_analysis_delivery.py`, `provider_access_live.py`, `check_qgis_delivery.py`, `live_job_controls.py`. 기존 검증 수정: frontend `provider-activation.spec.ts`, `search.spec.ts`, `analysis-conditions.spec.ts`, `providers.spec.ts`, `sensor-recommendations.spec.ts`, `runtime.ts`, `next-work.spec.ts`, `cloud-workflow.spec.ts`, `processing-foundation.spec.ts`. 사용자 문서: `README.md`, `TEST_REPORT.md`.

최종 앱 소스/설정 비교와 서버 정리는 아래 최종 기록을 따른다. 배포·push·의존성 설치·계정/키 발급·비용 동의·과학 계산/새 모델 변경은 없다. 기존3000/8000 서버는 종료하지 않았다.

최종 앱 소스 변경 0개, 원래 tsconfig/next-env/package 설정 보존 True. 기존3000/8000 서버 PID 유지 True. 격리3012/8012 서버 종료 True. 전체 source SHA/수정 시각·변경 목록은 `after.json`/`changed-files.json`에 있다.

---

# 수집 → 실행 → 실제 결과·전달 Phase — 2026-11-04

이번 Phase는 기존 `/`·`/processing`·단일 Workspace·MapLibre·제품별 서버 카탈로그·8개 분석/기존 QA·합성/제한 ML 엔진을 재사용했다. 계산식·제품 allowlist·인증/환경변수·재제공 설정·의존성·디자인 시스템은 변경하지 않았다. 침수 확정/피복 변화 분류, HLS/VIIRS/SAR/PC S2 픽셀 처리, 로컬 TIFF 업로드를 새로 지원하지 않는다. 추천 적합성/검색/원본 수신/서버 접근/픽셀 QA/작업 성공/파일 전달은 별개다.

수정 전 대상 파일의 실제 절대경로·SHA-256·UTC 수정 시각과 원본은 `test-results/flow-results-20261104-081921/before.json`, `extra-before.jsonl`, `backup/`에 보관했다. Git 상태를 전제로 덮어쓰지 않았으며 `.env`를 읽거나 변경하지 않았다. 이 절의 실행은 이번 Phase의 새 실행이며 아래 과거 수치를 재사용하지 않는다.

## 변경 파일과 실제 연결

| 실제 경로 (프로젝트 루트 기준) | 역할 |
|---|---|
| `backend/app/processing.py` | canonical/픽셀 단계의 실제 진행·실패·취소 events, 성공 후 작업 보관 갱신, 소유 세션/실제 파일 보관 상태 응답, 전송 쿼터 429와 슬롯 정리 |
| `backend/app/artifact_store.py` | 파일 저장/재열기 후에만 실행 기록·생성/만료 UTC를 게시. 존재·크기·TTL 조회와 다운로드 전체 해시 재검사 구분 |
| `backend/app/processing_record.py` (신규) | 실제 성공한 파일의 입력 ID/Asset key·출력·격자, 실행/생략/개별 근거 미기록 단계. 합성/ML을 해당 실행에서만 완료로 기록 |
| `frontend/src/components/ProcessingExecution.tsx` | 계획/확인/상태/결과/만료/재시도, 실제 장면 구름·기하 중첩, 원본 선택 사항·서버 입력 출처, 늦은 응답/이전 결과 차단, 저장된 polygon 모드 복원 |
| `frontend/src/components/ProcessingOutcome.tsx` (신규) | 실제 배열 미리보기, AOI·관측·유효 면적/분모, 실측 합성/ML 추정 면적, 실행 기록·입출력·정책·한계 |
| `frontend/src/components/WorkflowWorkspace.tsx`, `NaturalWorkflow.tsx`, `WorkSummary.tsx` | 기존 S2 실행에서도 브라우저 수신 강제를 제거. 필수 선택/세부 분석·공간·기간 및 서버 실제 검사 유지. 원본 수신 요약 보존·선택 제품별 미지원 안내 |
| `frontend/src/lib/types.ts`, `frontend/src/app/globals.css` | 선택적 작업/산출물 필드, 기존 디자인 안의 결과·미리보기·긴 오류/키보드 포커스/모바일 스타일 |
| `backend/tests/test_processing_records.py` (신규), `create_product_ui_fixture.py`, `test_product_live.py` | 실제 소형 TIFF·manifest/실행 근거·실패 null·보관 누락/변경/만료·전송 상한 및 격리 실연결 증거 |
| `frontend/tests/product-engines.spec.ts`, `processing-foundation.spec.ts`, `product-engines-live.spec.ts` | 8개 실제 분석 경로의 로컬 TIFF 계산 파일 저장/재열기, 오류 재시도·키보드·만료·긴 오류·polygon 모드 복원·실제 공개 PC 브라우저 처리 |
| `frontend/tests/analysis-selection.spec.ts`, `processing-guidance.spec.ts`, `workflow-pages.spec.ts`, `cloud-workflow.spec.ts` | 원본 수신과 서버 계산 분리, 명시 세부 선택을 기다리는 fixture 준비·기존 흐름 회귀 |
| `README.md`, `docs/WORKFLOW_PAGES.md`, `docs/PROCESSING_FOUNDATION.md`, `TEST_REPORT.md` | 현재 입력/단계/보관/전달 계약과 실제 증거 |

API 경로와 엔진은 그대로다. `ProcessingJob`에 `events`, `retention`, `ownership`, `job_expires_at`, 산출물에 `created_at`, `expires_at`, `execution_record`를 선택적으로 추가했다. 원본 파일 전체 수신 기록은 서버 접근 증거가 아니다. 기존 보안/자원 상한(단일 worker/소유권, 15분, 원본 Range 64MiB·시간/요청/동시성, 결과 ZIP16MiB/해제32MiB/디스크256MiB)을 유지한다. 파일 링크만으로 전달 완료를 기록하지 않는다.

## 이번 실제 실행 (KST, 종료 코드)

| 검증 | 실행 명령·시각 | 결과 |
|---|---|---|
| backend 전체 | `cd backend; ../.venv/Scripts/python.exe -m pytest -q`, 08:31:42–08:33:36 | **exit0 · 621 passed /28 skipped** |
| 독립 타입 검사 | `cd frontend; npm run typecheck`, 08:48:10–08:48:12 | **exit0** |
| production build | `node ../test-results/flow-results-20261104-081921/build-check.mjs` (frontend cwd; `next build --webpack`), 08:48:27–08:48:45 | **exit0** · 격리 dist/서버 환경 필터·생성 설정 복원 |
| 관련 18파일 E2E | 아래 명령, 08:40:13–08:43:12 | **exit0 · 113 passed /4 skipped** · polygon 복원 추가 보완 전; 다른 흐름 동일 |
| 마지막 복원/제품별 E2E | `npx playwright test tests/processing-foundation.spec.ts tests/product-engines.spec.ts --workers=2`, 08:47:21–08:48:04 | **exit0 · 15 passed**, 최신 앱 코드/독립 fixture 폴더 |
| 실제 공개 범위 읽기/산출물 | `LIVE_STAC=1 LIVE_PROCESSING=1 python -m pytest tests/test_product_live.py -q -k '(es_s2 and ndvi and not change) or (pc_landsat and surface_temperature)'`, backend cwd, 08:34:36–08:34:52 | **exit0 · 2 passed /9 deselected** |
| 현재 사이트 실제 브라우저 | `LIVE_STAC=1 LIVE_PROCESSING=1 npx playwright test tests/product-engines-live.spec.ts --workers=1`, frontend cwd, 08:49:46–08:50:13 | **exit0 · 1 passed**, 실제3000/8000 검색→처리→파일 저장/재열기 |

관련 18파일 명령 (frontend cwd, 격리된 production 서버3012/8012, 유료 AI/Kakao 차단):

```text
npx playwright test tests/product-engines.spec.ts tests/processing-foundation.spec.ts tests/processing-guidance.spec.ts tests/analysis-selection.spec.ts tests/workflow-pages.spec.ts tests/scene-cards.spec.ts tests/reliability.spec.ts tests/imagery-explorer.spec.ts tests/imagery-layout.spec.ts tests/public-data.spec.ts tests/media-access.spec.ts tests/landsat-preview.spec.ts tests/providers.spec.ts tests/external-access.spec.ts tests/pixel-quality.spec.ts tests/change-analysis.spec.ts tests/cloud-workflow.spec.ts tests/estimate-mode.spec.ts --workers=2 --grep-invert 'LIVE|실제 공개 다중 제공처 검색'
```

35개 frontend 전체 spec를 실행한 것은 아니다. 네 생략은 기존 대용량 확보 전제 등의 구형 실연결 게이트다. fixture는 테스트 경로에만 존재한다. 관련 파일의 1440/1280/390px, 키보드 실행/재시도, 긴 오류·가로 넘침, 목록↔지도/날짜/비교/밴드, 원본과 링크 목록, 미지원, 새로고침/뒤로가기/중복 실행 금지/응답 경합을 검사했다. 저장 E2E는 `download.saveAs` 후 ZIP 해시와 모든 TIFF의 CRS/NoData/실제 배열을 다시 열었다. 이는 GIS 데스크톱 GUI 검증과 다르다.

시행착오도 보존했다: `pytest-focused`의 새 기록 기대값2건을 실제 기존 radiometry 증거에 맞춰 수정했다. `pytest-all`의 루트 cwd 실행4건은 자식 Python의 `app` 경로 오류였으며 backend cwd 전체 재실행은 통과했다. 초기 dev E2E는 빌드 설정 갱신/탐색 경합, 구형 수신 강제 기대, 다음 실행의 문구 기대/세부 분석 fixture 선택 준비 순서 때문에 실패했다. 계획·필수 조건/기대 동작을 유지해 수정했고 격리 production E2E가 위 결과로 통과했다. 마지막 `e2e-delivery`는 공유 fixture 준비가 비정상 종료해5통과/1실패/9미실행이었다. 같은 생성기 단독 실행은 정상이며 당시 stderr가 보존되지 않아 최초 종료 원인은 확정할 수 없다. 제품 fixture를 실행/worker별 독립 폴더로 분리하고 stderr를 보존하도록 한 뒤 `e2e-complete`15개가 모두 통과했다. 테스트 진단의 Error 타입 속성1건도 수정해 마지막 독립 typecheck/build가 통과했다. 모든 로그·시각/종료 코드 JSON은 같은 증거 폴더에 있다. NumPy 기존 deprecation 경고는 남아 있다.

## 실제 공개 표본과 범위

| 실제 입력 | 이번 Range → 실제 파일 저장/재열기 |
|---|---|
| Earth Search `S2B_52SBF_20210716_0_L2A`, NDVI, bbox `[126.7,36.4,126.71,36.41]`, 2021-07 UTC | **성공** · 입력3,227,648bytes/11 Range, ZIP13,743bytes · AOI 유효60.6962% |
| PC `LC08_L2SP_039035_20250719_02_T1`, L2SP ST, bbox `[-115.15,36.16,-115.14,36.17]`, 2025-07 UTC | **성공** · 입력376,832bytes/20 Range, ZIP17,117bytes · AOI 유효71.9435%, K/degC·QA/마스크/manifest 재열기 |

이 실제 API/파일 검증은 공개 COG AOI 범위만 사용했다. NASA/USGS/CDSE 인증, 제공처 browse, 원본 전체 TIFF, 서울 전체/도시 규모 처리, GIS GUI, 유료 AI는 이번 검증에서 실행하지 않았다. 기존 HLS400/CDSE 인증 실패 등의 별도 오류를 해결했다고 주장하지 않는다. 확정 침수/피복 분류·새 업로드/새 모델·대형 AOI 엔진·다중 worker 영속 저장은 미구현 유지다. 등록 행정경계 모드 복원 fixture는 가짜 경계를 실제 제공처 처리한 증거가 아니다.

## 사이트 반영·브라우저 실연결

사용자는 이번 작업에서 진행 중인 분석/다운로드 없음과 검증 후 이 프로젝트만 재시작을 승인했다. 두 포트가 같은 `scripts/start-local.mjs` 트리이며 실제 자식 경로가 이 프로젝트임을 재확인했다. 픽셀 worker0건을 확인한 뒤 **08:49경 이 트리만 종료하고 `.\start.cmd`로 재시작**했다. 다른 앱/서버는 종료하지 않았다. 환경변수/키/승인 플래그는 그대로다.

- 실제 주소: `http://127.0.0.1:3000/`, `http://127.0.0.1:3000/processing`.
- 08:49:28 health 양쪽ok, `/processing`200, 웹 카탈로그5개 제공처/9컬렉션, 분석10개/계산 지원8개/방법11개. 카탈로그는 dictionary라서 객체 property 수로 계수했다.
- 재시작한 사이트에서 별도의 새 테스트 브라우저로 PC Landsat ST의 **실제 검색/선택/계획/QA·온도 계산/지도/실행 기록/파일 보관 확인/ZIP 전체 저장/재열기 성공**. 원본 TIFF 전체 수신 없이 서버 Asset Range를 사용했다. 제공처 browse·원본 다운로드·유료 AI/Kakao는 이 실브라우저 시험에서 차단했다.
- 브라우저 저장 ZIP **17,116bytes**, SHA-256 `54cb6c3918aba6aa2499a2e28fa08f32c64a3a373385f4f607de1036bc11aa49`. `temperature.tif`7,052bytes/2밴드 K·degC, `temperature_quality.tif`4,182bytes/2밴드 K·km, 유효1,344bytes/제외1,377bytes 마스크와 manifest. 모두30×38셀, 실제 저장 ZIP/TIFF 재열기와 manifest 해시 대조를 통과했다. 자세한 파일 근거는 `live-browser-files.json`과 `live-browser-artifacts/`에 있다.
- 같은 결과 확인 순서: 직접 목적 **열환경**, UTC **2025-07-01~31**, bbox **서-115.15/남36.16/동-115.14/북36.17** → PC Landsat 추천 제품 선택/검색 → 2025-07-19, `LC08_L2SP_039035_20250719_02_T1` 선택 → `세부 분석 선택으로` → `지표면 온도` 확인 → 필수 밴드/QA에서 기본 lwir11/qa_pixel/qa_radsat에 qa·cdist 추가 → `공통 처리 계획 검사` → 확인 체크/실행 → 실제 QA·지도/수치/실행 기록 → `검증된 처리 ZIP 다운로드`. 사용자 자신의 AOI/조건을 몰래 이 표본으로 바꾸지 않는다.
- 파일은 같은 브라우저 세션 소유/생성 후15분이다. 시험 브라우저 작업은 사용자 프로필의 작업이 아니므로 ID로 공유 접근하지 않는다. 새로고침 자체는 처리/다운로드를 재실행하지 않는다. 재시작 전 작업은 복원할 수 없다. QGIS/ArcGIS GUI 재열기와 나머지 실제 제공처 인증 경로는 이번 Phase에서 미검증이다.
- 격리3012/8012 시험 서버는 종료했다. `frontend/tsconfig.json`·`next-env.d.ts`는 수정 전 바이트와 동일하게 보존했다. 최종 변경 목록·SHA/수정 시각은 `after.json`/`changed-files.json`을 따른다.

---

# 제품별 기초 분석 완결 — 2026-11-03 (products-2)

이번 기록은 1단계 조사/2단계 기반 이후의 최신 코드·실행이다. 이전 통과 수를 현재 성공으로 재사용하지 않았다. Git 저장소 없이 수정 전250개 파일의 경로·SHA-256·UTC 수정 시각과 원본을 `test-results/product-engines-20261103-210850/before-files.json`, `backup/`에 보관했다. 키/환경변수/인증·재제공 플래그·의존성 설치·유료 AI·배포/push 변경은 없다.

## 실제 연결된 작업과 제품

백엔드 `/analysis/catalog`의 `products-2` 계약이 실행 지원의 단일 원천이다. 10개 세부 후보 중 **8개 기초 계산**을 연결했고 침수 확정·토지피복 변화 분류2개는 미지원으로 유지했다. 처리 방법은 기존 QA/합성/제한 ML을 합쳐11개다. [제품 적합성 표·공식 근거·버전·QA·사용 순서](docs/PRODUCT_ANALYSIS.md)를 확인한다.

| 작업 | 실행 allowlist/실제 계산 | 산출물 |
|---|---|---|
| 한 시점 NDVI | ES S2 L2A, PC Landsat8/9 C2 L2 반사도. 실제 Red/NIR·제품별 QA·보정 후 기존 NDVI 수치 커널 재사용 | `ndvi.tif`, valid/exclusion mask, manifest, 실제 지도 |
| 두 시점 NDVI 변화 | 기존 ES S2 동일 플랫폼·기준선·앞→뒤 날짜·공통 유효 픽셀 유지 | 기존 전후/차이3밴드·공통 계약 ZIP |
| MNDWI 수역 후보/변화 | ES S2/PC Landsat 반사도 Green/SWIR1. 사용자 임계값·근거 필수. 변화는 동일 제품/플랫폼·날짜 순서·공통 유효 픽셀 | `mndwi.tif` 또는 `mndwi_change.tif`, 후보/유지·증가·감소 mask, 기준±0.05 면적 민감도 |
| NDBI | 위 광학 제품 SWIR1/NIR. 나지/시가지 혼동·확정 피복 아님 | `ndbi.tif`, 마스크·기록 |
| 지표면 온도 | PC Landsat8/9 **L2SP**만. 실제 ST_B10(lwir11), QA_PIXEL/RADSAT, ST_QA(qa), ST_CDIST(cdist). 공식 보정 한 번 | `temperature.tif`2밴드 K/degC, `temperature_quality.tif` K/km·마스크 |
| 고온 지역 | 위 온도와 사용자가 명시한 섭씨 기준/근거가 있을 때만 | 온도 + `hotspots.tif` |
| 도시/주변 온도 비교 | 같은 ST 관측/QA·AOI 안의 비중첩 확정 영역2개와 이름 | 온도 + 영역별 면적 가중 평균/차이·유효 분모·manifest |

공통 `plan→명시 확인→job→실제 지도→binary ZIP`을 재사용한다. 브라우저 원본 수신 기록을 서버 입력/접근 증거로 사용하지 않는다. 서버가 canonical Item/Asset·제품/플랫폼/밴드 식별·날짜·QA/NoData/자료형·보정·실제 헤더를 다시 검사한다. 직접 입력 기준·QA 옵션·비교 영역은 같은 Workspace 설정/snapshot으로 연결하며 변경 시 계획·확인·오래된 응답/지도 적용을 무효화한다.

공식 재확인: Copernicus S2 제품/밴드/SCL·baseline offset, USGS C2 scale/QA/ST와 LSDS-1619 **v6.0(May2024)**, NASA NDVI/MNDWI/NDBI 정의를2026-11-03 읽었다. 문서 URL·확인일·제품/정책 버전·실제 출처/촬영일·헤더·단위·QA를 manifest에 기록한다. 새 지수는 기존 NDVI 정규화 차이 커널을 재사용하고 L2에 대기 보정을 반복하지 않는다. 열관측100m와 ST30m 출력 격자를 구분한다.

실제 PC QA_PIXEL은 STAC fill1인데 TIFF 헤더 NoData 태그가 없었다. 이 밴드만 공식 bit0 fill 검사로 처리한다. QA_RADSAT=0은 정상이다. 다른 반사도/ST/중간 품질 밴드의 NoData·scale 검사는 유지한다. 온도 QA 기본 제안2K/1km는 사용자 수정·확인 대상 운영값이며 보편적 과학/정확도 기준이 아니다. 기준을 낮추어 실검증을 통과시키지 않았다.

HLS30m·PC S2·NOAA·SAR와 ES requester-pays Landsat를 새 픽셀 allowlist에 넣지 않았다. PC S2 표본에는 밴드별 보정 메타데이터가 없어 추정 offset을 적용하지 않는다. NASA/USGS/CDSE 인증·HLS400·AWS 비용 경로를 이번 계산 성공으로 해결했다고 주장하지 않는다.

## 변경 파일 (작업 루트 아래 실제 경로)

루트 `C:\Users\aicam\Documents\ChatGPT\바이브코딩\`. 수정 전 백업을 보존하고 최종 목록/해시/수정 시각은 해당 증거 폴더의 `after-files.json`, `changed-files.json`에 기록한다.

| 파일 | 역할 |
|---|---|
| `backend/app/product_policy.py` (신규) | 목적/제품/제공처 allowlist·실제 Asset 키·공식 보정/QA·출처/버전 |
| `backend/app/band_math.py`, `landsat_temperature.py` (신규) | 기존 NDVI 수치 재사용, ST 단일 변환·Landsat QA |
| `backend/app/product_processing.py` (신규) | canonical 준비·범위 읽기·QA/격자·지수/ST/영역통계·공통 파일/지도 |
| `backend/app/analysis_catalog.py` | 8개 실제 분석·제품 행렬·사용자 입력/산출물·미지원 계약 |
| `backend/app/processing_models.py`, `processing.py`, `processing_worker.py` | 사용자 기준/확정 영역·QA 버전 검증, 기존 계획/작업에 새 방법 연결 |
| `backend/app/pixel_raster.py`, `processing_raster.py`, `artifact_store.py`, `raster_source.py` | 기존 기본 동작 유지하며 제품별 헤더/NoData·20/30m 격자·혼합 단위 TIFF 검증·안전한 오류 |
| `backend/app/metadata.py`, `recommendations.py` | 같은 카탈로그로 검색 카드·추천의 실행 후보 표시, 별도 추천기 없음 |
| `frontend/src/components/ProcessingExecution.tsx` | 제품별 필수 밴드/QA·기준·영역·계획/확인·통계/지도·파일 UI |
| `frontend/src/components/WorkflowWorkspace.tsx`, `WorkSummary.tsx`, `AnalysisSelection.tsx` | 같은 상태·서버 입력 계약·현재 가능한 행동·이전 응답/레이어 구분 |
| `frontend/src/components/Results.tsx`, `MapPanel.tsx` | 서버 지원 후보 표시, 한/두 장면의 실제 지수/온도 레이어와 정확한 범례 |
| `frontend/src/lib/types.ts`, `analysisFlow.ts` | 서버 제품/입력 계약 타입·표시 검사 |
| `backend/tests/test_product_engines.py` (신규) | 고정 실제 TIFF 수치/QA·실패·파일 재열기·온도 job/소유권65검사 |
| `backend/tests/test_product_live.py`, `create_product_ui_fixture.py` (신규) | 명시 공개 실연결, tests 전용 실제 TIFF 생성(서비스 fallback 아님) |
| `backend/tests/test_analysis_flow.py`, `test_processing_foundation.py` | 8지원/2미지원·기존 공통 계약 검사 갱신 |
| `frontend/tests/product-engines.spec.ts`, `product-engines-live.spec.ts` (신규) | 기준/영역/QA·390px·복원·파일, 실제 PC ST 브라우저 저장/재열기 |
| `frontend/tests/fixtures.ts`, `analysis-selection.spec.ts`, `cloud-workflow.spec.ts`, `estimate-mode.spec.ts`, `pixel-quality.spec.ts`, `imagery-explorer.spec.ts`, `imagery-layout.spec.ts`, `reliability.spec.ts` | 실제 지원 플랫폼/복합 ID·작은 AOI·현재 미디어 경로/레이어 이름·뷰포트 조건의 회귀 fixture |
| `README.md`, `docs/PRODUCT_ANALYSIS.md`(신규), `docs/PROCESSING_FOUNDATION.md`, `docs/ANALYSIS_SELECTION.md`, `TEST_REPORT.md` | 최신 계약/출처/제한·실행 근거 |

## 실제 검사·명령·시각 (KST)

모든 로그와 `*-result.json`은 `test-results/product-engines-20261103-210850/`에 있다. 아래 종료 코드는 실제 프로세스 기준이며 PowerShell의 NO_COLOR 경고와 구분한다.

| 검사/명령 | 시각 | 결과 |
|---|---|---|
| backend `..\.venv\Scripts\python.exe -m pytest -q --durations=3` | 21:56:09–21:58:41 | **0,616 passed/28 skipped**,147.99초 (`pytest-final2*`) |
| 신설 제품 TIFF/QA/입력/job 검사 `...pytest -q tests/test_product_engines.py` | 중간 구현 검증 | **0,65 passed**,6.11초 (`product-final.log`), 전체616개에 포함 |
| 독립 `npm.cmd run typecheck` | 22:08:07–22:08:10, 원래 타입 설정 복원 후에도 재실행 | **0**, `typecheck-release-result.json`, `typecheck-restored-result.json` |
| 격리 production `node ../test-results/product-engines-20261103-210850/build-check.mjs`→`next build --webpack` | 22:08:10–22:08:35 | **0**, `/`·`/processing` 빌드, `build-release-result.json` |
| 관련18파일 E2E, 아래 명령 | 22:02:47–22:07:22 | **0,108 passed/4 skipped**,4.5분 (`e2e-final4*`) |
| `LIVE_STAC=1 LIVE_PROCESSING=1 ...pytest -q tests/test_product_live.py tests/test_processing_live.py` | 21:36:13–21:37:28 | **0,11 passed** (`live-final*`): 새10조합+기존 실제 S2 NDVI 변화/API 작업 |
| 위 LIVE로 `...pytest -q tests/test_product_live.py -k 'pc_landsat and mndwi_change'` | 21:55:18–21:55:33 | **0,1 passed/10 deselected** (`live-pc-change*`). 실제 검색으로 추가 확인한 같은 LC08 두 날짜 |
| LIVE `npx playwright test tests/product-engines-live.spec.ts --workers=1` | 21:50:17–21:50:41 | **0,1 passed**, 실제 PC 검색/선택/원본 범위/작업/지도/ZIP 저장/재열기 (`live-browser*`) |

관련 E2E 실제 명령(frontend cwd, `E2E_BASE_URL=http://127.0.0.1:3012`, `E2E_API_BASE_URL=http://127.0.0.1:8012`, LIVE 플래그 제거):

```powershell
npx.cmd playwright test tests/product-engines.spec.ts tests/processing-foundation.spec.ts tests/analysis-selection.spec.ts tests/processing-guidance.spec.ts tests/workflow-pages.spec.ts tests/scene-cards.spec.ts tests/reliability.spec.ts tests/imagery-explorer.spec.ts tests/imagery-layout.spec.ts tests/public-data.spec.ts tests/media-access.spec.ts tests/landsat-preview.spec.ts tests/providers.spec.ts tests/external-access.spec.ts tests/pixel-quality.spec.ts tests/change-analysis.spec.ts tests/cloud-workflow.spec.ts tests/estimate-mode.spec.ts --workers=2 --grep-invert 'LIVE|실제 공개 다중 제공처 검색'
```

전체 frontend 전 파일 E2E를 실행한 것은 아니다. 기존 대용량 원본 전체 확보를 전제로 한 구형 실연결4개는 skip이다. backend28개 skip은 기본 LIVE 게이트 등이며 실연결 실패를 skip으로 바꾸지 않았다. 고정 TIFF 검사에는 문서 scale/offset·공식 예제의 정확한 산술·구름/그림자/fill·0분모·전부 무효·QA 누락·기간/제품/Item/날짜 순서·헤더 상충·사용자 기준/겹친 영역·실제 파일 해시/단위/재열기·작업 소유권을 포함한다.

수정 중 실패를 숨기지 않는다. 첫 단위 검사는 공식 FAQ의 반올림302.6K를 부정확하게 상수화한 기대값1건이 실패했고, 정확한 산술302.62974494K로 고쳤다. 첫 PC 실연결은 QA_PIXEL 헤더 태그 차이에서 차단됐고 문서화된 bit 검사로 수정했다. 한국 해안 ST 실연결은 유효 픽셀이 없어 실패로 유지했다. 초기 UI 회귀는 가상 플랫폼·처리 상한 밖 AOI·이전2필드 Item 키/직접 preview URL·고정 NDVI 범례를 사용한 fixture로 실패/중단했다. 제한/미디어 URL 검증을 풀지 않고 fixture를 현재 계약으로 맞췄다. 마지막 preview 복귀는 lazy loading 조건에 맞게 실제 이미지 영역을 스크롤한 뒤 검증한다. 실패 로그와 중단된 실행은 최종 통과로 합산하지 않는다.

## 실제 공개 픽셀·파일·브라우저

| 실제 표본 | 검사 범위 | 결과 |
|---|---|---|
| ES `S2B_52SBF_20210716_0_L2A` / `S2B_52SBF_20210726_0_L2A`, bbox `[126.7,36.4,126.71,36.41]`, UTC2021-07 | 한 NDVI·MNDWI·NDBI·MNDWI 변화와 기존 NDVI 변화 | 실제 Range·계산·저장·전체 TIFF/manifest 재열기 성공. 단일 지수 유효60.696%, 두 날짜43.896%로 전체AOI와 유효 부분 구분 |
| PC `LC08_L2SP_039035_20250719_02_T1`, bbox `[-115.15,36.16,-115.14,36.17]`, UTC2025-07 | NDVI/MNDWI/NDBI/ST/고온/영역 비교 | 실제 저장/재열기 성공. 광학 유효99.639%, ST71.943%; 광학 성공이 ST 전체 유효를 보증하지 않음 |
| PC `LC08_L2SP_039035_20250703_02_T1`→위07-19, 같은 bbox/플랫폼/L2SP | MNDWI 변화 | 공개 검색에서 두 ID를 확인 후 canonical·공통 유효 픽셀·파일 재열기 성공 |
| PC `LC09_L2SP_116035_20251011_02_T1`, 한국 해안 bbox `[126.7,36.4,126.71,36.41]` | 실제 TIFF 헤더/ST/QA 읽기 | **공통 유효 ST 없음으로 실패**, 평균0/가짜 파일/완료 표시 없음. 별도 육상 표본 성공으로 이 장면을 해결했다고 주장하지 않음 |

실제 PC ST 브라우저 출력: ZIP 전체 **16,341 bytes**, SHA-256 `cac03e65c6db0df6236095909d5b4ec9c8146cde10e2f0d3ca6b89ba37ba8d65`. `temperature.tif`2밴드7,052bytes(K/degC), `temperature_quality.tif`4,182bytes(K/km), `valid_mask.tif`1,344bytes, `exclusion_mask.tif`1,377bytes, manifest. 실제 원본 **Range376,832 bytes/20요청**. 유효 면적718,273.858m²/71.94346%, 면적 가중 평균329.24252K=56.09252℃(이 표본/유효 영역만의 관측값). 검증용 고온20℃/수역0 기준은 명시 테스트 입력이며 앱 기본 보편 임계값이 아니다. 두 영역 이름도 LIVE test west/east로 실제 도시/행정구역 통계라고 하지 않았다.

근거는 `live/*.json`·실제 출력ZIP, `live-browser/result.json`, `artifact-verification.json`, `panel.png`, `frontend/test-results/products-live/**/actual-pc-temperature.zip`. 390px 신설 UI 5개 시나리오와 기존1440/390px 회귀·가로 넘침·새로고침/계획 무효화·필수 밴드 선택을 fixture와 구분해 검사했다.

**실제 제공처 browse/원본 전체 장면 파일 다운로드·QGIS/ArcGIS GUI는 이번 실검증에서 미실행**이다. LIVE 브라우저의 자동 media 요청을 abort했고 유료 AI/Kakao 호출도 차단했다. 저장한 결과 TIFF를 rasterio로 전체 읽기/해시/격자/단위 확인한 것을 GUI 검증이라고 하지 않는다. L9 실제 유효 온도 출력, S2 A/C 실제 표본은 이번 성공 사례에 포함하지 않는다.

## 반영·확인과 남은 범위

사용자가 진행 작업 부재와 검증 후 재시작을 승인했다. 실행 경로/부모·자식이 이 프로젝트 런처임을 확인하고 픽셀 worker가 없는 것을 추가 확인한 뒤 그 트리만 종료, `.\start.cmd`로 숨김 재실행했다. **22:12:00 KST** 웹/백엔드 health ok, `/processing`200, 새 계획의 빈 입력422, 웹 분석 카탈로그 `products-2`·10후보/8지원/2미지원·11방법,5제공처/9컬렉션을 확인했다. 당시8000 PID40756,3000 PID42560이다. `project-restart-before.json`, `project-restart-start.json`, `project-restart-health.json`에 기록했다. 실제 픽셀/브라우저 검증은 앞의 격리3012/8012 결과이며 재시작 후 health를 실제 계산 검증으로 대신하지 않는다.

임시 서버는 종료했고 테스트가 추가한 타입 경로를 제거해 `tsconfig.json`·`next-env.d.ts`를 수정 전 백업과 바이트 단위로 동일하게 복원했다. 다른 편집이 없는지 먼저 검사했으며 복원 뒤 typecheck도0이다. 다른 앱/서버·키/환경 설정은 유지했다. 기존 세션 작업은 재시작 후 자동 재개하지 않으며 원래 보관/만료 계약을 따른다.

재현: 수집에서 **PC Landsat TIRS**·위 네바다 bbox·UTC2025-07-01~31 검색→07-19 위 LC08 장면 선택→세부 분석 선택→지표면 온도 확인→새 공통 패널의 밴드 상세에서 `qa`·`cdist` 추가 확인→QA2K/1km 확인→계획 검사→확인 체크→실행→succeeded/실제 온도 지도→ZIP 다운로드→압축 해제 후 TIFF/manifest 재열기. 원본 전체 수신0이어도 서버가 canonical Asset을 직접 읽으며 원본 전체 다운로드 완료로 표시하지 않는다.

HLS/VIIRS/SAR/PC S2 처리, 침수 확정·피복 변화 분류, 도시 전체/약1,100km² 서울 bbox·50km² 초과 처리, 다중 worker/영속 큐·재시작 작업 재개·로컬 TIFF 업로드는 남은 범위다. 새 지수/ST 상한은50km²/150,000셀·제품별20/30m 고정 격자이며, 기존 합성/ML25km²와 공통 전송/시간/파일/소유권 제한을 유지한다. 작은 실표본 성공을 모든 장면·최대 면적의 성능 보장으로 일반화하지 않는다. 원문/AOI/기간을 몰래 바꾸지 않고 미확인/부적합/무효는 실행 차단 또는 실패로 남긴다.

---

# 공통 실제 픽셀 처리 기반 — 2026-11-03 21:04 KST

이번 기록은 아래 과거 기록과 별개의 최신 수정/실행 결과다. 새 앱·온도/SAR 등 새 계산 엔진·인증 설정을 추가하지 않았다. `.git`이 없는 작업 폴더에서 수정 전 소스 경로·SHA-256·UTC 수정 시각을 `test-results/foundation-20261103-200942/before-files.json`에 기록하고 대상 원본을 `backup/`에 보관했다. 기존 `.env`/키/운영자 정책 플래그는 읽어 출력하거나 수정하지 않았다.

## 구현과 실제 지원 범위

- 백엔드 분석 카탈로그를 `processing_contract_version=foundation-1`로 확장했다. 10개 세부 후보의 실제 분석 지원은 여전히 **식생 두 날짜 NDVI 변화만**이다. 각 분석의 실제 처리 방법/제공처/제품/필수 변수·QA/시점/기간/공간/산출물/미지원 이유를 서버 계약으로 반환한다. 프런트가 독립적인 제품 지원 규칙을 추가하지 않는다.
- 새 `/processing/plans` → 사용자 확인 → `/processing/jobs` → 상태/취소/바이너리 ZIP 경로가 canonical Item/Asset·허용 기간·제품·밴드·QA·확정 ROI를 재검사한다. 브라우저 원본 수신 기록은 입력/증거로 사용하지 않는다. 기존 원본 수신·구형 엔진/UI 게이트는 호환 경로에 남는다.
- 기존 Earth Search S2 공개 COG 엔진을 재사용한다. 공통 QA/NDVI는 한 LAEA20m 격자·최대50km²/150,000셀/160×160셀 타일16개로 제한하며 실제 polygon 클리핑을 지원한다. 기존 합성/국소 ML은25km²·31일·bbox로 유지한다. 기존 과학 계산을 새 엔진으로 복제하지 않았다.
- 실제 TIFF/마스크/manifest를 비공개 디스크에 저장하고 CRS·transform·크기·밴드·자료형·단위·NoData·전체 읽기·해시·ZIP 무결성을 확인한 뒤 게시한다. 실제 배열만 기존 지도 레이어에 연결한다. 실패는 null/미확인이며 실제 전 영역 구름 검사0%와 구분한다. 관측/합성/ML 추정은 원래 출처일·픽셀 상태와 엔진 기록을 유지한다.
- 작업은 기존 HttpOnly 소유권/Origin 검사·idempotency·cancel·75초 자식 프로세스 상한·15분 보관을 사용한다. **로컬 단일 worker 전용, 재시작 후 작업 재개/공유 영속 큐는 미구현**이다. 복원된 작업 ID는 GET만 재조회하며 조건 불일치 결과를 새 지도에 적용하지 않는다.
- 범위 입력64MiB/128요청(PC SAS 예약 포함), 원격 요청8초/Range60초, ZIP16MiB/해제32MiB/디스크256MiB, 동시 픽셀1·다운로드2, 시간당 소유자/전체512MiB 제한을 적용한다. 실패한 입력 예약을 무제한 환불하지 않는다. OS 수준 메모리 격리를 구현했다고 주장하지 않는다.
- PC 익명 SAS 범위 읽기 어댑터는 mock만 검증했다. **PC/Landsat/HLS/VIIRS/Sentinel-1의 새 픽셀 엔진은 활성화하지 않았고, NASA/USGS/CDSE 인증을 공통 범위 읽기에 섞지 않았다.** 기존 공개 제공처 미디어/다운로드 회귀는 fixture로 검사했다.

## 실제 변경 파일과 역할

모든 경로는 `C:\Users\aicam\Documents\ChatGPT\바이브코딩\` 아래다.

| 파일 | 역할 |
|---|---|
| `backend/app/analysis_catalog.py` | 분석별 실행 지원/방법/산출물 스펙의 단일 서버 계약 |
| `backend/app/processing_models.py` (신규) | 명시 처리 입력/ROI 출처·polygon·기간·선택·QA 버전 검증 |
| `backend/app/processing.py` (신규) | canonical 계획/재검사·작업·소유권·취소·중복/사용량·파일 전달 |
| `backend/app/processing_raster.py` (신규) | 고정 전역 격자/제한 타일/실제 polygon·면적 분모 |
| `backend/app/raster_source.py` (신규) | 제공처별 공개 COG/PC 익명 SAS 범위 읽기 분리·목적지 검사 |
| `backend/app/processing_worker.py` (신규) | 기존 A3/A4/합성/ML 호출·실제 지도·공통 산출물 연결 |
| `backend/app/artifact_store.py` (신규) | 비공개 파일·TTL/공간 상한·원자적 게시·재열기/해시/ZIP 검증 |
| `backend/app/pixel_quality.py` | 기존 검사 전 canonical 준비 함수 분리, 구형 기본 계약 유지 |
| `backend/app/pixel_raster.py` | 선택적 고정 격자/내부 타일 캡처, 기본25km² 유지 |
| `backend/app/change_analysis.py` | 실제 타일 결과 재사용·공통 출력 한도·마스크 단위 태그 |
| `backend/app/cloud_composite.py` | 기존 TIFF의 단위 태그를 원래 해시 생성 전에 기록(ML 공용 helper 포함) |
| `backend/app/range_reader.py` | 서버 전용 제공처 validator 주입, 기존 공개 S2 기본 정책 유지 |
| `backend/app/main.py` | 공통 계획·작업·취소·다운로드 API 연결 |
| `frontend/src/components/ProcessingExecution.tsx` (신규) | 카탈로그 기반 계획/확인/작업/전체 ZIP·해시 확인, 오래된 응답 폐기 |
| `frontend/src/components/WorkflowWorkspace.tsx` | 같은 Workspace의 장면/비교 쌍/밴드/AOI/작업 ID와 실제 지도 결과 연결 |
| `frontend/src/lib/analysisFlow.ts`, `types.ts` | 서버 실행 계약을 읽는 표시/사전 검사와 타입 |
| `frontend/src/app/globals.css` | 새 패널만 읽기/최소 버튼 크기·줄바꿈 보완, 기존 디자인 유지 |
| `backend/tests/test_processing_foundation.py` (신규) | 실제 로컬 TIFF 계산/타일/QA/산출물·경계 신뢰/소유권/취소/제한/보안 검사 |
| `backend/tests/create_processing_ui_fixture.py` (신규) | tests 전용 실제 TIFF/ZIP 생성, 서비스 fallback 없음 |
| `backend/tests/test_processing_live.py` (신규) | 명시 LIVE 플래그에서 공개 canonical/Range/ZIP 재열기 |
| `frontend/tests/processing-foundation.spec.ts` (신규) | 1440/390px·단일 상태 전달·확인·ZIP 전체 수신/재열기·복원/경합/오류 |
| `frontend/tests/processing-foundation-live.spec.ts` (신규) | 실제 검색→canonical 픽셀→지도 상태→브라우저 ZIP 저장/재열기 |
| `frontend/tests/analysis-selection.spec.ts` | 독립 엔진 목록 대신 실제 서버 실행 계약으로 검사 |
| `docs/PROCESSING_FOUNDATION.md` (신규), `README.md`, `docs/WORKFLOW_PAGES.md`, `docs/ANALYSIS_SELECTION.md`, `TEST_REPORT.md` | 현재 계약/사용 순서/제한/실행 근거 |

Next dev/build가 추가한 `.next-foundation-dev` 타입 경로는 검증 서버 종료 뒤 제거했다. 기존 `.next-conditions*` 등 사용자 설정은 보존했고 `next-env.d.ts`는 실행 중인 기존 `.next/dev` 타입 참조로 복원했다. 생성 설정 복원 후에도 독립 typecheck를 다시 통과했다. 의존성·키·환경변수·이용조건 플래그·배포/push 변경은 없다.

## 실제 실행 결과 (KST, 최신 수정 기준)

명령/로그/종료 코드 JSON은 모두 `test-results/foundation-20261103-200942/`에 있다. 과거 통과 건수를 재사용하지 않았다.

| 실행 | 시각 | 종료 코드·결과 | 증거 |
|---|---|---|---|
| backend `..\.venv\Scripts\python.exe -m pytest -q --durations=5` | 20:59:29–21:01:12 | **0 ·551 passed/17 skipped**,100.92초 | `pytest-final2.log`, `pytest-final2-result.json` |
| frontend `npm.cmd run typecheck` | 20:48:27–20:48:30 | **0** | `typecheck-final*` |
| 생성 타입 복원 후 동일 독립 typecheck | 21:03경, 정확한 시각 JSON | **0** | `typecheck-restored*` |
| `node ../test-results/foundation-20261103-200942/build-check.mjs` → `next build --webpack` | 20:52:40–20:53:45 | **0**, `/`·`/processing` production build | `build-final*` |
| 관련 E2E16개 파일, 아래 명령 | 20:54:04–21:00:25 | **0 ·98 passed/4 skipped**,6.3분 | `e2e-final*` |
| `LIVE_STAC=1 LIVE_PROCESSING=1 npx playwright test tests/processing-foundation-live.spec.ts --workers=1` | 21:00:56–21:01:17 | **0 ·1 passed**,19.5초 | `live-browser-final*`, `live-browser/result.json` |
| API 직접 실제 공개 COG 검사 `LIVE_STAC=1 LIVE_PROCESSING=1 ...pytest -q tests/test_processing_live.py` | 20:35:19–20:35:33 | **0 ·1 passed**, 단위 태그 강화 전의 중간 실행 | `live-first*`, `live/result.json` (최종 완료 근거는 위 브라우저 재실행) |

production build는 `frontendEnvironment`로 비밀을 제거하고 `.next-foundation-build` 별도 dist를 사용했다. 임시 dev도 `.env`를 읽지 않는3011/8011, AI/지명/운영자 접근 비활성 환경이었다. build가 수정한 타입 설정은 즉시 복원했다. 타입/빌드 검사로 인증/외부 파일 성공을 주장하지 않는다.

관련 E2E 실제 명령(frontend cwd):

```powershell
$env:E2E_BASE_URL='http://127.0.0.1:3011'
$env:E2E_API_BASE_URL='http://127.0.0.1:8011'
$env:E2E_OUTPUT_DIR='test-results/foundation-final'
# LIVE_STAC/LIVE_PROCESSING 제거 후 fixture 회귀
npx.cmd playwright test tests/processing-foundation.spec.ts tests/analysis-selection.spec.ts tests/processing-guidance.spec.ts tests/workflow-pages.spec.ts tests/scene-cards.spec.ts tests/reliability.spec.ts tests/imagery-explorer.spec.ts tests/public-data.spec.ts tests/media-access.spec.ts tests/landsat-preview.spec.ts tests/providers.spec.ts tests/external-access.spec.ts tests/pixel-quality.spec.ts tests/change-analysis.spec.ts tests/cloud-workflow.spec.ts tests/estimate-mode.spec.ts --workers=1 --grep-invert 'LIVE|実際|실제 공개 다중 제공처 검색'
```

전체 frontend E2E 전 파일을 실행한 것은 아니다. 관련16개 파일에서 검색 부분 실패/0건·지도/날짜/비교·밴드 선택·PC/NOAA 공개 파일/USGS 제한·Landsat PC 대응 미리보기·만료/재시도·원본 수신과 링크 목록 구분·기존 A3/A4/합성/ML·모바일/복원/오래된 응답을 검사했다. 4개 skip은 기존 대용량 원본 확보를 전제로 한 구형 실연결 시나리오이며 새 공개 공통 경로 실검증과 별개다. backend17개 skip도 기본 실연결 게이트를 유지한 결과다. 1,795개 warning(주로 NumPy/rasterio 및 기존 의존성 deprecation)은 남아 있으며 오류로 숨기지 않았다.

중간 실패도 보존한다: `foundation-second.log`는 PC mock이 이미 소비된 httpx 본문을 반환해1실패→fixture를 실제 stream으로 수정했다. 첫 typecheck/E2E의 새 테스트 중괄호 문법 오류, fixture 생성기의 app import 경로, 이전 카탈로그 기대값 불일치는 수정 후 재실행했다. 중간 E2E 한 번은 소스 hot reload 중 AI 화면 안정화 timeout이 있었고 재실행 통과했다. **첫 실제 브라우저 실행은 NDVI `valid_mask.tif`의 unit 누락을 새 엄격 검증이 발견해 failed로 중단했다**(`live-browser.log`). 검증을 완화하지 않고 원래 TIFF writer에서 unit을 해시 생성 전에 기록해 최종 브라우저 전체 수신/재열기를 통과했다. 첫 build wrapper의 PowerShell quoting 오류는 파일 기반 wrapper로 수정했다. 중간 실패를 최신 성공 근거로 쓰지 않는다.

## 실제 공개 API·브라우저·파일 내용 검증

최종 실연결은 실제 검색에서 반환된14건 중 아래 두 canonical Item을 명시 선택했다. 다른 장면으로 대체하거나 fixture를 서비스 응답으로 사용하지 않았다.

- 제공처/제품: Earth Search / Sentinel-2B L2A, `sentinel-2-l2a`.
- Item: `S2B_52SBF_20210716_0_L2A`, `S2B_52SBF_20210726_0_L2A`.
- UTC 허용 기간2021-07-01–07-31, bbox `[126.7,36.4,126.71,36.41]`, 식생→두 날짜 NDVI 변화, 적색/근적외선/SCL.
- 실제 입력 Range **6,373,376 bytes /22요청**, 격자 타일1개. AOI면적995,374.394m², 실제 분석 유효영역436,928.949m²/전체AOI43.89594%. 이는 장면 전체 구름량/기하 중첩과 다르다.
- 실제 출력 ZIP 전체 **26,390 bytes**, SHA-256 `2b85fae41ccb945508c92b8c7b0e3ba4177191c2c530614c25842ea3e6d25a77`. `ndvi_change.tif`3밴드17,337bytes, `valid_mask.tif`1,696bytes, `exclusion_mask.tif`1,503bytes, `processing.json`, `manifest.json` 포함. 모든 TIFF의 unit=1·CRS/NoData·실제 배열 읽기·manifest 파일별 해시를 재확인했다.
- 실제 브라우저 검색/계획/확인/작업 succeeded·기존 지도 `실제 NDVI` 레이어 상태·ZIP 전체 수신/브라우저 다운로드 파일 저장/저장 파일 rasterio 재열기 성공. `live-browser/artifact-verification.json`, `live-browser/panel.png`, `frontend/test-results/foundation-live-final/**/actual-public-processing.zip`에 근거를 남겼다.
- **실제 제공처 browse/원본 전체 장면 다운로드는 이 실연결 테스트에서 제외**했다. 자동 미디어 요청을 abort하여 별도 제공처 전송을 하지 않았다. QGIS/ArcGIS GUI에서 열기·사용자 PC의 기존 다운로드 파일 확인도 미실행이다. rasterio GIS 파일 재열기와 GUI 검증을 혼동하지 않는다.
- 1440/390px 새 패널 screenshot은 `screenshots/foundation-1440.png`, `foundation-390.png`이며 시각 확인했다. 모바일 가로 넘침이 없고 동일 영상/확인/다운로드 컨트롤이 표시된다. 해당 두 화면의 ZIP/픽셀은 테스트 로컬 TIFF fixture로 실연결 표본과 구분된다.
- 약49km² 로컬 TIFF fixture에서 같은 전역 격자의 타일/비타일 수치·마스크 일치와 polygon 부분면적을 확인했다. 최신 큰 테스트는56.49초(복수 계산 합계)다. **50km² 실장면 전송/시간 보장·도시 규모 분산 처리를 검증하지 않았다.**

## 현재 사이트 반영과 재현

사용자가 진행 작업 부재와 재시작을 승인했다. 3000/8000의 부모/자식·실행 경로가 이 프로젝트 `scripts/start-local.mjs`임을 확인한 뒤 그 트리만 종료하고 루트 **`.\start.cmd`**로 숨김 실행했다. 임시3011/8011도 검증 뒤 종료했다. 키/환경/인증 플래그는 변경하지 않았다.

21:02:54 KST 웹/백엔드 health ok, `/processing`200, 웹 `/api/analysis/catalog`는 `foundation-1`·4개 방법·10개 분석 후보, `/api/catalog`는5개 제공처/9개 컬렉션이었다. 새 `/api/processing/plans`의 빈 입력은404가 아니라422로 검증 거절했다. 서버 PID8000=51344,3000=51548(당시). 근거 `project-restart-before.json`, `project-restart-start.json`, `project-restart-health.json`.

확인 순서: http://127.0.0.1:3000 → 직접 입력 식생/위 UTC 기간/bbox → Earth Search S2 검색 → 위 두 장면/필수 밴드 선택 → `세부 분석 선택으로` → `시기별 식생 변화` 확인 → 새 공통 패널에서 두 날짜 확인 → `공통 처리 계획 검사` → 조건 확인 체크 → `확인한 계획 실행` → succeeded/실제 NDVI 지도 → `검증된 처리 ZIP 다운로드` → 압축 해제 후 GIS에서 TIFF/마스크를 열고 manifest와 비교한다. 자동 AI/검색/다운로드/ML 실행은 추가하지 않았다.

## 남은 제한

- PC 범위 어댑터 실연결·PC/SAR/HLS/Landsat/VIIRS 픽셀 분석은 미검증/미구현이며 실행 게이트를 열지 않았다. NASA/USGS/CDSE 기존 인증/HLS400 문제는 이번 기반에서 해결했다고 주장하지 않는다.
- 서울 약1,100km² bbox·도시 전체/등록 서울 경계 처리, 대규모 분할/공유 큐·다중 worker·서버 재시작 작업 재개, 로컬 파일 업로드는 미구현이다. 초과 시 사용자에게 축소를 안내하며 AOI/기간을 몰래 바꾸지 않는다.
- 파일 접근/권한/QA·보정 실패는 미확인으로 중단한다. 관측 합성과 ML은 기존 검증 게이트를 유지하며 추정의 구름 아래 참값 정확도를 보장하지 않는다. 원본은 덮어쓰지 않는다.
- 작업/결과는15분 보관이고 단일 프로세스 소유권이다. 공개 다중 사용자 영속 운영이 준비됐다는 뜻이 아니다. 비밀키 설정 변경·유료 AI·대용량 일괄 다운로드·배포/push는 수행하지 않았다.

---

# 이번 후속 점검: Sentinel-1 원본 다운로드 활성 조건 — 2026-11-03 17:00 KST

## 실제 원인·변경

- 사용자 화면의 공개 Item `S1A_IW_GRDH_1SDV_20250817T093217_20250817T093243_060574_0788C1_8F3F_COG`를 CDSE STAC에서 다시 확인했다. Product ZIP **1,177,053,605 bytes**, VV **627,835,581 bytes**, VH **541,730,379 bytes**다. 기존 파일당256 MiB·사용자512 MiB/시간·운영자1 GiB/시간 제한으로 실제 원본 세 파일이 모두 막혔다. 작은 자동 미리보기 두 건이 전송 슬롯을 사용하면 명시 원본 검사도 즉시 `busy`가 됐다.
- CDSE Sentinel-1만 파일당2 GiB, 시간당 사용자/운영자3 GiB, 제공처 수신20분·브라우저 전달5분으로 제한을 분리했다. 전체 원본은 서버 임시 spool을 거쳐 Chrome/Edge 파일 저장 스트림에 쓴다. 사용자 저장 파일 완료는 스트림 닫힘 후에만 기록한다. Range1024 검사는 버튼 활성 조건이며 전체 수신 완료가 아니다. 명시 원본 검사는 바쁜 슬롯을 최대12초 기다린다. 다른 제품 상한은 유지했다.
- 공식 [Sentinel 데이터 고지](https://cds.climate.copernicus.eu/licences/ec-sentinel)의 배포·출처 조항과 [CDSE 약관](https://dataspace.copernicus.eu/terms-and-conditions)의 Sentinel/기타 포털 자료 구분을 확인해 Sentinel-1 카드에 `Copernicus Sentinel data [Year]`를 표시했다. 로컬 `backend/.env`에는 누락됐던 `OPERATOR_CDSE_ENABLED=1`, `OPERATOR_CDSE_REDISTRIBUTION_REVIEWED=1`만 설정했다. 기존 사용자명·비밀번호 값은 수정/출력하지 않았다. 공개 배포는 하지 않았다.
- **실제 인증 실패는 남음:** 현재 실행 서버의 제공처 상태는 여전히 `public_catalog_only`(서버 재시작 전 환경)였다. 갱신된 설정을 별도 프로세스에 로드해 정확한 Item의 Product 1 KiB 접근을 시도했으나 `operator_reconnection_required`/receipt 없음이었다. 공식 CDSE `cdse-public` password grant를 별도로 최소 진단했을 때 HTTP **400 `invalid_grant`**, access/refresh token 없음이었다. 사용자명·비밀번호의 앞뒤 공백/명백한 예시값은 없었다. 계정 정보 오류인지 2FA 필요한 계정인지는 이 코드만으로 확정하지 않는다. **실제 원본 파일 전체 다운로드·ZIP/TIFF 재열기는 미실행/미완료이며 버튼을 강제로 활성화하지 않았다.** 실패 세대는 암호화 운영자 저장소에서 `reconnection_required`로 보존된다.

변경: `backend/app/provider_transfer.py`, `media_access.py`, `operator_store.py`, `operator_access.py`, `backend/tests/test_operator_access.py`, `frontend/src/lib/providerPreviewQueue.ts`, `frontend/src/components/ManagedAssetAccess.tsx`, `ProviderPreview.tsx`, `frontend/next.config.ts`, `frontend/tests/media-access.spec.ts`, `backend/.env`(활성/검토 플래그만), `README.md`, `docs/OPERATOR_DATA_ACCESS.md`, 이 보고서. 빌드가 자동 추가한 임시 TypeScript include는 `frontend/tsconfig.json`에서 제거했다. 토큰/비밀번호·서명 URL은 로그/보고서에 남기지 않았다.

## 최신 실제 실행 (2026-11-03 KST)

| 검사 | 종료 코드 | 결과 |
|---|---:|---|
| 백엔드 `python -m pytest tests/test_media_access.py tests/test_operator_access.py -q` | 0 | **56 passed**. 1.18 GB 선언 Range의 1 KiB 테스트 전용 응답으로 receipt/미완료 구분 확인 |
| 백엔드 `python -m pytest -q` | 0 | **518 passed, 16 skipped**. LIVE 제공처 검사는 기본 비활성 |
| 프런트 `npm.cmd run typecheck` | 0 | 독립 TS 검사 통과 |
| 프런트 `NEXT_DIST_DIR=.next-download-build2 npm.cmd run build` | 0 | Next.js production build에서 `/`, `/processing` 생성 |
| 프런트 `npm.cmd run test:e2e -- tests/media-access.spec.ts --grep "Sentinel-1 대용량"` | 0 | **1 passed**, 테스트 전용 저장 스트림·버튼·바이트 검증 |
| 프런트 `npm.cmd run test:e2e -- tests/media-access.spec.ts tests/operator-access.spec.ts tests/workflow-pages.spec.ts` | 0 | **29 passed, 2 LIVE skipped**, 기존 원본/링크/처리 흐름 회귀 포함 |
| 실제 CDSE 공개 STAC 검색 | 0 | HTTP200, 정확한 Item·세 원본 크기 확인. 파일 수신과 별개 |
| 실제 CDSE password grant/원본 1 KiB 검사 | 0(진단 실행) | 인증 HTTP400 `invalid_grant`; 원본 검사 `operator_reconnection_required`, receipt 없음. **실패** |

수정 중 첫 백엔드 회귀는 기본 인자에 기존 타임아웃 상수가 고정돼 1건 실패(54 passed/1 failed)했고 수정 후 56/518건이 통과했다. 첫 TS 재실행은 테스트 타입 1건으로 종료1, 수정 후 종료0. 첫 build는 샌드박스 Fonts DNS/디렉터리 권한으로 종료1, 별도 격리 디렉터리의 승인된 재실행은 종료0. 첫 Sentinel-1 E2E는 fixture 응답 기간이 요청 기간 밖이라 장면 카드가 제거되어 종료1; fixture 기간을 맞춘 재실행은 종료0. 실패 실행을 성공 근거로 합산하지 않는다.

최종 코드에서 제공처 수신20분·브라우저 전달5분을 분리하고 프록시/브라우저 전체 제한을26분으로 맞춘 뒤의 재확인: `python -m compileall -q app` 종료0, `npm.cmd run typecheck` 종료0. 전체 pytest 재실행은 자동 승인 검토가 원 요청·허용된 재시도 모두 기한 내 끝나지 않아 **미실행**(코드 실패 판정 아님). 기본 샌드박스 build 재실행은 컴파일/TypeScript까지 성공했으나 `/_not-found` 페이지 생성의 `EPERM`으로 종료1. 앞 표의 518건·production build·29건 E2E 통과는 이 마지막 시간 상한 수정 **직전**의 결과이며 최종 코드에 대한 재실행 통과로 주장하지 않는다. 최근 user 입력 후에도 `backend/.env` 수정 시각은16:41, `OPERATOR_CDSE_REVISION`은 미설정(기본1), refresh token도 미설정으로 확인됐다. 실행 서버는 재시작하지 않았다.

## 남은 조치

운영자가 [CDSE 공식 토큰 절차](https://documentation.dataspace.copernicus.eu/APIs/Token.html)에 따라 계정을 확인해야 한다. 서버 전용 `backend/.env`의 비밀번호를 바로잡거나 공식 2FA 절차에서 얻은 refresh token을 설정하고 `OPERATOR_CDSE_REVISION`을 현재 값보다 높인 뒤 로컬 서버를 재시작한다. 비밀값을 채팅에 보내지 않는다. 그 후 이 Item의 Product 또는 VV/VH 한 파일을 다시 Range 검사해 `available`/크기를 확인하고, 사용자가 명시 다운로드하여 **실제 전체 파일 저장·ZIP/TIFF 재열기**까지 검증해야 한다. 현재 조건에서는 원본 다운로드 완료라고 보고하지 않는다. 수신20분/브라우저 전달5분/3 GiB 상한·임시 디스크·Chrome/Edge 저장 기능·계정 쿼터가 남은 운영 제한이다.

---

# 이번 Phase: 검색 결과 카드 정보 순서·선택·미리보기 — 2026-11-03

이번 범위는 기존 검색 결과 카드의 표시/선택 경험과 관련 UI 회귀 검증이다. 기존 디자인·목적별 추천 규칙·검색·선택/날짜/지도·밴드·파일 수신·분석 엔진을 재사용했다. 백엔드/API/공통 Scene 타입·인증/키/환경/이용조건 설정 변경, 새 분석 엔진·가짜 운영 미리보기·유료 AI·배포/push·서버 재시작은 없다. 이번 Phase만 검증하고 종료한다. 아래 과거 Phase 통과 수를 이번 코드의 검증 근거로 합산하지 않는다.

## 원인과 수정

- 기존 카드 앞부분에 작은 미리보기와 많은 메타데이터/밴드가 함께 노출되어 핵심 촬영 정보·추천 근거·처리 지원을 먼저 파악하기 어려웠다. 첫 주요 카드 밴드도 자동으로 펼쳐졌다. 촬영일(UTC) → 위성/제품·제공처 → 기존 추천 근거·앱 처리/원본 접근 → 지도 선택 → 큰 제공처 이미지 → 독립 품질 정보 순서로 바꿨다. 촬영/제품 상세·밴드·Item ID는 접어서 보존한다.
- 구름량은 장면 메타데이터, 중첩은 기하 값, 실제 AOI QA는 검사 상태로 각각 표시한다. 누락 수치를 만들지 않는다. PC S2의 센서 적합성과 현재 앱 S2 픽셀 엔진 미지원은 선택 전에 명시한다. 미리보기와 원본 밴드·분석/QA 결과는 별개다.
- 밴드 추천 기본값·전체 선택/해제/추천 복원·명시 원본 접근 확인/다운로드·링크.txt 저장을 기존 상태/API로 유지한다. 접근 확인을 전체 파일 수신 완료로 바꾸지 않는다.
- PC 등 픽셀 처리 미지원 제품도 수집 화면에서 기존 두 장면 비교를 이용할 수 있도록 접힌 메타데이터 비교를 추가했다. 기존 pair/compareMode를 공유하며 새 엔진/비교 상태를 만들지 않았다. 수집 비교에서는 A2/A3/A4 실행을 노출하지 않고 처리 페이지의 기존 실행 경로는 유지한다.
- 큰 카드 캡처 회귀에서 화면 밖으로 이동한 미리보기 img를 제거하던 기존 조건이 이미지 높이와 표시를 바꾸는 것을 확인했다. 이미 확인·수신한 이미지는 스크롤 중 유지한다. 최초 조회는 계속 가시 영역에서만 하며 명시 숨기기·인증 변경·실패/만료 복구·오래된 응답 차단을 재사용한다. 화면 밖에서 다운로드/픽셀 처리를 자동 시작하지 않는다.
- 결과 그리드는 실제 `.results` 하위 wrapper 구조에 맞춰 최소340px 반응형 열을 적용했다. 글자14–21px, 버튼/summary 최소44px, 고정 체크박스와 focus 표시 등 결과 영역 전용 스타일로 기존 입력 화면을 보존한다. 미리보기 이미지는 높이260px/contain으로 자르지 않는다.

## 변경한 실제 파일

| 경로 | 역할 |
|---|---|
| `frontend/src/components/Results.tsx` | 카드 정보 계층·UTC 날짜·처리 지원·큰 제공처 이미지·독립 품질·접힌 상세/밴드/ID, 기존 선택 callback 재사용 |
| `frontend/src/components/SceneProvenance.tsx` | 기존 원본 접근 문구를 공유 helper로 재사용. 실제 파일 접근 성공을 추정하지 않음 |
| `frontend/src/components/ProviderPreview.tsx` | 이미 수신한 이미지의 스크롤 유지·미리보기 대체 텍스트. 기존 인증/수신/제한 경로 유지 |
| `frontend/src/components/SceneComparison.tsx` | metadataOnly 표시 옵션·수집 비교용 고유 label/ID, 기존 처리 UI/상태 유지 |
| `frontend/src/components/WorkflowWorkspace.tsx` | 기존 비교 pair를 사용하는 수집 화면의 접힌 두 장면 메타데이터 비교 |
| `frontend/src/app/globals.css` | 결과 카드/수집 비교 범위만 크기·대비·그리드·모바일/포커스 보완 |
| `frontend/tests/scene-cards.spec.ts` | 신규7개 fixture 검사와 별도 opt-in LIVE1개 |
| `frontend/tests/runtime.ts` | 밴드/수집 비교를 명시적으로 펼치는 E2E helper |
| `frontend/tests/reliability.spec.ts`, `external-access.spec.ts`, `imagery-explorer.spec.ts`, `providers.spec.ts`, `workflow-pages.spec.ts`, `media-access.spec.ts` | 접힌 밴드와 수집 메타데이터 비교의 기존 회귀 검사 갱신 |
| `frontend/tests/search.spec.ts` | 밴드 영역 명시 펼침. 이번 파일 자체의 네트워크 E2E는 미실행, typecheck 대상에 포함 |
| `README.md`, `docs/WORKFLOW_PAGES.md`, `TEST_REPORT.md` | 표시/공유 상태 계약·실제 검증/한계 기록 |

`AssetDownloads.tsx`, `MapPanel.tsx`, 공통 Scene/API 타입·백엔드/처리 엔진은 읽고 기존 것을 그대로 사용했다. 환경 파일/사용자 자격증명과 이전 입력·처리 Phase 변경을 유지했다.

## 최신 코드 실제 실행 (2026-11-03 KST)

최종 기능 코드 변경은16:02의 ProviderPreview 스크롤 유지다. 아래 최종 검사는 그 이후이며 빌드와 E2E/LIVE를 순차 실행했다.

| 시각 | 실제 명령·범위 | 종료 코드 | 결과 |
|---|---|---:|---|
|16:07:00–16:07:03|frontend `npm.cmd run typecheck` (`tsc --noEmit`)|0|독립 타입 검사 통과|
|16:07:13–16:07:48|Node 격리 래퍼 안의 `node node_modules/next/dist/bin/next build --webpack`|0|production build, `/`·`/processing` 생성 성공|
|16:07:58–16:13:50|아래 fixture E2E 명령·10개 파일|0|**68 passed (5.8m)**|
|16:14:00–16:14:21|아래 LIVE PC 카드 명령|0|**1 passed (19.6s)**. 실제 검색·실제 제공처 PNG 전체 수신/브라우저 디코딩·1440/390px 캡처|
|16:10경/16:14 이후|로컬 실제 `live-preview.png`를 `rasterio.open(...).read()`로 전체 디코딩|0|PNG·1024×1024·4채널,2,190,270바이트. 최신 확인 시각은 `live-decode.json`|
|16:10경|웹3000 및 백엔드8000/health 읽기 전용 GET|0|각 HTTP200. 검색/다운로드 완료의 증거로 사용하지 않음|

빌드는 `scripts/server-env.mjs`의 `frontendEnvironment`로 서버 비밀 환경을 제외하고 `NEXT_DIST_DIR=.next-scene-cards`, `API_BASE_URL=http://127.0.0.1:8000`만 지정한 기존 Node 래퍼에서 수행했다. `next-env.d.ts`/`tsconfig.json` 원래 내용을 보관·복원해 개발 서버/사용자 설정을 유지했다. 실제 종료 코드/시각/출력은 `test-results/scene-cards/final-{typecheck,build,e2e,live}-result.json` 및 같은 이름 `.log`에 있다. PowerShell이 Node의 NO_COLOR 경고를 NativeCommandError 형식으로 기록하지만 위 종료 코드/Playwright 결과는0이다.

```powershell
# frontend에서 실행, 위 실제 서버만 사용. 테스트 runtime은 OpenAI/Kakao 외부 호출을 차단.
$env:E2E_BASE_URL='http://127.0.0.1:3000'
$env:E2E_API_BASE_URL='http://127.0.0.1:8000'
$env:E2E_OUTPUT_DIR='test-results-scene-cards-verified'
npx.cmd playwright test tests/scene-cards.spec.ts tests/reliability.spec.ts tests/imagery-explorer.spec.ts tests/public-data.spec.ts tests/media-access.spec.ts tests/landsat-preview.spec.ts tests/providers.spec.ts tests/workflow-pages.spec.ts tests/processing-guidance.spec.ts tests/external-access.spec.ts --grep-invert 'LIVE|실제 공개 다중 제공처 검색' --timeout=45000 --workers=2

# 위 검사 종료 후 별도 실제 공개 검색/미리보기, 실제 원본 파일 수신 없음
$env:E2E_OUTPUT_DIR='test-results-scene-cards-live-verified'
$env:LIVE_STAC='1'
$env:LIVE_SCENE_CARDS='1'
npx.cmd playwright test tests/scene-cards.spec.ts --grep 'LIVE PC Sentinel' --timeout=120000 --workers=1
```

68개 검사는 새 PC 카드/기본 밴드/전체 선택·해제·복원, 목록↔지도·UTC 날짜, 수집/처리 비교, 원본 접근 확인/모의 전체 수신/링크 목록, 미리보기 없음·부분 장애·인증/만료·선택 변경·응답 순서, 뒤로/새로고침·중복 실행 방지·기존 미지원/지원 처리 안내를 포함한다. fixture 이미지/바이트는 tests의 TEST ONLY 자료이며 서비스 실패 시 대체 자료로 사용하지 않는다. 모의 TIFF/ZIP의 수신 성공은 실제 제공처 원본/분석의 성공이 아니다. Edge headless 실제 브라우저 자동화로1440px·390px 카드/버튼/접힌 밴드/가로 넘침·Enter 선택을 검사했다. 운영체제 저장 위치의 파일 현존이나 접근성 전체 인증은 검증하지 않았다.

### 수정 과정의 실패/재실행 (최종 통과와 구분)

-15:39 독립 typecheck 종료2: external-access 테스트의 새 helper import 누락. import 수정 후15:42 및 최종16:07 종료0.
-15:45–15:48 관련 fixture67개 종료0. 그 뒤 그리드/표시 및 스크롤 검증을 추가했으므로 최종68개 근거로 대체했다.
-15:46 LIVE 종료1: 검색200/2건 후 미리보기 수신 대기의 기본5초 assertion 만료. 실제 제공처 실패로 단정하지 않고 LIVE 표시 대기를60초로 분리했다.15:49 LIVE1개 종료0으로 전체 PNG 수신 확인.
-15:55–16:01 fixture 재실행 종료1:66통과/1실패. reliability 비교 검사에서 로컬 `/request/interpret` route.fetch의 socket hang up(ECONNRESET). 원인을 앱 기능 오류로 단정하지 않았고 POST를 숨겨 재시도하는 코드는 넣지 않았다. 최종 빌드/fixture/LIVE를 순차 실행해 같은 검사를 포함한68개가 통과했다.
-15:55 LIVE 재실행 종료1: 실제 검색/PNG 전체 수신·디코딩 후 캡처/스크롤 중 img 가시성 검사 실패. 화면 밖 img 제거 조건을 바로잡고 새 fixture 스크롤/숨기기 검사를 추가했다. 최신 코드 LIVE는16:14 종료0.
- 마지막 빌드/타입 출력 일부가 도구 결과 한도에 가려졌던 실행은 최종 근거로 쓰지 않고, 위16:07 로그/종료 코드를 남긴 검사로 확인했다.

## 실제 공개 제공처 검증 (fixture와 별도)

수동 날짜/좌표·목적 직접 선택으로 유료 AI를 호출하지 않고 브라우저에서 검색했다. 조건: 식생, UTC **2025-07-20~2025-07-26**, bbox **[126.7,36.4,126.71,36.41]**, **Sentinel-2 L2A · Planetary Computer**만 선택. 응답 HTTP200/outcome=success/**2건**이다. 이전 건수에 맞춘 fixture/결과 조작을 하지 않았으며 LIVE는 0건 여부만 검사하고 고정2건을 요구하지 않는다.

| 실제 Item ID | 촬영 시각 UTC | 장면 구름량 | 기하 중첩 | 실제 AOI QA |
|---|---|---:|---:|---|
|`S2B_MSIL2A_20250725T021539_R003_T52SBF_20250725T041758`|2025-07-25T02:15:39.024000Z|1.197259%|100%|not_checked|
|`S2C_MSIL2A_20250720T021631_R003_T52SBF_20250720T054314`|2025-07-20T02:16:31.025000Z|69.629484%|100%|not_checked|

두 결과의 provider_id=`planetary-computer`, collection=`pc-sentinel-2-l2a`, 제품=`S2MSI2A`. 첫 장면의 **제공처 PNG 전체2,190,270바이트/1024×1024**를 앱의 기존 미디어 경로로 받아 PNG 시그니처·브라우저 decode·로컬 전체 픽셀 decode를 확인했다. HEAD/일부 바이트만으로 성공 처리하지 않았다. 원본 다운로드 요청은**0건**이다. 두 번째 장면 전체 미리보기/원본·실제 픽셀 QA·NDVI·공개 제공처 전체 실연결은 이번 실제 검증에 포함하지 않는다.

안전한 산출물: `test-results/scene-cards/live-search.json`, `live.json`, `live-decode.json`, `live-preview.png`, `live-desktop.png`, `live-desktop-preview.png`, `live-mobile.png`; fixture 캡처 `card-1440.png`, `card-390.png`. JSON은 공개 Item/날짜/수치·이미지 크기만 기록하고 토큰/쿠키/서명 URL은 기록하지 않는다. 최신 실제 이미지/스크린샷을 열어1440px·390px에서 확인했다. 현재3000/8000 프로세스 PID14364/38828은 재시작하지 않았다.

## 사용자 확인 순서·남은 제한

1. `http://127.0.0.1:3000/`에서 목적 직접 선택=식생, 위 기간/네 좌표 입력 후 좌표 적용. 위성 직접 선택에서 PC Sentinel-2만 선택하고 명시 검색한다.
2. 카드 앞부분의 촬영일/제품/제공처·추천 근거·**픽셀 처리 미지원**을 확인한다. 지도에서 선택/날짜 필터로 같은 Item 강조가 연결되는지 본다.
3. 제공처 미리보기를 확인하고 장면 구름량/기하 중첩/실제 QA 미검사를 구분한다. 촬영·추천 상세/밴드/Item ID를 필요할 때 펼친다. 밴드 전체 선택·해제·추천 복원은 그대로다.
4. `두 장면 미리보기·메타데이터 비교`에서 비교한다. 픽셀 처리 버튼을 제공하는 비교가 아니다.
5. 원본이 필요할 때만 밴드 영역의 접근 확인→원본 다운로드를 사용한다. 링크 목록.txt와 전체 파일 수신은 별개이며, 이번 검증은 실제 원본을 다운로드하지 않았다.

백엔드 코드 미변경으로 이번 Phase pytest는 미실행. 전체 E2E가 아닌 위 관련10개 파일의 비LIVE68개와 별도LIVE1개만 실행했다. 변경된 `search.spec.ts` 자체 및 다른 LIVE 제공처/AI/Kakao/실제 원본·분석 엔진은 미실행이다. 미리보기 후보 없음·파일 인증/크기/제공처 장애·PC 픽셀 처리 미지원은 기존 한계대로 남는다. 신규 분석/인증 수리나 추가 Phase로 진행하지 않는다.

---

# 이전 Phase: 수집 입력 가독성·키보드 접근 — 2026-11-03

이번 범위는 데이터 수집 화면의 표시/배치와 UI 회귀 검증이다. 기존 디자인 팔레트·글꼴을 유지하고 수집 화면 전용 CSS로 가독성을 보완했다. 상태 관리 훅·AI 요청/캐시/IME/수동 보호·날짜/AOI 확정·검색 실행 조건·지도 선택·분석 엔진은 변경하지 않았다. 키/환경/이용조건·유료 AI·배포/push·서버 재시작 없음. 이번 Phase 검증 후 후속 기능에 착수하지 않는다.

## 실제 수정과 유지 범위

- 큰 SIGNAL 장식/긴 소개의 공간을 수집 화면에서 줄이고 목적·기간·AOI·검색 바로가기를 먼저 배치했다. 바로가기는 포커스/스크롤 이동만 하며 API/영역 선택/검색을 실행하지 않는다.
- 기존 단일 검색 버튼을 지도·추천 카드 뒤에서 핵심 입력 뒤의 같은 form으로 옮겼다. `form="analysis-input"`, submit handler와 disabled 표현식은 그대로다. 제품/검색 제한의 상세는 접어 보관하고 추천 카드 뒤에는 같은 버튼으로 돌아가는 이동 링크만 제공한다. 검색 버튼을 복제하지 않았다.
- AI 기본 영역은 상태·필요한 행동·명시 비용 고지와 필요한 오류/충돌/후보 선택 위주다. 모델·호출 통계·원문 근거·단계별 검사·출처는 `AI 해석 상세·출처·사용량`에 보존한다. 초기 비활성 재시도는 숨기고 실제 응답/오류가 있을 때 기존 재시도를 제공한다. 직접 목적/날짜/좌표 입력과 실패의 `직접 입력으로 계속`은 유지했다.
- 분석 장소/위치 재시도·직접 지명·거리 도구를 AOI 입력 옆으로 옮겼다. 동일 state와 기존 callback만 사용한다. 선택적 관측 조건은 핵심 입력 뒤로 이동했다.
- 본문/상태/버튼을14–17px, 텍스트/날짜/좌표 입력을16px로 표시한다. 입력 배경은 불투명하게 하고 키보드 focus-visible3px·최소44px 제어 높이를 제공한다. 날짜 그리드를 minmax(0,1fr)로 보완해 모바일 날짜 입력이 폼 밖으로 밀리지 않게 했다. 실제 입력·버튼·상태/비용·오류의 계산된 색 대비 최소4.5:1을 새 E2E에서 검사한다(앱 전체 접근성 인증을 뜻하지 않음).
- 원래 접근성 이름 `시작일`/`종료일`/네 좌표명을 유지하고 자동/수동 표시는 aria-describedby로 연결한다. 좌표 오류는 기존 검증 결과를 검색 영역의 role=alert로 표시한다. 새 검증 규칙을 만들거나 원래 허용/차단을 바꾸지 않았다.

## 변경한 실제 파일

| 경로 | 역할 |
|---|---|
| `frontend/src/components/WorkflowWorkspace.tsx` | 핵심 입력/장소·위치 도구/선택 조건 순서, 단일 검색 위치·바로가기·가까운 오류 안내·접근성 이름 |
| `frontend/src/components/AutomaticConditions.tsx` | 간결한 상태/행동·비용 고지, 접힌 기술 상세/통계/근거/출처. 기존 handler 재사용 |
| `frontend/src/app/globals.css` | `.collection-workspace`에 한정한 크기/대비/포커스·장식 공간·반응형 입력 그리드 |
| `frontend/tests/collection-readability.spec.ts` | 신규6개:1440/834/390px 키보드 입력/단일 검색·대비/입력 폼 경계, AI 성공/실패/수정 보호·상세 펼침, 지도 바로가기 |
| `frontend/tests/ai-primary-fixtures.ts` | 접힌 설정 문구 대신 동일 설정 응답의 준비 속성을 기다리는 test hydration 대기. 요청 fixture/결과는 그대로 |
| `README.md`, `docs/AI_PRIMARY_INPUT.md`, `TEST_REPORT.md` | 표시 계약·실제 검증/한계 기록 |

`useConditionInput.ts`, `MapPanel.tsx`, 기존 science/검색/다운로드/API·환경 파일은 변경하지 않았다. 이전 처리 화면 Phase도 별도 수집 class 밖의 스타일과 기존 상태로 유지한다.

## 최신 실제 실행 (KST)

| 명령 / 위치 | 실제 시각 | 종료 코드·결과 |
|---|---|---|
| `npm.cmd run typecheck` / frontend | 최종15:03:02–15:03:05 | **0**, 독립 TypeScript 검사 |
| 아래 production build wrapper / frontend | 최종15:03:05–15:03:27 | **0**. 수집 최종 기능 코드 포함. 기존 next-env.d.ts/tsconfig.json 바이트 복원 |
| 아래7개 E2E 파일, output `test-results-collection-readability` | 14:51:35–14:57:35 | **1**,28 passed /19 failed. 아래 회귀/테스트 가정과 dev 재로딩을 반영한 초기 실패이며 통과로 취급하지 않음 |
| `npx.cmd playwright test tests/collection-readability.spec.ts --timeout=45000 --workers=2` / frontend, output `test-results-collection-readability-focus` | 14:58:07–14:58:36 | **0**,6 passed(25.7s). 이후 캡처에서 날짜 폼 경계 문제를 발견해 CSS와 경계 검사를 보완했으므로 이것만을 최종 검증으로 사용하지 않음 |
| 아래7개 파일 최종 E2E, output `test-results-collection-readability-final` | 15:03:55–15:06:39 | **0**,47 passed,2.7min. 최종 고정 소스의 신규6개·기존 입력/수동 보호/IME·지도·복원·처리 안내 회귀 모두 통과 |

E2E는 기존3000 dev 프런트/8000 백엔드의 새 Edge/Playwright 세션을 사용한다. 최종 실행은 기능 코드를 고정한 뒤 실행한다. 전체 E2E/pytest를 실행했다고 주장하지 않는다.

```powershell
$env:E2E_BASE_URL='http://127.0.0.1:3000'
$env:E2E_API_BASE_URL='http://127.0.0.1:8000'
$env:E2E_OUTPUT_DIR='test-results-collection-readability-final'
npx.cmd playwright test tests/collection-readability.spec.ts tests/automatic-conditions.spec.ts tests/ai-conditions.spec.ts tests/ai-camera.spec.ts tests/boundary-conditions.spec.ts tests/analysis-selection.spec.ts tests/processing-guidance.spec.ts --timeout=45000 --workers=2
```

실제 production build 명령은 서버 환경 필터·별도 output을 사용하고 Next가 자동 변경하는 두 설정 파일을 원래 바이트로 복원한다. build 성공과 production 서버의 실행 검증은 별개다.

```powershell
node --input-type=module -e "import {spawnSync} from 'node:child_process';import {readFileSync,writeFileSync} from 'node:fs';import {frontendEnvironment} from '../scripts/server-env.mjs';const names=['next-env.d.ts','tsconfig.json'];const prior=names.map(n=>readFileSync(n));let code=1;try{const r=spawnSync(process.execPath,['node_modules/next/dist/bin/next','build','--webpack'],{stdio:'inherit',env:frontendEnvironment({...process.env,NEXT_DIST_DIR:'.next-collection-readability',API_BASE_URL:'http://127.0.0.1:8000'})});code=r.status??1;}finally{names.forEach((n,i)=>{if(!readFileSync(n).equals(prior[i]))writeFileSync(n,prior[i]);});}process.exit(code);"
```

초기 실패에서 날짜/좌표 상태를 label 안에 배치해 접근성 이름이 바뀐 실제 회귀를 발견했다. 원래 이름을 복원하고 provenance를 설명 속성으로 연결했다. 신규 검사가 빈 문장 수동 입력에서 항상 `직접 입력으로 계속` 버튼/disabled 검색을 기대한 가정도 보완했다. 원래 코드는 이 경우 직접 selector와 HTML 필수 날짜·검색 시 좌표 검증을 사용한다. 따라서 그 기존 게이트를 유지한 채 잘못된 좌표에서 실제 검색 API 요청0건을 검사한다. 실행 중 수정으로 dev 재로딩이 섞인 초기 navigation/복원 실패도 최종 통과 증거로 사용하지 않으며, 최종 소스를 고정한 전체 관련 suite로 재검사한다.

## 검증 범위와 한계

실제 브라우저 크기는 데스크톱1440×1000 / 태블릿834×1112 / 모바일390×844다. 키보드 Tab·Enter·바로가기·focus-visible, 입력/날짜/좌표·AOI 확정→동일 검색 요청, AI mock 상태/상세 펼침·수동값 보호·IME/경합·지도 선택/드래그·뒤로/새로고침 복원을 검사했다. 문서 가로 넘침뿐 아니라 각 날짜/좌표 입력의 폼 경계도 통과했다. `test-results/collection-readability/inputs-1440.png`, `inputs-834.png`, `inputs-390.png`, `error-390.png`는 mock UI 캡처이며 직접 열어 확인했다. 최종 모바일/태블릿 캡처에서 날짜 입력이 폼에 들어가고 단일 검색 버튼·큰 오류 글씨·명확한 포커스가 유지됨을 확인했다. 사용자 실제 저장 작업을 검증한 것으로 일반화하지 않는다.

기존 dev 서버가 수정 프런트를 자동 반영한다. 검증 중 backend PID38828(8000)·frontend PID14364(3000)는 유지했으며 프로세스를 종료하거나 새 운영 서버를 시작하지 않았다. 확인 순서: 수집(`/`) 새로고침 → 목적/기간/AOI 바로가기와 비용 고지 → 직접 입력 또는 AI 해석 상태 확인 → 필요 시 AI 상세 펼침 → AOI 좌표 적용/지도 확정 → 핵심 입력 뒤의 검색 버튼. 이 순서가 자동 검색이나 유료 AI 검증 실행을 의미하지 않는다. 이번 Phase를 완료하고 멈춘다.

검색·AI·Kakao 응답은 명시 test fixture이며 유료 AI·실제 지명/영상/원본 파일 API 성공을 뜻하지 않는다. basemap과 로컬 카탈로그/일반 작업 해석은 기존 경로를 사용한다. 실제 제공처 접속·전체 pytest/전체 E2E·실기기 가상 키보드·음성 스크린리더 검증은 이번 Phase에서 미실행이다. 초기 비어 있는 폼의 검색 버튼 비활성 여부만으로 조건 검증 성공을 주장하지 않는다. 이전 Phase의 실제 영상/전체 suite 결과를 이번 최신 전체 코드 통과 증거로 재사용하지 않는다.

---

# 이번 Phase: 처리 화면의 빈 상태·분석별 다음 행동 — 2026-11-03

요청 범위는 처리 안내/UI 분기 수정이다. 기존 사용자 상태·디자인·수집·다운로드와 실제 S2 QA/NDVI/관측 합성/제한 ML 엔진을 보존했다. 새 과학 엔진·API·페이지·상태 저장소를 만들지 않았다. 자격증명/환경/이용조건 플래그·유료 AI·실제 제공처 원본·배포/push는 건드리지 않았다. 백엔드 소스 변경이나 프로젝트 재시작도 없다. 이 Phase 검증 후 후속 기능에는 착수하지 않는다.

## 실제 원인과 수정

- 기존 `WorkflowWorkspace`의 MapPanel과 공통 검색 빈 상태가 처리 페이지에서도 무조건 표시됐다. 선택 영상이 없는 경우 WorkSummary와 별도 경고·공통 다음 작업이 겹칠 수 있었다. 이제 복원 중/선택 없음의 **단일 수집 복귀 안내**를 표시하고 지도·빈 검색·처리 단계·일반 처리 footer를 숨긴다. 지도/Workspace의 단일 상태 소유는 유지한다.
- 세부 분석과 실제 제품 지원에 관계없이 공통 처리 단계·전처리 설명·NDVI 열기 버튼이 표시됐다. 기존 `analysis_catalog`와 `s2QualitySupported`를 조합한 **표시용 capability**로 QA/전처리/NDVI 안내를 구분한다. 자료 적합성·선택 밴드·전체 수신·서버 canonical/픽셀 검증은 기존 게이트가 계속 담당한다.
- 상단 작업 요약에 `현재 가능한 다음 행동`을 추가했다. 미확정/자료 보완/원본 확보/지원 QA·NDVI·한 시점 전처리/앱 처리 미지원 상태를 나눠 안내한다. 원본 확보 링크는 같은 선택 카드의 밴드·다운로드 패널을 연다.
- Landsat L2SP 열환경은 실제 목적·AOI·기간·lwir11/QA 밴드·수신 개수·픽셀 QA 상태를 보존하고 원본 확보·메타데이터·외부 GIS만 안내한다. 원본을 받았다는 이유로 미지원 온도 계산을 활성화하지 않는다. 일반 S2 합성/NDVI 단계와 실행 버튼을 없앴으며 Sentinel-2를 열적외선 대안으로 표시하지 않는다.
- S2 두 날짜 NDVI는 기존 QA/전처리/계산 UI를 유지한다. 한 시점 식생은 기존 QA·관측 합성 ZIP·확인된 결측의 제한 ML을 유지한다. 단일 NDVI나 합성 ZIP→NDVI 자동 연결이 없으므로 한 시점 결과에서 이를 실행하는 듯한 `분석으로 계속하기` 버튼은 제공하지 않는다. 전처리 결과만 받고 종료할 수 있다. 원본·실측 합성·ML 추정 구분은 유지한다.
- 목적·AOI·UTC 기간·장면·밴드·수신 기록·방법 선택/확정과 저장/뒤로·앞으로/새로고침 로직은 그대로 재사용한다. 과거 작업 기록·산출물 조회도 현재 작업과 구분해 유지한다.

## 변경한 실제 파일

| 경로 | 역할 |
|---|---|
| `frontend/src/lib/analysisFlow.ts` | 기존 카탈로그/제품 검사에 따른 표시 capability와 TypeScript 타입. 과학 규칙/실행 허가 복제 없음 |
| `frontend/src/components/WorkflowWorkspace.tsx` | 빈 처리 화면·지도/빈 검색 숨김·실제 지원 단계 표시. 상태/복원/엔진 유지 |
| `frontend/src/components/WorkSummary.tsx` | 확정 방법·제품/자료 상태에 맞는 다음 행동, 원본 복귀·메타데이터·GIS 안내 |
| `frontend/src/components/AnalysisSelection.tsx` | 실제 경로가 없는 작업에 일반 전처리 계획을 노출하지 않음. 기존 의도 선택/확정·자료 검사는 유지 |
| `frontend/src/components/NaturalWorkflow.tsx` | 미지원 자료의 일반 처리 안내/자동 후속 해석 비활성, 지원 S2 흐름 보존·NDVI와 한 시점 전처리 설명 구분 |
| `frontend/tests/processing-guidance.spec.ts` | 신규6개 UI 사례:1280/390px 빈 화면·저장 열환경, 수동 밴드/부분 수신 복원, 미확보 NDVI 차단 |
| `frontend/tests/analysis-selection.spec.ts`, `frontend/tests/next-work.spec.ts`, `frontend/tests/workflow-pages.spec.ts` | 미지원 작업에 가짜 실행 항목을 기대하던 검사와 빈 화면/원본 복귀 기대 수정, 지원 자료의 미지원 후속 요청 검사는 별도 유지 |
| `docs/ANALYSIS_SELECTION.md`, `docs/WORKFLOW_PAGES.md`, `TEST_REPORT.md` | 이번 표시 계약·기존 지원 범위·검증 기록 |

`types.ts`, `workSession.tsx`, 백엔드 API/카탈로그·픽셀 처리 코드는 읽고 재사용했으며 변경하지 않았다. CSS/색/글꼴·인증·검색 제공처는 변경하지 않았다.

## 실제 실행 명령·결과 (KST)

| 명령 / 위치 | 실제 시각 | 종료 코드·결과 |
|---|---|---|
| `.venv\Scripts\python.exe -m pytest backend/tests/test_analysis_flow.py backend/tests/test_change_analysis.py backend/tests/test_work_sessions.py -q` / 루트 | 14:19:57–14:20:11 | **0**,42 passed,432 warnings,10.81s. 세부 분석 계약·기존 NDVI 계산·작업 소유권 fixture 회귀 |
| `npm.cmd run typecheck` / frontend | 14:19:18–14:19:22, 최종14:26:24–14:26:28 | **0**, **0**. 독립 tsc, 최신 테스트 수정 포함 |
| 아래 분리 production build / frontend | 14:19:46–14:20:28 | **0**. 최신 기능 코드 포함 .이후 변경은 테스트/문서뿐 |
| 아래9개 파일 E2E / frontend | 14:21:20–14:26:01 | **1**,55 passed /5 skipped /2 failed .새 표시 계약에 따른 링크 위치, 기본 밴드 저장 가정의 테스트 실패를 아래처럼 수정 |
| 동일9개 파일 E2E 최종, output `test-results-processing-guidance-final` | 14:26:29–14:30:50 | **0**,57 passed /5 skipped,4.3min. 신규6개와 원본 복귀·상태 복원·기존 지원 엔진 UI 회귀 모두 통과 |

E2E 명령(PowerShell):

```powershell
$env:E2E_BASE_URL='http://127.0.0.1:3000'
$env:E2E_API_BASE_URL='http://127.0.0.1:8000'
$env:E2E_OUTPUT_DIR='test-results-processing-guidance-final'
npx.cmd playwright test tests/processing-guidance.spec.ts tests/analysis-selection.spec.ts tests/next-work.spec.ts tests/workflow-pages.spec.ts tests/change-analysis.spec.ts tests/pixel-quality.spec.ts tests/cloud-workflow.spec.ts tests/estimate-mode.spec.ts tests/landsat-preview.spec.ts --timeout=45000 --workers=2
```

Production build 명령(기존 Next 설정 파일 바이트 보존, 서버 환경 필터·독립 output 사용):

```powershell
node --input-type=module -e "import {spawnSync} from 'node:child_process';import {readFileSync,writeFileSync} from 'node:fs';import {frontendEnvironment} from '../scripts/server-env.mjs';const names=['next-env.d.ts','tsconfig.json'];const prior=names.map(n=>readFileSync(n));let code=1;try{const r=spawnSync(process.execPath,['node_modules/next/dist/bin/next','build','--webpack'],{stdio:'inherit',env:frontendEnvironment({...process.env,NEXT_DIST_DIR:'.next-processing-guidance',API_BASE_URL:'http://127.0.0.1:8000'})});code=r.status??1;}finally{names.forEach((n,i)=>{if(!readFileSync(n).equals(prior[i]))writeFileSync(n,prior[i]);});}process.exit(code);"
```

초기 검사에서 루트의 `npm.cmd run typecheck`는 package.json이 없어 ENOENT로 실패했다(종료 코드 미보관). 이후 정확한 frontend 경로에서 독립 검사 exit0을 확인했다. 별도3019 검증 서버의 background 시작 명령은 **자동 승인 검토가 실행 전에 차단**했다(반환 사유 `blocked by policy`, 프로세스 종료 코드 없음). 별도 서버를 다른 방식으로 강제 실행하지 않고 기존3000/8000을 새 브라우저 세션에서 사용했다. 사용자 서버를 종료/재시작하지 않았다. production build 성공과 실제 production 서버 실행 검증은 별개다.

초기 E2E의2개 실패는 다음과 같다. 기존 테스트가 계산 미지원 Landsat에서도 숨겨진 공통 `next-work` 링크를 찾았다. 상단의 실제 `원본 확보·선택 밴드 확인으로` 링크로 바꿔 선택한 카드가 열리는지 검사한다. 신규 테스트는 기본 밴드를 `saved.bands`에 중복 보관한다고 가정했으나 실제 코드는 default_keys에서 유도하고 수동 변경만 보관한다. QA 밴드를 실제로 해제/재선택한 뒤 뒤로·앞으로/새로고침에서 수동값·부분 수신 기록을 검사하도록 보완했다. 기능 게이트를 느슨하게 하거나 기대 수신 개수를 바꾸지 않았다.

## 브라우저 확인과 미실행 범위

새 Edge/Playwright 세션, 기존 localhost3000의 최신 dev 코드로 UI를 검증했다. 검색·미디어·파일·픽셀 결과는 각 테스트의 명시 fixture이며 실제 AI/지명/제공처 파일 요청은 실행하지 않았다. 백엔드 카탈로그와 기존 일반 작업 해석은 로컬 API를 사용했다. `test-results/processing-guidance/empty-1280.png`, `empty-390.png`, `thermal-1280.png`, `thermal-390.png`는 mock UI 캡처이며 직접 열어 단일 빈 안내·열환경 다음 행동·0/3 수신·QA 미검사·미지원 온도 안내와 가로 넘침 없음을 확인했다. 사용자 실제 저장 작업/원본을 읽거나 검증한 것으로 표현하지 않는다.

14:29:54 KST의 `/processing`, `/api/health`, backend `/health`는 모두 HTTP200이었다. 사용자 backend PID38828(8000)·frontend PID14364(3000)는 변경되지 않았고 현재 dev 서버가 프런트 변경을 자동 반영했다. 서버200을 분석/다운로드 성공으로 쓰지 않는다. 저장된 작업을 사용자가 직접 확인하려면 `/processing`을 새로고침한다. 영상이 없으면 복귀 안내만, 열환경 작업이면 원본 확보·메타데이터·외부 GIS 안내를 확인한다. 지원 S2 방법에서는 기존 실행 전 자료/수신 검사를 유지한다.

실제 공개 영상 검색·미리보기/원본 전체 수신·운영자 인증·유료 AI·실제 A3/A4/합성/ML 원격 처리 검증은 이번 Phase에서 미실행이다. 관련 LIVE5개는 기본 실행에서 skip이며, 기존 제공처/HLS400·인증·다운로드 제한을 해결했다고 하지 않는다. 전체 pytest/전체 E2E 대신 이번 표시/상태/엔진 연결에 관련된 명시 suite를 실행했다. 아래 이전 Phase의 전체 통과 기록을 최신 전체 코드 검증으로 재사용하지 않는다.

---

# Landsat Earth Search → 정확한 PC 제공 미리보기 — 2026-11-03

사용자 후속 확인(2026-11-03): **처음 선택한 카드의 Item ID는 여전히 미확인으로, 그 장면의 해결 여부는 미검증이다.** 아래 성공은 명시한 실제 L2SP 표본에만 해당한다. [사용자 장면 별도 재현 절차](docs/PUBLIC_DATA_ACCESS.md#검증-범위와-사용자-장면의-별도-재현-절차)를 추가했다. 제공처/컬렉션/Item ID·기존 AOI/UTC 기간·밴드로 목표 카드를 다시 선택하고, 제품 대응·미리보기 전체 수신·원본 접근을 별도로 확인하도록 했다. 이번 후속 작업은 문서2개만 변경했으며 기능/환경/인증 변경·서버 재시작·새 외부 요청·새 테스트 실행은 하지 않았다. 아래 실행 시각과 결과는 이전 실제 실행 기록이며 이번에 다시 실행한 것으로 보고하지 않는다.

이번 범위는 기존 Landsat 미리보기/접근 안내 수리다. 선택 장면·밴드·검색/추천·원본 다운로드·분리 페이지·A2~A4 엔진과 디자인을 보존했다. `.env`, 자격증명, 이용조건 승인 플래그, requester-pays 동의는 변경하지 않았다. 유료 AI·계정 생성·원본 대용량 수신·배포/push 없음. 사용자가 공개 Item ID 질문에 환경 파일을 언급했으나, 허용된 공개 ID 변수만 제한적으로 검사했을 때 해당 ID는 없었다. 아래 표본은 **현재 브라우저에서 읽은 ID가 아니라 실제 앱 검색으로 재현한 Earth Search L2SP 장면**이다.

## 확인된 원인과 실제 표본

- 제공처 `earth-search`, 컬렉션 `landsat-c2-l2`, Item `LC09_L2SP_116035_20250723_02_T1`.
- 전체 제품 `LC09_L2SP_116035_20250723_20250726_02_T1`, Landsat-9 / L2SP / Collection02, 촬영 UTC `2025-07-23T02:11:18.464892Z`.
- UTC 기간 `2025-07-20`–`2025-07-26`, bbox `[126.7,36.4,126.71,36.41]`, 열환경 목적.
- 실제 canonical Earth Search `thumbnail`/`reduced_resolution_browse`는 requester-pays S3다. 정확히 대응된 USGS ST browse는 **GET HTTP302 → `ers.cr.usgs.gov`** 로그인 호스트였다. 리다이렉트는 따라가지 않았고 NASA 토큰을 보내지 않았다. 기존 화면의302는 공개 이미지 수신 성공이 아니다.
- PC는 전체 제품 ID 대신 처리일을 생략한 짧은 Item ID를 사용했다. canonical PC Item의 실제 밴드 Asset 경로에서 전체 제품을 확인하고 플랫폼·촬영 시각·수준·버전·scene ID까지 대조한 뒤에만 PC 이미지를 사용한다. 영상별 처리일이 다르면 같은 장면으로 합치지 않는다.
- 실제 API 통합 검증(12:14 KST): 원래 ES 선택을 유지한 채 PC `rendered_preview` **전체1,239,292바이트**, PNG **1009×1024**, 4채널 **4,132,864개 값 전체 디코딩** 성공. 원래 `lwir11` 접근은 여전히 USGS302 / `access_verified=false`. 안전한 요약 `test-results/landsat-preview/before.json`, `after.json`, 이미지 `verified-preview.png`. 토큰·쿠키·서명 query/Location 원문은 저장하지 않았다.

## 변경 파일과 역할

| 실제 경로 | 변경 |
|---|---|
| `backend/app/landsat_access.py` | PC canonical 조회·전체 제품/처리일·플랫폼·UTC 시각·수준·Collection/scene 검증 |
| `backend/app/media_access.py` | 제한된 PC 공개 이미지 후보·전체 디코딩·원래 소유자/참조에 묶인 ticket·출처/원래 실패 분리. 캐시 키에 전체 제품 버전 추가 |
| `backend/app/provider_transfer.py` | 차단된 로그인 리다이렉트의 허용된 호스트만 안전하게 진단·반환. 목적지 허용 범위/인증 전달 규칙은 완화하지 않음 |
| `frontend/src/lib/useProviderAccess.ts` | 별도 미리보기 출처/제품 검증·원래 제한·대체 실패 타입 |
| `frontend/src/lib/workSession.tsx` | 기존 공유 상태에 명시 PC 검색 동작 연결 |
| `frontend/src/components/WorkflowWorkspace.tsx` | 현재 AOI·UTC 기간·목적을 유지하는 명시적 PC 컬렉션 검색. 이전 추천 카드의 선택 조건은 해제하고 최종 PC 조건 표시 |
| `frontend/src/components/ProviderPreview.tsx` | PC 출처·원본 권한 분리, 원래 thumbnail 없는 경우도 검사, PC 검색 버튼·접힌 기술 상세 |
| `frontend/src/components/ManagedAssetAccess.tsx` | 이해하기 쉬운 USGS 원본 로그인 안내·접힌 HTTP 상세 |
| `frontend/src/components/AssetDownloads.tsx` | 미리보기와 원본 확보·권한의 구분 |
| `backend/tests/test_landsat_preview.py` | 23개 fixture 회귀 사례 |
| `frontend/tests/landsat-preview.spec.ts` | 6개 mock UI 회귀 + opt-in 실제 공개 이미지 검증 |
| `README.md`, `docs/PUBLIC_DATA_ACCESS.md`, `TEST_REPORT.md` | 현재 경로·사용법·근거·검증/제한 기록 |

기존 `/media/inspect` 응답에 선택적 출처/검증/실패 상세 필드만 추가했다. 검색 API·장면/밴드 식별·원본 다운로드 API·science API와 엔진은 교체하지 않았다. USGS 로그인이나 S3 requester-pays를 PC 미리보기로 해결했다고 표시하지 않는다. PC 대응 실패는 원래 실패를 유지하고 사용자가 누르는 PC 재검색만 제공한다. 공식 [PC Landsat 컬렉션](https://planetarycomputer.microsoft.com/api/stac/v1/collections/landsat-c2-l2)의 실제 Asset/메타데이터와 기존 공개 전송/SAS 경로를 사용한다.

## 최신 실행 결과 (KST)

| 실행 명령 / 위치 | 시각 | 종료 코드·결과 |
|---|---|---|
| `.venv\Scripts\python.exe -m pytest backend/tests -q` / 루트 | 12:22:49–12:24:51 | **0**, 517 passed / 16 skipped / 1096 warnings, 118.60s. 실연결 opt-in 16개는 미실행 |
| `npm.cmd run typecheck` / frontend | 12:31:41–12:31:49, 최종12:37:51–12:37:53 | **0**, **0**. 최종 모바일 캡처 대기 보완까지 독립 TypeScript 검사 |
| 아래 분리 output production build / frontend | 12:19:15–12:20:00 | **0**. 최신 프런트 기능 코드 포함. 이후 기능 변경은 backend 캐시 버전 키뿐이며 pytest에 포함 |
| `E2E_BASE_URL=http://127.0.0.1:3019 E2E_API_BASE_URL=http://127.0.0.1:8019 E2E_OUTPUT_DIR=test-results-landsat-final npx.cmd playwright test --timeout=45000 --workers=2` / frontend | 12:30:39–12:35:57 | **0**, 174 passed / 10 skipped, 5.3min. HLS/공개 파일·픽셀/ML 등 opt-in 실검증과 이번 Landsat LIVE는 기본 실행에서 미실행 |
| `E2E_BASE_URL=http://127.0.0.1:3000 LIVE_STAC=1 LIVE_LANDSAT_PREVIEW=1 E2E_OUTPUT_DIR=test-results-landsat-live npx.cmd playwright test tests/landsat-preview.spec.ts --grep 'LIVE Earth Search Landsat' --timeout=120000 --workers=1` / frontend | 12:36:25–12:36:47 | **0**, 실제 공개 API/현재 웹 브라우저 1 passed, 19.9s |
| 위 LIVE 명령, output `test-results-landsat-live-final` | 12:37:28–12:37:45 | **0**, 1 passed, 14.8s. 모바일 resize 후 이미지 표시/디코딩 대기를 보완해 데스크톱·모바일 최종 캡처 재확인 |

위 환경변수 표기는 명령의 환경 설정을 요약한 것이다(PowerShell에서는 `$env:이름='값'`). 3019/8019는 이번 검증 전용 production frontend/최신 backend이며 사용자 사이트와 분리했다. 신규6개 UI 회귀는 mock이다. 전체 suite에는 기존 실제 읽기 전용 SAR/VIIRS/S2 검색 테스트도 포함된다(각 카드/수동 검색과 다중 제공처 검색). 운영자 자격증명/실제 AI·Kakao 호출은 사용하지 않는다. fixture 통과를 실제 제공처 성공 근거로 대신하지 않는다.

Production build는 기존 frontend 환경 필터와 독립 `.next-conditions-final`을 사용하고 Next가 수정하는 두 설정 파일을 원래 바이트로 복원했다. 실행 명령:

```powershell
node --input-type=module -e "import {spawnSync} from 'node:child_process';import {readFileSync,writeFileSync} from 'node:fs';import {frontendEnvironment} from '../scripts/server-env.mjs';const names=['next-env.d.ts','tsconfig.json'];const prior=names.map(n=>readFileSync(n));let code=1;try{const r=spawnSync(process.execPath,['node_modules/next/dist/bin/next','build','--webpack'],{stdio:'inherit',env:frontendEnvironment({...process.env,NEXT_DIST_DIR:'.next-conditions-final',API_BASE_URL:'http://127.0.0.1:8019'})});code=r.status??1;}finally{names.forEach((n,i)=>{if(!readFileSync(n).equals(prior[i]))writeFileSync(n,prior[i]);});}process.exit(code);"
```

초기 검증 실패도 보존한다. pytest 최초 전체 실행은515 passed/16 skipped/1 failed(exit1): 새 테스트의 HTML200 차단 기대값을 기존 실제 분류 `login_page`로 수정했다. 초기 E2E는173 passed/10 skipped/1 failed(exit1,12:28:47 종료): 이미 열린 원본 패널을 테스트가 다시 닫아 확인 버튼이 숨겨진 문제였다. 열린 상태를 확인한 뒤 조작하도록 테스트를 수정했고 해당 단일 재검사는 exit0/1 passed. 기능 결함을 테스트 성공으로 감추거나 미실행 검증을 통과로 쓰지 않았다.

새 fixture는 제품 처리일/시간/플랫폼/수준/버전/scene ID 불일치, PC401/403/404/429/503, 이미지 없음, 원래 thumbnail 없음, SAS403 후 단1회 갱신, 잘못된 호스트/다른 Item URL 차단, 로그인 HTML, 원본 ticket 분리/다른 소유자 차단, 같은 짧은 ID 처리 버전의 캐시 격리를 검사한다. 기존 공개 경로 SAS 만료/동시 갱신·크기 제한/원본 파일, Earth Search·PC·NOAA 및 추천/비교/다운로드/모바일 테스트도 전체 suite에 포함된다.

## 실제 사이트 반영·브라우저 결과

최종 전체 검증 후 현재 작업의 사용자 승인(진행 작업 없음)에 따라 12:36:18 KST에 이 프로젝트만 `start.cmd`로 재시작했다. 이전 launcher7776 → node40264 → backend40484/9484 및 frontend20688/14596의 경로·계보를 먼저 확인하고 해당 트리만 종료했다. 새 launcher34372, 현재 backend listener38828(8000)·frontend14364(3000). 프런트 페이지·`/api/health`·backend `/health` HTTP200. 검증 전용8019/3019는 검증 후 별도로 종료했으며 현재 사용자 사이트는 계속 실행 중이다.

실제 [현재 사이트](http://127.0.0.1:3000/)에서 새 Edge/Playwright 브라우저로 검색 → 실제 canonical 대응 검사 → 서버 이미지 전체 응답 → 브라우저 PNG 표시를 확인했다. 제공처 로그인 쿠키를 설정하지 않았고 AI/지명 요청은 테스트 런타임에서 차단했다. 현재 사이트 API와 실제 Earth Search·USGS·PC 요청을 사용했으며 이 LIVE 테스트의 검색/미디어를 fixture로 바꾸지 않았다. 원본 다운로드 요청은 **0건**, 원래 `lwir11` 밴드/ES 선택을 유지했다. 전체 suite 이후 바뀐 것은 LIVE 테스트의 캡처 대기뿐이며 최종 LIVE와 typecheck를 다시 실행했다. 기능 코드는 그대로다.

최종 안전 요약 `test-results/landsat-preview/browser.json`: 12:37:42 KST, 동일 제품 확인, PC PNG 전체1,239,292바이트/1009×1024, 원래 USGS302/login. `browser-preview.png`는 전체 파일이고 rasterio PNG4채널 전체 읽기(4,132,864값)도 exit0으로 확인했다(12:36:58, 초기 LIVE 수신본과 최종본 바이트 수/크기 동일). 위치정보 없는 browse의 NotGeoreferencedWarning은 예상한 것으로 GIS 정량 래스터로 취급하지 않는다.

최종 `browser-desktop.png`, `browser-mobile.png`를 직접 열어 실제 이미지·PC 출처·원래 권한 유지 문구·접힌 상세/PC 검색 버튼을 확인했다. 모바일390×844에서 가로 넘침 없음. 초기 모바일 캡처는 viewport 변경 직후 observer 갱신 전 상태였으므로 LIVE 테스트에 이미지 표시/자연 크기 대기를 추가하고 재검증했다. 실제 브라우저의 **원본 파일 저장은 미실행**, 미리보기 저장 버튼의 OS 파일 저장 확인도 미실행이며 이미지 전체 응답/브라우저 표시와 구분한다. 별도 CUA 현재 탭 연결은 없어 사용자가 이전에 선택한 Item 자체는 읽지 못했다.

재현 순서: 수집(`/`) → 목적 직접 선택 `열환경` → UTC2025-07-20~07-26 → 서126.7/남36.4/동126.71/북36.41 입력 후 `좌표 적용` → Landsat OLI/TIRS 추천 카드 `이 제품 선택` → `위성영상 검색` → 위 Item 선택 → `날짜별 실제 영상`의 `Planetary Computer 제공 미리보기` 확인. `미리보기 출처·접근 상세`에서 전체 제품/USGS302 호스트를 확인한다. 기존 원본 선택에서 `선택 원본 접근 확인`을 누르면 원본 로그인 제한은 유지된다. 공개 PC 원본이 필요하면 `PC Landsat에서 검색`으로 명시 전환하고 PC 결과의 기존 원본 접근 확인/다운로드를 사용한다. 이 후속 실제 원본 다운로드 성공은 이번에 검증하지 않았다.

## 남은 제한

- 동일 제품이 PC에 없거나 원격 이미지가 실패하면 미리보기 성공을 보장하지 않는다. 원래 실패와 대체 실패를 함께 보존한다.
- ES/USGS 원본 로그인 제한은 남는다. PC 원본이 필요하면 현재 조건을 유지한 PC 재검색 후 그 제공처의 기존 명시 다운로드 경로를 이용한다. 이번 실제 검증에서 원본 밴드 다운로드는 실행하지 않았다.
- 실제 PC SAS 만료까지 기다린 검증은 미실행이며 갱신은 fixture로 검증했다. 이번 실제 이미지는 PC의 공개 rendered PNG다.
- 픽셀 QA·온도 계산·HLS400·NASA 인증·SAR 처리·다른 제공처 수리는 이번 범위가 아니다. 미리보기 성공은 분석 성공/원본 확보를 의미하지 않는다.

---

# 큰 분야 → 수집 → 세부 분석 확정 → 관련 전처리 연결 — 2026-11-03

이번 우선 계약은 [ANALYSIS_SELECTION.md](docs/ANALYSIS_SELECTION.md)이다. 두 페이지·기존 사용자 편집·디자인·추천/검색/다운로드·A2~A4/관측 합성/제한 ML 엔진을 보존하면서 실제 분류/추천/선택/호환성/실행 게이트를 연결했다. 아래 이전 보고의 품질 확인 우선 순서는 이번 세부 분석 우선 흐름으로 대체한다. 새 과학 엔진·계정·의존성 설치·인증/키/이용조건 플래그 변경·유료 AI 호출·대용량 일괄 수신·배포/push는 하지 않았다.

## 실제 연결된 흐름

1. 수집(`/`): 기존 AI 자동 조건 API에서 큰 분야·짧은 요청 요약·세부 의도/원문 근거/명시·추론을 분리한다. 일반적인 더위는 열환경만, 명시 지표면 온도는 그 의도를 보존한다. 불명/다중 분야는 미지정/후보를 남긴다. 기존 지역·UTC 기간·수동 수정 보호와 지도/AOI 흐름을 유지한다.
2. 기존 검토된 제품 추천: 큰 분야 + 알려진 세부 의도 + 관측 형태/필수 변수·제품 수준/원관측 해상도 + 현재 AOI/기간의 실제 검색 가용성·접근/QA 상태를 구분한다. 세부 의도가 두 시점을 필요로 하면 그 조건을 표시한다. 요청보다 거친 원관측을 출력 격자 재표본화로 충족한다고 하지 않는다. 카드마다 대표 세부 분석·추가 조건·엔진 지원을 표시한다.
3. 원본 다운로드만 하고 종료하거나 `세부 분석 선택으로` 이동한다. 선택·미리보기·링크.txt·원본 전체 수신은 기존대로 별개다.
4. 처리(`/processing`) 최상단의 ① 세부 분석에서 질문·필요 자료·시점 수·추가 입력·실제 산출물/미지원 엔진을 확인한다. 알려진 원문 세부 의도는 미리 선택하고 사용자가 확인/변경한다. ② 자료/품질 → ③ 관련 전처리 → ④ 분석/내보내기로 연결한다.
5. 선택 분석마다 변수/실제 Asset·선택 밴드·장면/서로 다른 날짜·허용 기간·AOI 중첩·지원 제품/플랫폼·처리 면적·기존 공통20m 출력 조건을 재평가한다. 픽셀 QA/보정/제품 기준선/날짜 선후 등은 기존 실행 서버가 다시 검증한다. 부족 자료를 자동 교체하지 않고 같은 조건/기존 선택을 보존해 수집으로 돌아간다. 선택한 세부 의도는 보완 추천에도 반영한다.
6. 원문/분야/세부 의도/확정 분석/조건/장면·밴드/수신 기록/처리 설정·작업/결과는 기존 단일 Workspace/WorkContext와 제한된 같은 탭 보관을 사용한다. 새 문장·방법·자료/설정 변경 시 관련 계획/레이어/결과를 무효화하고 늦은 응답을 폐기한다. back/reload에서 AI·검색·다운로드·작업 POST를 중복 실행하지 않는다.

## 지원과 미구현

큰 분야4개, 세부 안내 후보10개다. 이는10개 계산 엔진 지원을 뜻하지 않는다.

| 분야 | 세부 후보 | 실제 앱 계산 |
|---|---|---|
| 식생 | 단일 식생지수(NDVI), 시기별 식생 변화 | **기존 두 날짜 S2 L2A NDVI 변화만**. 단일 NDVI 독립 계산은 미구현 |
| 열환경 | 지표면 온도 분포, 고온 지역 탐색, 도시/주변 온도 비교 | 모두 계산 미구현. 검토된 Landsat L2SP 등 수집 후보·외부 GIS 활용 안내 |
| 수체/침수 | 수체 추출, 수체 변화, 침수 범위 | 계산 미구현. SAR/광학 관측량·자료 접근·SAR 전처리 미연결 분리 |
| 도시/피복 | 토지피복 변화, NDBI 검토 | 계산 미구현. 분류 체계/학습·검증 자료를 단순 지수 후보와 구분 |

도시/주변 온도 비교는 같은 관측 한 장의 서로 다른 영역을 비교할 수 있으므로 두 촬영일을 강제하지 않는다. 다중 AOI 통계 엔진은 미구현이다. NDVI 변화는 벌채 면적이나 변화 원인을 확정하는 엔진이 아니다. 일반적인 식생 변화에 사건 기준일을 임의 생성하거나 불필요하게 요구하지 않는다. 실제 사건 전후/모호한 날짜는 기존 별도 확인 계약을 유지한다.

전처리 계획은 방법별 필수/선택/불필요와 이유·실행 지원을 보여준다. 기존 한 시점 S2 QA·실제 관측 합성 ZIP·확인된 잔여 결측에 대한 제한 ML은 재사용한다. 구름 마스킹=제외, 합성=다른 날짜 실측, ML=추정이며 자동 ML은 없다. 독립 자르기/임의 재투영·해상도/단독 마스크 파일 도구, 합성/ML ZIP→NDVI 입력 자동 연결은 미구현이다. 이미 보정된 L2 제품에 대기 보정을 반복하지 않는다. 원본은 보존하며 기존 산출물의 날짜·격자·마스크·방법/설정·출처 JSON을 유지한다.

## 변경 파일과 역할

- `backend/app/analysis_catalog.py` **신규**: 세부 ID·질문/입력/산출물·추가 조건·지원 엔진·방법별 전처리 계약. 필수 변수는 기존 `purpose_plan.RULES`를 참조한다.
- `backend/app/ai_conditions.py`: 기존 strict 추출에 요약·다중 분야 후보·세부 ID/근거/명시·추론, 분야/세부 일치·근거 검증. 일반 변화와 사건 날짜 요구 구분. 규칙 fallback 추가 없음.
- `backend/app/ai_interpretation.py`: 확장 계약의 기존 서버 캐시 키 버전 구분. 기존 Responses 경로/상한·모델·키 유지.
- `backend/app/models.py`, `recommendations.py`, `main.py`: 허용 `detail_intent`, 추천에도 `requested_resolution_m`, 분야/의도 불일치422, 기존 제품/밴드/관측 규칙의 세부 조건·해상도 제약·후보 설명 확장, `GET /analysis/catalog`.
- `frontend/src/lib/analysisFlow.ts` **신규**: 현재 선택 자료/변수/시점·기간/중첩/S2 지원·면적/출력 해상도의 메타데이터 사전 검사. 실제 QA/보정을 수행한 것으로 표현하지 않음.
- `frontend/src/components/AnalysisSelection.tsx` **신규**: 세부 후보·원문 의도 사전 선택/확인·현재 두 영상의 명시 선택·부족 이유·수집 보완·관련 전처리 계획.
- `frontend/src/components/WorkflowWorkspace.tsx`: 같은 상태의 수집/세부 선택/추천/호환성/엔진 게이트·저장/복원/무효화 연결. 방법 변경은 기존 검색/장면을 자동 삭제·교체하거나 검색하지 않음. 빈/구버전 응답에 추천 정보가 없어도 카드 렌더링이 깨지지 않도록 보호.
- `frontend/src/lib/useConditionInput.ts`, `types.ts`, `workSession.tsx`: 요약/세부 의도/분야 후보·선택/확정 분석의 타입·상태·공통 실행 게이트. 기존 snapshot 보안 필터 재사용.
- `frontend/src/components/WorkSummary.tsx`, `SensorRecommendations.tsx`: 세부 분석 확정 상태·`세부 분석 선택으로`·제품별 대표 분석/추가 조건·지원 구분.
- `frontend/src/components/ChangeAnalysis.tsx`: 확정한 `ndvi_change` 의도/자료·수신 조건에서만 기존 A4 호출. 계산 알고리즘은 수정하지 않음.
- `frontend/src/components/NaturalWorkflow.tsx`: 단계 번호 조정. 기존 QA/합성/ML 경로는 같은 WorkContext 게이트 사용.
- `frontend/src/components/SceneComparison.tsx`: 모드 변경 때 기본 비교 쌍 제안 사실과 실행 전 확인 안내. 기존 비교 상태/API 보존.
- `frontend/src/app/globals.css`: 새 분석 라디오 행만 고정18px·shrink0·텍스트 줄바꿈, 처리 fieldset 배치. 기존 디자인 토큰/색/글꼴·다른 입력 CSS 유지.
- `backend/tests/test_analysis_flow.py` **신규11개**, `backend/tests/test_ai_interpretation.py`: AI mock/계약·근거·제품/해상도·추가 조건/미지원·스키마 fixture 확장.
- `frontend/tests/analysis-selection.spec.ts` **신규8개**: 요청3사례·세부 변경/보완·복원/중복 실행 방지·자료/면적/해상도·다중 분야/목록 API 실패.
- `frontend/tests/runtime.ts`, `fixtures.ts`, `change-analysis.spec.ts`, `workflow-pages.spec.ts`, `imagery-layout.spec.ts`와 기존 버튼명 사용 테스트: 명시 세부 확인/작은 AOI/새 이동 이름에 맞게 회귀 보완. fixture는 테스트에만 있다. 연결 reset 한정 작은 설정 GET에1회 재시도하며 HTTP 실패·POST·검색/작업/파일 수신을 자동 재실행하거나 가짜 응답으로 바꾸지 않음.
- `README.md`, `docs/WORKFLOW_PAGES.md`, `docs/ANALYSIS_SELECTION.md`, `TEST_REPORT.md`: 현재 우선 계약과 실제 검증/제한.

기존 `purpose_plan.py`·`sensor_catalog.py`의 규칙/사양을 재사용했으며 별도 경쟁 추천 규칙을 만들지 않았다. `pixel_worker.py`, `pixel_raster.py`, `pixel_quality.py`, `change_analysis.py`, `cloud_composite.py`, `cloud_estimate.py`의 과학 계산 알고리즘, 미디어/다운로드·제공처 인증 코드는 변경하지 않았다.

## 실제 실행 명령·결과 — 모두2026-11-03 KST

| 검사/명령 | 시각 | 실제 결과 | exit |
|---|---|---|---|
| backend `LIVE_STAC=0`, `..\.venv\Scripts\python.exe -m pytest -q --disable-warnings` **최종** |**11:28:38–11:29:24**|**494 passed,16 skipped**,1096warnings,43.83초. 최종 온도 영역 비교 입력 계약 포함|**0**|
| frontend `npm.cmd run typecheck` 독립 실행 |**11:22:58–11:23:01**|성공|**0**|
| frontend 격리 production build(아래 명령) |**11:21:19–11:21:44**|성공, `/`·`/processing` 정적 생성. dev 빌드·next-env/tsconfig 보존|**0**|
| 전체 E2E `npx.cmd playwright test --timeout=45000 --workers=2` **최종** |**11:23:02–11:28:33**|**168 passed,9 skipped**,177개 전체,5.5분. 새8개 포함|**0**|
| 현재 서버 재시작 후 health·두 페이지·catalog |11:30|backend/front health·`/`·`/processing`·`/api/analysis/catalog` 모두200.4분야/10세부,5제공처/9컬렉션. 온도 영역 비교 최소1장 확인|0|
| `node test-results/detail-live/verify.mjs current` |**11:30:26 이후**|AI mock + 실제 추천/공개 검색 + 실제3000 브라우저 전달/차단·데스크톱/모바일 확인|**0**|

E2E 환경(frontend cwd): `E2E_BASE_URL=http://127.0.0.1:3019`, `E2E_API_BASE_URL=http://127.0.0.1:8019`, `E2E_OUTPUT_DIR=test-results-detail-final`. 별도 검증 백엔드는 `.env`를 읽지 않고 AI/지명/운영자 접근을 비활성화했다. 검증 후8019/3019만 종료했고 사용자3000/8000은 유지했다.

실제 최종 build 명령(frontend cwd):
```powershell
node --input-type=module -e "import {spawnSync} from 'node:child_process';import {readFileSync,writeFileSync} from 'node:fs';import {frontendEnvironment} from '../scripts/server-env.mjs';const names=['next-env.d.ts','tsconfig.json'];const prior=names.map(n=>readFileSync(n));let code=1;try{const r=spawnSync(process.execPath,['node_modules/next/dist/bin/next','build','--webpack'],{stdio:'inherit',env:frontendEnvironment({...process.env,NEXT_DIST_DIR:'.next-conditions-final',API_BASE_URL:'http://127.0.0.1:8019'})});code=r.status??1;}finally{names.forEach((n,i)=>{if(!readFileSync(n).equals(prior[i]))writeFileSync(n,prior[i]);});}process.exit(code);"
```

초기 실패를 통과로 합산하지 않았다. 최초19개 집중 실행은 검증용8019 서버 부재(ECONNREFUSED)로17실패/1통과/1skip(exit1); 별도 네이티브 서버 기동 후17통과/1실패/1skip(exit1)이었다. A4의 기존 테스트가 AOI 중첩0인 세 번째 장면도 계산 성공해야 한다고 가정해 새 사전 게이트가 정상 차단했다. 이를 잘못된 실행 차단·오래된 응답 폐기 확인으로 보완했다. 이후 전체177개 첫 시도는166통과/9skip/2실패(exit1): 설정 GET의 일시 ECONNRESET(해당 단독 재실행1통과)과 추천 정보가 없는 빈 응답의 UI 예외였다. 설정 GET reset에만 한정한 테스트 전송 재시도/빈 응답 보호 후 위 최종 전체를 재실행해 실패0을 확인했다. 실제 제공처 장애를 fixture로 대체하지 않았다.

## mock·실제 API·브라우저 구분

- **mock/fixture 검증:** 실제 OpenAI/Kakao 대신 테스트 응답으로 일반 더위→열환경/세부 미지정, 지표면 온도→의도/추천 요청/사전 선택, 식생 변화→두 시점/격자·QA 계획, 모호한 다중 분야 수정, 부족 자료 보완, 수신/처리 실패, AI 실패/응답 역전, 상태 복원/중복 실행 금지, 원본만 종료·합성 전처리 ZIP만 종료·NDVI ZIP/레이어를 확인했다. 테스트 파일/바이트는 실제 제공처 원본/계산 완료 증거가 아니다.
- **실제 공개 API 회귀:** 전체 E2E의 실제 A2 Item/HEAD/격자, 추천·Earth Search/다중 제공처 검색·지도/밴드 흐름 통과. 동일 `[126.7,36.4,126.71,36.41]`, UTC `2025-07-20~26`에서 카드/수동 Sentinel-1 각1건, CMR VIIRS 각7건, S2 각2건을 실제 반환했다. 최종 실검색 테스트의 HTTP 오류 로그는 빈 목록이었다. 검색 성공을 원본 인증/QA/분석 성공으로 확대하지 않는다.
- **현재3000 실제 브라우저:** OpenAI 응답만 명시적 mock으로 분리하고 나머지 추천/목록/실제 Earth Search 검색을 사용했다. 위 AOI/UTC 기간, `detail_intent=vegetation_change`, `temporal_mode=change`가 실제 검색 요청에 전달됐다. `S2B_52SBF_20250725_0_L2A`(2025-07-25, sentinel-2b)와 `S2C_52SBF_20250720_0_L2A`(2025-07-20, sentinel-2c)2건, 각각 기하 중첩100%를 실제 반환했다.
- **현재 화면 전달:** `/processing`의 식생 변화가 미리 선택되고 같은 요청/자료를 유지했다. 확인 후 관련 전처리 계획이 나타났지만, **플랫폼이 달라 자료 보완 필요**를 표시했다. 원본 미확보도 유지했고 자료를 자동 교체/분석하지 않았다.390px 가로 넘침 없음, 라디오18px/shrink0. `test-results/detail-live/report.json`과 `collection.png`, `processing-desktop.png`, `processing-mobile.png`를 저장하고 화면을 확인했다.
- **미실행:** 실제 유료 OpenAI/모델 응답·Kakao·운영자 인증 파일·이 단계의 실제 전체 원본 다운로드·실제 다중 원본 QA/합성/NDVI/ML 계산은 수행하지 않았다. backend LIVE16개, E2E9개(실제 A3/A4/관측 합성/ML4개 및 opt-in 실제 파일5개)는 제외했다. 필요한 대용량 여러 밴드 수신/인증을 이번 검증으로 승인받거나 대신 수행하지 않았다. 과거 실제 SCL 전체 수신 기록을 이번 단계 다운로드 성공 증거로 재사용하지 않는다.

기존 OpenAI 경로의 strict/nullable 구조화 계약은 [공식 Structured Outputs 문서](https://developers.openai.com/api/docs/guides/structured-outputs)를 확인해 확장했다. 키·모델·계정 접근은 바꾸지 않았으며 실제 계정 응답 성공을 주장하지 않는다.

## 반영과 사용자 확인 순서·남은 제한

사용자 확인 `진행 중 작업 없음 — 검증 후 재시작`에 따라 경로/부모 자식 관계를 확인한 프로젝트 wrapper47220과 그 자식만 종료하고 `start.cmd`로 재실행했다. 새 wrapper7776, 최종3000=14596/8000=9484. 다른 앱·서버·편집·환경 파일은 종료/변경하지 않았다. 현재 주소는 `http://127.0.0.1:3000/`, 다음 페이지는 `/processing`이다.

1. 수집에서 “더운 곳을 보고 싶어”, “지표면 온도를 보고 싶어”, “식생 변화를 보고 싶어” 등의 원문을 입력한다. 자동 AI는 기존 비용 안내/설정을 사용하므로 직접 사용 시 실제 사용량이 발생할 수 있다. 이번 개발의 해당 문장 해석 증거는 mock이다.
2. 큰 분야·요약·보존한 세부 의도, 실제 지역/AOI/UTC 기간을 확인한다. 모호한 날짜/지명·수동 충돌은 기존 확인 절차를 따른다. 적합한 제품을 골라 명시 검색한다. 원본만 다운로드하고 종료해도 된다.
3. `세부 분석 선택으로`→질문/자료/산출물/지원 상태 확인→원문 의도 또는 다른 후보를 확인한다. 부족하면 `같은 조건으로 자료 보완하기`로 돌아간다. 같은 센서 계열이라는 이유로 S2B/S2C를 현재 동일 플랫폼 엔진에 자동 투입하지 않는다.
4. 호환 자료/원본 수신/필수 밴드와 실제 QA 게이트를 통과할 때만 관련 기존 처리를 실행한다. 전처리 ZIP만 다운로드해 종료하거나 지원되는 원본 쌍의 NDVI로 이어간다. 합성/ML ZIP→NDVI 자동 입력은 미구현이다.

기존 NASA HLS HTTP400·다른 제공처 인증 수리·전면적 분석·다중 worker 영속 작업 저장소는 이번 범위 밖이다. 서버 메모리 작업/ZIP15분·세션/재시작 복원 한계는 이전 계약 그대로다. 실제 API/health200이나 UI 연결을 전체 원본 수신·전체 분석 성공으로 보고하지 않는다.

---

# 데이터 수집 / 전처리·분석 페이지 분리 — 2026-11-03 최종 검증

이번 변경은 기존 화면·상태·처리 엔진의 재구성이다. 사용자 편집과 현재 색상·글꼴을 유지했으며, 자격증명/.env·이용조건 승인·제공처 어댑터·분석 알고리즘은 변경하지 않았다. 신규 과학 분석·인증 수리·유료 AI·배포·push는 수행하지 않았다. 구체 상태 계약은 [WORKFLOW_PAGES](docs/WORKFLOW_PAGES.md)를 따른다. 아래 이전 보고들은 당시 실행 기록이다.

## 현재 기능과 검증 경계

| 기능 | 이번 확인 결과 |
|---|---|
| 수집 `/` | 기존 AI 조건·목적/AOI/UTC 기간·추천·검색·날짜/지도·미리보기·밴드·원본 UI 유지. mock 회귀 및 현재 사이트의 실제 공개 검색/preview/작은 원본 저장 검증 |
| 처리 `/processing` | 동일 조건·장면·밴드·수신 기록 전달, 상단 요약/돌아가기, 품질→선택 전처리→분석/내보내기. 미선택 진입/미확보/미지원 차단 검증 |
| A2 조건 확인 | 기존 canonical Item·공개 Asset HEAD·격자 검사 재사용. 단위/통합 및 실제 공개 Item E2E 검증. HEAD는 전체 파일 수신 증거가 아님 |
| A3 품질·A4 NDVI | 기존 작은 AOI/S2 L2A 엔진 유지. pytest 계산 fixture와 UI mock 내보내기/실패/무효화 검증. 이번 변경 후 실제 원본 쌍의 전체 처리 흐름은 미실행 |
| 관측 합성 전처리 ZIP | 기존 실측 픽셀 선택·SCL/밴드·격자·출처/날짜·마스크 엔진 재사용. fixture UI 계획→확인→작업→전처리 ZIP만 저장·종료 검증. 실제 다중 원본 전체 실행은 미실행 |
| ML | 기존 지원 S2 식생 한 시점의 제한된 추정만. 관측/추정/남은 결측·검증 한계 유지, mock/엔진 fixture 검증. 실제 ML 실행은 미실행 |
| 독립 AOI 자르기·임의 CRS/해상도 변경·단독 마스킹 ZIP | 미구현 안내. 기존 합성/NDVI 내부 처리와 구분 |
| 합성/ML 산출물을 NDVI 변화 입력으로 자동 연결 | 미구현. 분석 페이지는 호환되는 원본 쌍의 기존 NDVI만 실행 |
| HLS/VIIRS/SAR/열환경 픽셀 처리 | 미구현/기존 제한 유지. 검색·파일 접근과 처리 지원을 혼동하지 않음 |
| 제공처 인증/HLS400 | 이번 수리 범위 아님. 이전 NASA browse/B04 HTTP400을 해결됐다고 표시하지 않음. 실제 NASA 인증 원본은 이번에 재검증하지 않음 |

## 변경 파일과 역할

- `frontend/src/app/page.tsx`, `frontend/src/app/processing/page.tsx`, `frontend/src/app/layout.tsx`: 두 라우트와 지속 Workspace. 페이지마다 폼/검색 상태를 복제하지 않음.
- `frontend/src/components/WorkflowWorkspace.tsx`: 기존 page의 조건·추천·검색·선택·비교·단일 AOI·지도 상태를 이동, 수집/처리 화면 연결, 복원/무효화/작업 기록.
- `frontend/src/components/WorkSummary.tsx`: 선택/밴드/원본 수신/링크 목록/QA 상태와 주요 행동, 복원 작업의 상태·취소·다운로드.
- `frontend/src/lib/workSession.tsx`, `frontend/src/lib/workSnapshot.ts`: 공통 작업 컨텍스트와 제한된 sessionStorage 메타데이터. 토큰·쿠키·비밀번호·서명/query URL·receipt·실행 확인·바이너리 제외. 행정경계 링 보존, 중단 수신은 실패로 복원.
- `frontend/src/lib/useConditionInput.ts`: 기존 AI/수동 조건의 복원 경로. 새로고침에서 자동 유료 재해석하지 않고 미확정 문장은 차단/재확인.
- `frontend/src/components/Results.tsx`, `AssetDownloads.tsx`, `ManagedAssetAccess.tsx`: 공통 밴드 선택·링크 목록 기록·전체 응답 수신 기록. 선택/preview/Range/txt/전체 원본 수신 구분.
- `frontend/src/components/NaturalWorkflow.tsx`, `SceneComparison.tsx`, `AnalysisConditions.tsx`, `PixelQuality.tsx`, `ChangeAnalysis.tsx`, `EstimatedImage.tsx`: 기존 API/계산 엔진을 처리 페이지에 재배치, 실제 수신/필수 밴드/지원 조건 게이트, 처리 설정 공유, QA→선택 전처리→분석 내보내기·작업 기록/늦은 응답 폐기.
- `frontend/src/lib/workflow.ts`: 기존 S2/NDVI 지원 판정 재사용. 과학 추천 규칙 추가 없음.
- `frontend/src/components/MapPanel.tsx`: 페이지 너비 변화에 resize. 기존 선택/날짜/레이어/수동 AOI 유지.
- `frontend/src/app/globals.css`: 기존 토큰/색/폰트를 유지한 경로 숨김·내비게이션·처리 폭·모바일 배치만 추가.
- `backend/app/work_sessions.py`, `backend/app/main.py`, `backend/app/cloud_jobs.py`: 기존 합성/ML 계획·실행·조회·취소·ZIP의 브라우저 세션 소유권. 새 과학 API나 계산 모델 없음. HttpOnly/SameSite Strict 세션 쿠키, 서버 메모리 서명키/최대8시간. 외부 Origin 변경 요청 차단, 다른 세션/서버 재시작 후404.
- `backend/tests/test_work_sessions.py`: 두 작업 종류의 소유권·위조/재시작·쿠키/Origin mock 검사3개.
- `frontend/tests/workflow-pages.spec.ts`, `workSnapshot.spec.ts`: 새 흐름7개/보관3개. mock 실제 파일 수신→전달/게이트·전처리만 종료·분석 ZIP·back/reload·불확정 문장·보안/경계 링 검증.
- `frontend/tests/runtime.ts`, `change-analysis.spec.ts`, `pixel-quality.spec.ts`, `cloud-workflow.spec.ts`, `estimate-mode.spec.ts`, `imagery-explorer.spec.ts`, `imagery-layout.spec.ts`, `next-work.spec.ts`, `providers.spec.ts`, `search.spec.ts`, `hls.spec.ts`, `earthdata-auth.spec.ts`: 이동된 UI의 기존 회귀 검사 보완. 기존 엔진 mock에는 TEST_ONLY 수신 이력을 명시 준비하며 실제 서비스 fallback으로 사용하지 않음. 공개/운영자 설정에 의존하던 auth fixture를 context 전체 mock으로 격리, HLS400은 disabled 버튼을 검사.
- `README.md`, `docs/WORKFLOW_PAGES.md`, `TEST_REPORT.md`: 사용 흐름·정확한 지원/복원 한계·실행 근거.

API JSON/과학 입력 스키마는 유지했다. 합성/ML 작업 API는 같은 HttpOnly 브라우저 세션이 필요하다. 브라우저 수신 기록은 인증 증거/서버 파일 캐시가 아니며, 실제 처리 서버는 canonical Item·접근·밴드·범위·QA/격자/보정 조건을 다시 검사한다. `pixel_worker.py`, `pixel_raster.py`, `pixel_quality.py`, `cloud_composite.py`, `cloud_estimate.py`의 계산 알고리즘은 수정하지 않았다.

## 최신 실행 명령·결과 (모두 2026-11-03 KST)

| 명령/검사 | 시각 | 실제 결과 | 종료 코드 |
|---|---|---|---|
| backend: `LIVE_STAC=0` 후 `..\.venv\Scripts\python.exe -m pytest -q --disable-warnings` |10:01:33–10:02:28|**483 passed,16 skipped**,1096 warnings,53.77초|0|
| frontend: `npm.cmd run typecheck` 독립 실행 최종 |10:38:47–10:38:50|성공. 테스트 선택자 보완과 프로젝트 재시작 후 재검사|0|
| frontend: 분리 dist에서 `next build --webpack` (명령 아래) |10:18|성공, `/`·`/processing` 포함. 실행 중 dev 빌드와 next-env/tsconfig 보존|0|
| 관련 E2E: `npx.cmd playwright test tests/earthdata-auth.spec.ts tests/hls.spec.ts tests/workflow-pages.spec.ts tests/workSnapshot.spec.ts --timeout=45000` |10:16–10:17|**23 passed**|0|
| 전체 E2E 최종: 아래 env 후 `npx.cmd playwright test --timeout=45000 --workers=2` |**10:31:00–10:34:49**|**160 passed,9 skipped**,3.8분.169개 전체 수집/실행, 실패0|**0**|
| 프로젝트 재시작 후 `/`, `/processing`, backend/front health, `/api/catalog` |10:35|각HTTP200,5제공처/9컬렉션|0|
| 실제 새 Edge 브라우저: `node test-results/workflow-live/verify.mjs` |10:36:05–10:36|실검색/실preview/작은 원본 전체 저장/처리 전달/미지원 실행 차단·모바일 확인|0|
| 로컬 rasterio 전체 `src.read()` 형식 검사 |10:36:32|아래 SCL 파일 전체 디코딩 성공|0|

최종 E2E 환경: `E2E_BASE_URL=http://127.0.0.1:3019`, `E2E_API_BASE_URL=http://127.0.0.1:8019`, `E2E_OUTPUT_DIR=test-results-workflow-complete` (frontend cwd). 분리 production frontend/백엔드로 실행했다. 테스트용 백엔드는 환경 파일을 읽지 않고 AI·지명·운영자 인증을 비활성화했고, 기존 실제 공개 검색은 허용했다. 검증용3019/8019는 끝난 뒤 종료했으며 현재 사용자3000/8000만 유지한다.

분리 production build 실제 명령(frontend cwd, Node env 필터 재사용):
```powershell
node --input-type=module -e "import {spawnSync} from 'node:child_process';import {readFileSync,writeFileSync} from 'node:fs';import {frontendEnvironment} from '../scripts/server-env.mjs';const names=['next-env.d.ts','tsconfig.json'];const prior=names.map(n=>readFileSync(n));let code=1;try{const r=spawnSync(process.execPath,['node_modules/next/dist/bin/next','build','--webpack'],{stdio:'inherit',env:frontendEnvironment({...process.env,NEXT_DIST_DIR:'.next-conditions-final',API_BASE_URL:'http://127.0.0.1:8000'})});code=r.status??1;}finally{names.forEach((n,i)=>{if(!readFileSync(n).equals(prior[i]))writeFileSync(n,prior[i]);});}process.exit(code);"
```

이전 시도도 성공으로 합산하지 않았다. dev 기반 전체는157통과/9skip/3실패(exit1): auth fixture의 두 탭/StrictMode 응답 순서와 HLS disabled 버튼 기대를 수정하고 관련23개 재검사 통과. 그 다음 production 단일 worker 전체는158통과/9skip/2실패(exit1): 화면 중앙을 지리적 촬영범위로 가정한 지도 테스트와 숨겨진 처리 요약까지 포함한 모바일 순서 선택자를 보완했다. 각각 집중1개 검사도 통과했고, 이후 위 **최종 전체160통과**로 다시 확인했다. 오래된 validation backend를 발견해 중단한 production 검사 시도는 완료된 전체 검사로 집계하지 않았다.

## mock / 실제 API / 실제 브라우저 구분

- **mock/fixture:** AI 자동 조건·실제 엔진 수치 테스트, 전처리/분석 ZIP UI, 후보/실패/세션/늦은 응답·모바일·보관 검증. fixture 파일 수신과 엔진 실행은 실제 제공처 다운로드 성공으로 보고하지 않는다.
- **실제 공개 API 포함 E2E:** A2 실제 Item/HEAD/격자, 다중 제공처 검색, 추천/검색/지도/밴드 회귀. 같은 bbox `[126.7,36.4,126.71,36.41]`, UTC `2025-07-20~2025-07-26`의 카드/수동 검색에서 Sentinel-1 각1건, CMR VIIRS 각7건, S2 각2건을 실제 반환했다. 전체 실검색 테스트의 최종 HTTP 오류 로그는 빈 목록이었다. 이전 dev 검사에서 preview429가 있었으므로 모든 장면의 preview/원본 성공으로 일반화하지 않는다.
- **현재 사이트 실제 새 브라우저:** 위 bbox/UTC 기간, 식생→Sentinel-2 MSI→명시 검색2건. 선택 `earth-search / sentinel-2-l2a / S2B_52SBF_20250725_0_L2A`, 촬영 `2025-07-25T02:27:32.626000Z`. 제공처 preview 실제 이미지343×343 디코딩. 선택 밴드SCL만 접근 확인(206/전체 크기 확인) 후 명시 다운로드. `SCL.tif` **1,591,434바이트 전체 수신·브라우저 저장** 및 파일 내용 디코딩 성공. 단순 Range/HEAD200을 전체 다운로드 성공으로 집계하지 않았다.
- **파일 검증:** `test-results/workflow-live/original-scl.tif`, GTiff,5490×5490,1밴드,uint8,EPSG:32652,`src.read()`30,140,100개 값 전체 디코딩 성공. 이는 파일 형식 확인이며 AOI 픽셀 QA/NDVI 계산이 아니다.
- **페이지/모바일:** 실제 `/processing` 전환과 같은 장면·밴드·AOI/UTC 요약 유지, SCL만 있어 필수 밴드 미확보 처리 차단,390px 가로 넘침 없음. 스크린샷 `test-results/workflow-live/{collection-desktop,processing-desktop,processing-mobile}.png` 확인. 검증 도구 첫 실행은 원본/preview 성공 후 Next 경로 전환 대기가 누락돼 handoff미확인이었다. 도구에 실제 URL/heading 대기와 실패 조건을 추가해 재검증했다. 같은 작은 SCL 파일을2회 수신(합계3,182,868바이트)했고 대용량/일괄 수신은 하지 않았다.
- **미실행:** backend LIVE16개. E2E9개는 실제 A3/A4/관측 합성/ML4경로와 opt-in 공개/인증 파일5경로다. 새 수신 게이트를 충족하려면 여러 대용량 밴드를 먼저 받아야 하므로 자동 실행하지 않았다. 실제 유료 AI/Kakao/NASA 인증 원본/모든 제공처 전체 다운로드·실제 다중 원본 분석을 이번 증거로 주장하지 않는다. 유료 AI 호출0, 실제 Kakao 호출0.

## 현재 사이트 확인 순서와 남은 제한

1. `http://127.0.0.1:3000/`에서 기존 AI 자연어 또는 직접 조건 입력→AOI/기간 확인→추천 제품 선택→명시 검색. 이번 개발 검증은 유료 호출을 피하려고 직접 조건을 사용했다.
2. 장면·밴드를 선택한다. `원본 다운로드`는 해당 Asset 패널로 이동한다. `선택 원본 접근 확인`→파일별 `원본 다운로드`를 명시 클릭한다. 링크 목록.txt/preview 저장을 원본 확보로 오인하지 않는다. 여기서 종료 가능하다.
3. `선택 영상으로 전처리·분석`→`/processing`. 같은 조건 요약 확인→품질→필요한 기존 관측 합성→전처리 ZIP만 저장/종료 또는 호환 원본의 NDVI·내보내기. 필수 밴드/원본이 없으면 수집으로 돌아가 선택·확보한다. 일반 재투영이나 합성 ZIP→NDVI 입력을 구현된 것처럼 제공하지 않는다.
4. back/reload는 메타데이터/같은 탭 작업 기록을 복원하며 검색·다운로드·AI·분석을 자동 재실행하지 않는다. 브라우저가 실제 파일 현존/OS 저장을 보증하지 않으며 서버는 원본을 별도 범위 읽기한다. 새로고침하면 메모리 NDVI ZIP/지도 픽셀은 복원할 수 없다.
5. 기존 작업/계획/ZIP은 서버 메모리15분 보관, 서명키도 메모리다. 서버 재시작·만료·다른 세션이면 조회 불가다. 익명 브라우저 세션 소유권은 사용자 계정/Supabase/다중 worker 영속 작업 저장소를 구현한 것이 아니다. 공개 다중 사용자 영속 운영은 후속 작업이다.

사용자 확인(진행 작업 없음/검증 후 재시작 승인)에 따라 확인된 기존 프로젝트 wrapper22944와 그 자식만 종료하고 `start.cmd`로 재시작했다. 새 wrapper47220, 최종 리스너3000=14316/8000=27224. 다른 앱·서버·VS Code 편집은 종료하지 않았다. 최신 health/페이지 성공은 HLS400 또는 실제 전체 분석 완료의 증거가 아니다.

---

# HLS HTTP 400 후속 진단·수정 — 2026-11-02 17:40~17:59 KST

**400 정상화는 미완료다.** 실제 발생 위치를 확인하고 안전한 진단·부분 응답 검증·오류 설명을 보완했다. mock 통과/서버 재시작을 실제 NASA 파일 성공으로 보고하지 않는다. 아래 과거 인계·테스트 기록은 보존한다. 이전 PHASE 작업의 변경(test_live.py의 명시 purpose_type 등), 다른 사용자 편집·디자인·환경 파일은 이번 범위에서 변경/복구하지 않았다.

## ① 확인된 사실과 미확정 원인

CMR가 현재 반환한 HTTPS browse를 그대로 사용했다. 대상 호스트는 `data.lpdaac.earthdatacloud.nasa.gov`. L30은 `/lp-prod-public/HLSL30.020/<original_id>/<original_id>.jpg`, S30은 `/lp-prod-public/HLSS30.020/<original_id>/<original_id>.jpg`다. 최소 무인증 GET과 앱 경로 모두 **첫 응답(hop0) HTTP400 / application/json / Content-Length0 / 실제 본문0바이트 / redirect0회**였다. 최초로 달라지는 응답 단계는 없었다. 다른 제품의 실제 표본(S30)도 같아 L30 한 파일만의 문제라는 근거는 없다.

보호 원본은 같은 호스트의 `/lp-prod-protected/<제품>.020/<original_id>/<original_id>.B04.tif`. 기존 DPAPI/SQLite active grant를 정상 서버 전송 경로로 읽어 보냈다. **Range=true / Authorization 존재=true**인 첫 응답이 동일400이었다. Content-Range 없음, TIFF 시그니처 확인 불가, 전체 크기 미확인이다.400은401/403이 아니므로 인증 실패·토큰 만료로 분류하거나 토큰을 갱신하지 않았다. 제공처 내부/네트워크상의 구체 원인은 아직 알 수 없다. 주소 인코딩·CMR URL 선택 오류도 입증되지 않아 hls.py/cmr.py를 수정하거나 다른 호스트로 대체하지 않았다.

공식 [HLS 접근 안내](https://hls.gsfc.nasa.gov/data-access-and-tools/)와 [EDL User Token 문서](https://urs.earthdata.nasa.gov/documentation/for_users/user_token)를 재확인했다. 해당 문서는 현재 표본의400 원인을 설명하지 않는다. 다음 진단에는 LP DAAC에 아래 공개 Item/파일 경로, UTC2026-11-02 08:45 전후, 첫 응답400·본문0바이트·무리다이렉트라는 기록을 제시하고 제공처 로그의 처리 이유 확인이 필요하다. 필요하면 별도 네트워크의 같은 공개 browse 비교로 재현 범위를 좁힐 수 있다. 토큰/쿠키/서명 URL 전달은 필요하지 않다.

## ② 이번 변경 파일·API

- `backend/app/provider_transfer.py`: 명시 로컬 진단 문맥. 요청 단계/hop/허용 호스트/공개 HLS 경로/상태/Content-Type/선언·실수신 크기/숫자 Content-Range/Range·인증 존재 여부만 수집. ContextVar로 요청 격리,64행 상한. query·userinfo·Location·본문·비밀값 미보관. 평상시 로그/API 미노출.206의 범위 시작·끝·전체 크기·길이 검증 강화.
- `backend/app/media_access.py`: 잘못된 Content-Range와 HTTP400을 정확히 설명.400을 인증 성공/실패로 단정하지 않고, 미리보기/원본 수신 실패로 표시.
- `scripts/diagnose-hls-local.py`: 기존 서버 env 로더를 쓰는 제한된 진단. 기존 저장 grant만 사용, 신규 채택/갱신/회전 거부. canonical CMR 조회→최소 browse/앱 비교→B04 probe→크기 확인 후 제품별 최대1개/10MiB 전체 수신·전체 TIFF 디코딩.429/로그인/동의/redirect/크기 오류 중단.실제 실패 시 runner도 실패 exit 반환.
- `backend/tests/test_transfer_diagnostics.py`, `test_hls_diagnostic_runner.py`: 비노출·문맥 격리·64행 상한·교차 호스트 인증 제거·400 분류·206 검증·Range 무시 상한·갱신/초기 채택 거부·429/HTML 중단을 mock으로 검사.
- `frontend/tests/hls.spec.ts`: HTTP400에서 원본 다운로드 버튼/완료 상태를 만들지 않고 날짜·제품 선택을 유지하는 회귀 추가.
- `docs/HLS_ADAPTER_DESIGN.md`, 본 보고서: 최신 실제 실패 근거·재현·남은 조치 기록.
- 새 endpoint/프런트 타입/제품/분석 엔진/디자인 변경 없음. 기존 status/provider_error와 http_status=400 계약 유지, 전송 오류 코드에 invalid_content_range 추가.

## ③ 실제 실행한 검증

시각은 KST, 해당 호출을 실행/결과 확인한 시간 범위다. 외부 파일 실패는 테스트 fixture로 대체하지 않았다.

| 명령/검사 | 시각 | 실제 결과 | exit |
|---|---|---|---|
| backend `LIVE_STAC=0`, `..\.venv\Scripts\python.exe -m pytest -q --disable-warnings` 최종 |17:58:44~17:59:14|**480 passed,16 skipped**,1096warnings,28.55초|0|
| 신규 진단 runner 단위 `..\.venv\Scripts\python.exe -m pytest tests/test_hls_diagnostic_runner.py -q --disable-warnings` |17:48:41|4 passed,1warning,1.40초. 위 최종 전체에도 포함|0|
| frontend `npm.cmd run typecheck` 최종 |17:50~17:51|성공|0|
| 분리 production build(아래 명령) |17:45~17:46|성공. 프런트 제품 코드 변경 없음. next-env.d.ts/tsconfig.json 기존 내용 보존|0|
| frontend `E2E_OUTPUT_DIR=test-results-hls-400-final`, `npx.cmd playwright test tests/hls.spec.ts tests/media-access.spec.ts tests/public-data.spec.ts --timeout=45000` 최종 |17:54~17:55|**23 passed,4 skipped**,54.6초. mock 검색/파일/밴드·오류·공개 경로·모바일 회귀. LIVE 전용4개는 미실행|0|
| 기존 env 로더→`scripts/diagnose-hls-local.py` 실제 NASA |17:45:18~17:46|검색 L30 1/S30 2 성공. 최소/앱 browse400, 인증B04 probe400. 전체 파일0개|runner2, PowerShell 도구1|
| 공개 경로 TestClient 실제 회귀(下記) |17:49~17:50:16|Earth Search/PC S2 검색·preview·probe 성공, 작은 SCL 전체 수신·GTiff 전체 디코딩 성공|0|
| `node test-results/hls-diagnostic/browser-live.mjs` 현재3000 실제 UI |17:54|실검색 L30 1/S30 2, bbox/UTC/제품 일치, B04 선택, 실제 browse400 설명, 원본 버튼0, 모바일 가로 넘침 없음, 실제 유료AI0|0|
| 위 UI 진단의 첫 시도 |17:52~17:53|미리보기 영역에 스크롤하기 전 지연 로딩을 기다린 검증 도구의 Timeout. 도구 수정 후 위 재실행. 앱 성공으로 집계하지 않음|2|

전체 E2E·이전 Phase LIVE16개는 이번 HLS 변경 후 다시 실행하지 않았다. 위 관련27개와 별도 실제 NASA/공개 경로 검증만 이번 근거로 삼는다. 최근 큰 파일 전체 검증이나 실제 HLS TIFF decode는 수행하지 않았다.

실제 NASA runner 명령(루트, 비밀값 출력 없음):
```powershell
node --input-type=module -e "import {spawnSync} from 'node:child_process';import {childEnvironments} from './scripts/server-env.mjs';const r=spawnSync('.venv/Scripts/python.exe',['scripts/diagnose-hls-local.py'],{env:childEnvironments(process.cwd()).backend,stdio:'inherit',windowsHide:true});process.exit(r.status??1);"
```
진단 원본 실행 이후 runner의 중단 조건·출력 요약·인증 revision 변경 시 신규 grant 채택 차단을 보완했고 해당 보완은 runner mock5개/최종 전체 pytest로 검증했다. 동일400을 반복하기 위해 실제 NASA를 다시 호출하지 않았다. 구체 trace는 `test-results/hls-diagnostic/report.json`이다. .env 원문 로컬 해시 대조 결과 unchanged=true, 값/해시는 출력하지 않았다.

production build(frontend, 서버 비밀 제거):
```powershell
node --input-type=module -e "import {spawnSync} from 'node:child_process';import {readFileSync,writeFileSync} from 'node:fs';import {frontendEnvironment} from '../scripts/server-env.mjs';const names=['next-env.d.ts','tsconfig.json'];const prior=names.map(n=>readFileSync(n));let code=1;try{const r=spawnSync(process.execPath,['node_modules/next/dist/bin/next','build','--webpack'],{stdio:'inherit',env:frontendEnvironment({...process.env,NEXT_DIST_DIR:'.next-conditions-final',API_BASE_URL:'http://127.0.0.1:8000'})});code=r.status??1;}finally{names.forEach((n,i)=>{if(!readFileSync(n).equals(prior[i]))writeFileSync(n,prior[i]);});}process.exit(code);"
```

公開 경로는 env 파일을 읽지 않는 별도 Python TestClient에서 위 bbox/기간으로 각 컬렉션 max_items=1 검색→canonical `/media/inspect`→확인된10MiB 이하 SCL만 `/media/downloads/<receipt>` 전체 수신했다. 출력에는 receipt/URL/키 값이 없다. `test-results/hls-diagnostic/public-regression.json`에 기록했다:

- Earth Search `S2B_52SBF_20250725_0_L2A`, scl: **1,591,434 bytes**, GTiff5490×5490, 전체 배열 디코딩. HLS 원본 성공이 아니라 별도의 공개 품질 마스크 회귀다.
- PC `S2B_MSIL2A_20250725T021539_R003_T52SBF_20250725T041758`, SCL: **1,474,350 bytes**, GTiff5490×5490, 전체 배열 디코딩. 익명 SAS는 기존 서버 경로 내부에서만 사용.

## ④ HLS 단계별 판정·안전한 반영

| 단계 | L30 | S30 |
|---|---|---|
| CMR 실제 검색 |성공1건|성공2건|
| 실제 browse 이미지 표시 |실패400·본문0|실패400·본문0|
| 기존 인증 원본 Range |실패400·인증 성공 미확인|실패400·인증 성공 미확인|
| 원본 전체 수신·TIFF 읽기 |미실행(크기 미확인)|미실행(크기 미확인)|
| 실제 HLS 원본 브라우저 저장 |미실행|미실행|

mock E2E의 다운로드 이벤트/샘플 저장은 위 실제 NASA 성공이 아니다. 링크 목록.txt는 경로 안내 목록이며 원본 TIFF 저장이 아니다. 원본 전체 수신과 browse 이미지 저장도 별개다. 이번에는 실제 HLS 파일이 없으므로 파일 저장 성공을 주장하지 않는다.

사용자의 현재 작업 부재·재시작 승인을 받은 뒤, 부모 관계/프로젝트 실제 경로/3000·8000 포트를 대조했다. 기존 wrapper33616/런처15120 및 그 자식만 종료하고17:51:59 `.\start.cmd`로 시작했다. 새 wrapper4404, 백엔드20860/8000, 웹21844/3000. 다른 서버/편집기는 종료하지 않았다. backend health·웹 health200, `/catalog`와 `/api/catalog`200(5제공처/9컬렉션). 실제 접속 주소는 **http://127.0.0.1:3000/**. 자격증명·재제공 플래그·허용 호스트·TLS·디자인 변경, 유료AI·배포·push 없음.

## ⑤ 사용자 재현 순서

1. 현재 주소 새로고침→목적 직접 선택 `식생`→시작2025-07-20/종료2025-07-26(UTC).
2. 좌표 서126.7/남36.4/동126.71/북36.41→좌표 적용.
3. `NASA HLS L30 · Landsat · v2.0`(추천 hls_l30) 또는 `NASA HLS S30 · Sentinel-2 · v2.0`(hls_s30) 선택→명시적 위성영상 검색.
4. L30 촬영일2025-07-23의 `G3625879681-LPCLOUD / HLS.L30.T52SBF.2025204T021054.v2.0`, S30 촬영일2025-07-25의 `G3627467473-LPCLOUD / HLS.S30.T52SBF.2025206T021539.v2.0` 선택.
5. 날짜별 실제 영상의 미리보기 영역으로 스크롤하면 현재 실제 HTTP400·인증 원인 미확정 안내가 나온다. 재시도 버튼을 반복 클릭하지 않는다.
6. 원본/밴드 패널에서 B04를 확인한다. `선택 원본 접근 확인`도 현재 실패이므로 원본 다운로드는 가능으로 표시되지 않는다. 링크 목록 저장은 원본 다운로드가 아니다.

## ⑥ 남은 작업

제공처가400을 반환한 구체 이유를 LP DAAC에서 확인해야 한다. 확인 전에는 토큰 교체/추측 S3 주소/광범위 redirect 허용/다른 제공처 HLS 연결로 우회하지 않는다. 응답이 정상화되면 같은 표본에 대해 Range/Content-Range/TIFF 확인→확인 크기10MiB 이하 한 파일 전체 수신/디코딩→쿠키 없는 새 브라우저의 명시 저장을 이어 검증한다. 해당 크기 파일이 없으면 예상 크기와 추가 승인을 먼저 보고한다. HLS 픽셀 QA/NDVI/합성/ML은 여전히 범위 밖이다.

---

# NASA HLS L30/S30 검색·미디어 연결 검증 — 2026-11-02 (KST)

## 결과 판정

기존 Next.js·MapLibre·FastAPI, 단일 목적 추천 규칙·AOI/UTC 기간·CMR·장면/밴드 선택·미디어 receipt·Earthdata 사용자 OAuth/운영자 인증을 확장했다. 새 앱/분석 엔진/GIBS 타일/가짜 이미지를 만들지 않았다. 기존 사용자 변경과 gpt-4o/키 설정을 보존했다. 유료 AI 호출·계정/키 발급·AWS 비용 활성화·배포·push는 하지 않았다.

| 항목 | 코드·mock | 실제 제공처/현재 웹사이트 |
|---|---|---|
| HLSL30/HLSS30 v2.0 등록·추천·선택·검색 | **완료**. 식생/수역/도시 광학 후보, 열환경 추천 제외 | **성공**. 실제 CMR L30 1건/S30 2건, 현재3000에서도 같은 결과 |
| 실제 제공 browse 연동 | **완료**. CMR browse만·없음/오류 구분·전체 이미지 형식 검사 | **실패**. 두 표본 LP DAAC HTTPS browse가 HTTP400 반환. CMR S3 browse도 진단 요청에서 무인증403. 가짜/다른 장면으로 대체하지 않음 |
| NASA 운영자 자격 설정·암호화 보관 | **완료**, 사용자 명시 승인 후 적용·DPAPI/SQLite 기존 저장소 재사용 | 설정 인식/로컬 state=active. **실제 NASA 인증 성공을 뜻하지 않음**. connected=false/파일별 접근 확인 필요 |
| 보호된 원본 밴드 서버 다운로드 | **완료**. 밴드 매핑·권한/만료/HTML/redirect/크기·범위 확인/전체 수신 구분 | **접근 실패**. 실제 Bearer 요청의 B04 probe가 두 제품 모두 HTTP400. 크기 확인 불가로 **전체 원본 다운로드/GTiff 실파일 검증 미실행** |
| HLS 픽셀 QA·분석·합성·ML | **범위 밖·미구현** | 기존 Sentinel-2 전용 처리에 자동 적용하지 않음 |

HTTP400은 빈 application/json 응답이었으며 현재 근거만으로 토큰 만료·권한 부족·제공처 장애 중 원인을 확정하지 않는다. 로컬 저장 성공, JWT exp 확인, 검색 성공, 파일 인증 성공은 다른 판정이다. 새 토큰을 요구하거나 게이트/요청자 비용 경로로 우회하지 않았다.

## 공식 제품·밴드·권한 근거

2026-11-02 무인증 CMR collections.umm_json의 실제 응답으로 확인했다:

| 앱 ID | 공식 컬렉션/버전 | CMR Concept ID | 서버 제품 경로 | DOI |
|---|---|---|---|---|
| hls-l30-002 | HLSL30 / 2.0 | C2021957657-LPCLOUD (조회 revision98) | HLSL30.020 |10.5067/HLS/HLSL30.002|
| hls-s30-002 | HLSS30 / 2.0 | C2021957295-LPCLOUD | HLSS30.020 |10.5067/HLS/HLSS30.002|

근거: [CMR L30 UMM](https://cmr.earthdata.nasa.gov/search/collections.umm_json?concept_id=C2021957657-LPCLOUD), [S30 UMM](https://cmr.earthdata.nasa.gov/search/collections.umm_json?concept_id=C2021957295-LPCLOUD), [NASA L30 제품 사양](https://hls.gsfc.nasa.gov/products-description/l30/), [S30 밴드 대응·격자·scale](https://hls.gsfc.nasa.gov/products-description/s30/), [HLS 접근 안내](https://hls.gsfc.nasa.gov/data-access-and-tools/), [공식 인용 안내](https://hls.gsfc.nasa.gov/documents/).

NASA 공개 카탈로그의 accessLevel=public 및 정부 저작물 이용 안내, CMR UseConstraints의 NASA data-use-policy 링크를 확인했다. Earthdata 정책 본문 일부 URL은403/접근 실패였으므로 그 본문 전체를 검증했다고 하지 않는다. 이 근거와 대상 제품·DOI 출처·계정 권한/한도·운영 제약을 설명하고 **사용자가 HLS 전용 정책 확인·설정 적용·인증 실검증을 승인**했다. 모든 NASA 제품/계정 권한을 익명 방문자에게 확대하지 않는다. [사용자 토큰 공식 문서](https://urs.earthdata.nasa.gov/documentation/for_users/user_token)의 호환 앱·만료·renew 시 기존 토큰 무효화도 유지한다.

L30은 OLI/OLI-2, S30은 MSI 원자료 계열의 조화 NBAR 광학 시계열이며 제품 격자는30m다. S30 원자료 밴드별10/20/60m와 출력30m를 구분한다. L30 B04/B05/B06/B07, S30 B04/B8A/B11/B12를 적색/NIR/SWIR1/SWIR2에 대응시키고 S30 B08과 B8A는 별개 파일로 보존한다. 기본 추천 NIR은 S30 B8A다. 실제 link가 없는 밴드는 만들지 않는다. 반사도scale0.0001과 Fmask 비트 QA를 기록하되 픽셀 적용/호환 판정은 하지 않는다. L30 B10/B11 TOA 밝기온도를 지표면온도로 표시하지 않는다. 개별 입력 플랫폼·파일 크기·구름량 누락은 임의로 채우지 않는다.

## 실제 검색·파일 요청

bbox **[126.7,36.4,126.71,36.41]**, UTC **2025-07-20~2025-07-26**. 작은 AOI는 연결 검증용이며 HLS30m로 그 크기의 대상을 상세 분석할 수 있다는 근거가 아니다.

| 제품 | 실제 선택 표본 | CMR 촬영 시작 UTC | 검색 건수 | 기하 중첩/장면 구름량 | 실제 파일 결과 |
|---|---|---|---|---|---|
| L30 | G3625879681-LPCLOUD / HLS.L30.T52SBF.2025204T021054.v2.0 |2025-07-23T02:10:54.573Z|1|100% /82%| browse400, 인증 B04 probe400, 크기 미확인, 전체0파일 |
| S30 | G3627467473-LPCLOUD / HLS.S30.T52SBF.2025206T021539.v2.0 |2025-07-25T02:27:32.626Z|2|100% /5%| browse400, 인증 B04 probe400, 크기 미확인, 전체0파일 |

기하 중첩은 제품 타일 포함이며 유효 픽셀률이 아니다. 구름은 CMR 장면 메타데이터이고 AOI QA가 아니다. 파일명 시각과 CMR 관측 구간은 그대로 보존하며 타일 모든 픽셀의 정확한 시각으로 간주하지 않는다. 실제 QA·NDVI·LST 계산은 하지 않았다.

16:18 공개 검색/미디어,16:29 승인 후 인증 표본 검증,16:37 현재 사이트 새 브라우저에서 실제 재검색했다. 인증 실검증은 각 제품 최대1개 전체 파일·파일당16MiB/합계32MiB 계획이었으나 probe 단계에서 실패해 대용량/일괄 수신은 없었다. HEAD200으로 성공 처리하지 않았다. 인증 검증 스크립트 runner 자체 exit0은 보고서 생성 완료이고, 그 JSON의 file status는 **provider_error/400**이다. 실제 파일 성공 코드가 아니다.

## 설정 적용·보안·서버 반영

처음 확인 시 OPERATOR_NASA_USER_TOKEN/OPERATOR_NASA_TOKEN_EXPIRES_AT만 존재하고 enable/정책 확인값은 미설정이었다. 토큰 원문·일부·JWT payload·비밀키는 출력/로그/브라우저/fixture에 넣지 않았다. 사용자 승인 후 아래 **비밀이 아닌8개 설정만** backend/.env에 적용했다:

```dotenv
OPERATOR_ACCESS_ENABLED=1
OPERATOR_NASA_ENABLED=1
OPERATOR_PUBLIC_ORIGIN=http://127.0.0.1:3000
OPERATOR_WORKERS=1
OPERATOR_NASA_REVISION=1
OPERATOR_NASA_COLLECTIONS=hls-l30-002,hls-s30-002
OPERATOR_NASA_REDISTRIBUTION_REVIEWED=1
OPERATOR_NASA_HLS_REDISTRIBUTION_REVIEWED=1
```

기존 token/expiry와 다른 모든 환경 값은 메모리상 대조로 보존 확인했다. USGS/CDSE enable이 비활성인 것도 확인했다. NASA 제품 allowlist 기본은 과거 VIIRS뿐이며 이번 설정은 **HLS 두 개만** 허용한다. 과거 VIIRS 정책 확인을 HLS로 자동 승계하지 않도록 별도 HLS review gate를 추가했다. 새 gate는 공개 경로를 막거나 사용자별 OAuth를 대신하지 않는다. 실제 .env·.private는 버전 관리 제외, 예시는 비밀 없는 이름/비활성 값뿐이다.

기존 서버 env 로더는 backend/.env 한 곳만 읽고 프로세스 환경이 우선한다. 새 HLS 설정도 backend만 전달한다. 토큰은 최초 승인 요청에서 기존 Windows DPAPI/SQLite 저장소로 채택됐고 회전/폐기 이력을 지우거나 초기화하지 않았다. 이번400은401이 아니므로 갱신/회전 API는 호출하지 않았다. 본문의 active는 로컬 grant 상태다. 현재 단일 Windows worker만 지원하며 공개/다중 worker 배포는 이번 승인이 아니다.

canonical CMR collection+granule+Asset를 재확인하고 정확한 호스트/제품 폴더·동일 파일명만 사용한다. Bearer는 LP DAAC 인증 호스트만, 교차 호스트 redirect에서 영구 제거한다. S3 requester-pays는 켜지 않았다. 전체 파일은 명시 클릭만, 범위 접근과 전체 완료는 별도다. 기존 파일256MiB·preview8MiB/16MP·동시2·35초/파일·receipt120초·사용량/캐시 상한을 유지한다. 현재 공개 browse는400이므로 실제 이미지로 표시하지 않는다.

사용자가 작업 부재/재시작을 승인한 뒤 루트12772와 프로젝트 경로·부모 관계가 맞는 자식만 종료했다. `.\start.cmd`로 새 wrapper33616/런처15120을 시작했다. 현재3000 PID40512,8000 PID35036. 분리 검증용3016/8016 프로세스는 종료했고 다른 앱/서버는 건드리지 않았다.

실제 웹 **http://127.0.0.1:3000**와 backend/frontend health 모두200. `/catalog`, `/api/catalog`200, **5개 제공처/9개 컬렉션**, 두 HLS concept 일치. NASA status는 configured=true, integration=operator, connected=false. 새 브라우저에서 방문자 Earthdata 로그인 링크가 숨겨짐·두 HLS 메뉴 선택·실제 검색 L30 1/S30 2·HTTP400 오류 표시를 확인했다. 데스크톱/390px 모바일 스크린샷과 가로 넘침 확인도 수행했다. 자연어 필드는 편집하지 않아 AI 호출은 없었다.

## 변경 파일·API/타입

- 신규 서버 `backend/app/hls.py`. 기존 `cmr.py`를 VIIRS 단일 고정에서 등록된 NASA 세 컬렉션으로 확장, 각 페이지 concept/Item collection 검증 유지.
- 수정 `backend/app/provider_registry.py`, `sensor_catalog.py`, `purpose_plan.py`, `recommendations.py`, `models.py`, `metadata.py`, `assets.py`, `access_paths.py`: 등록·단일 목적 규칙·실제 밴드 대응·품질 자료·원본 식별/출처. HLS를 기존 원본 S2/Landsat와 같은 제품으로 합치지 않음.
- 수정 `backend/app/media_access.py`, `provider_transfer.py`, `operator_access.py`: HLS canonical 재조회, 정확한 경로 allowlist, 제품별 정책/허용 게이트, 보호 파일 인증, 확인 가능한 전체 크기. 기존 사용자 OAuth/서버 미디어 receipt·전송 경로 재사용.
- 프런트 `frontend/src/app/page.tsx`, `components/SceneProvenance.tsx`, `ManagedAssetAccess.tsx`, `lib/types.ts`, `externalAccess.ts`, `useProviderAccess.ts`: 수동 HLS 메뉴·제품/DOI/QA 설명·원본 크기. 기존 결과/미리보기/밴드 선택/비교/다운로드 상태 재사용.
- 서버 환경 `scripts/server-env.mjs`, `server-env.test.mjs`, `backend/.env.example`. 실제 backend/.env는 위8개 승인 설정만 적용. 신규 `scripts/verify-hls-local.py`는 명시 승인 후 실행하는 제한된 실검증 도구이며 자격 값/URL을 출력하지 않음.
- 테스트 신규 `backend/tests/test_hls.py`, `frontend/tests/hls.spec.ts`, `hls-fixture.json`. 기존 `backend/tests/test_core.py`, `test_providers.py`, `test_sensor_recommendations.py`, `frontend/tests/provider-activation.spec.ts`, `sensor-recommendations.spec.ts`의 새 등록 수/추천 범위 반영.
- 문서 `docs/HLS_ADAPTER_DESIGN.md`, `OPERATOR_DATA_ACCESS.md`, `README.md`, `AGENTS.md`, 본 보고서. 과거 설계/당시 검증 기록은 아래 보존.
- 새 endpoint 없음. 기존 `/search`에 hls_l30/hls_s30 추천 ID, hls-l30-002/hls-s30-002 컬렉션을 허용. 공통 Scene에 hls provenance와 raster_metadata, media asset 상태에 size_bytes를 선택적으로 추가. **처리용 ItemReference는 확장하지 않음**.

## 실제 실행 테스트·종료 코드

| 검사 | 명령·환경 | KST 실행 시각 | 결과 | exit |
|---|---|---|---|---|
| 최종 backend 전체 | backend에서 `LIVE_STAC=0`, `..\.venv\Scripts\python.exe -m pytest -q --disable-warnings` |16:32~16:33:25| **465 passed,16 skipped**,1096warnings/35.34초 |0|
| 서버 env 로딩/노출/우선순위 | `node --test scripts/server-env.test.mjs` |16:31:58| **17 passed**,0 failed |0|
| 독립 typecheck | frontend `npm.cmd run typecheck` |16:19,16:31 및 재시작 후16:37| 성공 |0|
| production build | 아래 분리 환경 build |16:17~16:18:15| 성공 |0|
| 관련 E2E | 아래5파일,3016→8016, LIVE_STAC=0 |16:25~16:27:51| **32 passed,2 skipped** |0|
| 전체 E2E | frontend `npx.cmd playwright test --timeout=45000`,3016→8016,LIVE_STAC=0 |16:30~16:35:16| **153 passed,5 skipped**,5.2분 |0|
| 현재 사이트 HLS mock E2E | `npx.cmd playwright test tests/hls.spec.ts --timeout=45000`,3000→8000 |16:36:38 완료| **3 passed**,9.6초 |0|
| 실제 NASA 인증 표본 | 아래 기존 env 로더+검증 스크립트 |16:29:19~26| runner 완료, **browse400/인증B04 400 실패·전체 파일0개** |0 (runner)|
| 실제 현재 사이트 브라우저 | `node test-results/hls-ui-live.mjs` (ignored 검증 도구) |16:37:20| 실제 검색/메뉴/로그인 숨김/모바일 확인, 미리보기 실패를 정확히 표시 |0|
| 로컬 비노출 감사 | 토큰을 로컬 메모리에서만 대조, source/tests/docs/scripts/example/생성 frontend static252파일 |16:38 전| 토큰 일치0파일, 외부 전송 없음 |0|

production build(frontend, 서버 비밀을 제거한 환경):
```powershell
node --input-type=module -e "import {spawnSync} from 'node:child_process';import {frontendEnvironment} from '../scripts/server-env.mjs';const r=spawnSync(process.execPath,['node_modules/next/dist/bin/next','build','--webpack'],{stdio:'inherit',env:frontendEnvironment({...process.env,NEXT_DIST_DIR:'.next-conditions-final',API_BASE_URL:'http://127.0.0.1:8016'})});process.exit(r.status??1);"
```

관련 E2E(frontend):
```powershell
$env:E2E_BASE_URL='http://127.0.0.1:3016'
$env:E2E_API_BASE_URL='http://127.0.0.1:8016'
$env:LIVE_STAC='0'
npx.cmd playwright test tests/hls.spec.ts tests/media-access.spec.ts tests/operator-access.spec.ts tests/providers.spec.ts tests/sensor-recommendations.spec.ts --timeout=45000
```

실제 인증 검증(root, 승인 후만 실행; stdout은 안전한 상태 보고만):
```powershell
node --input-type=module -e "import {spawnSync} from 'node:child_process';import {childEnvironments} from './scripts/server-env.mjs';const r=spawnSync('.venv/Scripts/python.exe',['scripts/verify-hls-local.py'],{cwd:process.cwd(),env:childEnvironments(process.cwd()).backend,encoding:'utf8',windowsHide:true});process.stdout.write(r.stdout||'');if(r.status)console.log(JSON.stringify({exit:r.status,diagnostic:'Details suppressed to protect credentials'}));process.exit(r.status??1);"
```

mock 범위: L30/S30 변환·기간/bbox 보존·페이지/중복/기간 밖 제외·컬렉션 부분 timeout·미리보기 누락·잘못된 파일/버전/호스트·정확한 적색/NIR/Fmask 선택·계정 게이트·만료·401/403/404·HTML·교차 호스트 헤더 제거·크기 제한·2×2 합성 GeoTIFF 전체 내용 검증·명시 다운로드·모바일. 기존 공통 만료/회전 race/철회/다른 사용자 receipt·공개 제공처/QA/NDVI/합성/ML 회귀도 포함한다. AI/Kakao transport는 차단/mock이며 사용자의 실키를 fixture로 사용하지 않는다.

pytest16skip과 E2E5skip은 선택적 실제 제공처/공개 전체 파일 검사다. 일부 기존 E2E는 공개 STAC/래스터 실연결을 수행하지만 HLS 인증/원본 성공의 대체 증거가 아니다. 전체 E2E 중 기존 실검색의 `/media/inspect`429 두 건도 관측했다. 검색/UI 단언은 통과했으나 '모든 미리보기 요청이 성공'한 것으로 표현하지 않는다. 동시2 제한을 해제하지 않았다.

중간 실패: 첫 관련pytest83passed/1failed 및 첫 전체459passed/4failed는 기존 추천/등록 개수 고정 단언을 새 HLS 범위로 수정한 뒤 통과했다. 초기 관련E2E27passed/5failed/2skipped에는 HLS가 추가 후보 그룹인 점·접힌 밴드 영역, 잘못된 TEST ONLY PNG, 기존 카드 개수 단언이 원인이었다. 디코딩 가능한 TEST ONLY PNG로 교정하고 기존 그룹/밴드 상태에 맞춰 최종32/2·전체153/5·runtime3으로 재확인했다. 기능 코드에서 실패를 fixture로 대신하지 않는다.

## 사용 순서와 남은 제한

현재3000 새로고침 → 목적 직접 선택=식생(유료 AI 없이 가능) → 위 UTC 기간/좌표 입력·AOI 확정 → 위성 선택=직접 선택 → **NASA HLS L30 · Landsat · v2.0 / NASA HLS S30 · Sentinel-2 · v2.0** 선택 → 검색. 추천 카드의 **이 제품 선택**도 같은 컬렉션·AOI/기간을 사용한다. HLS 결과는 다른 위성·추가 후보 그룹에서 확인한다. 밴드 선택·다운로드를 펼치면 L30 B04/B05/Fmask, S30 B04/B8A/Fmask가 기본 선택이다. Fmask 존재는 실제 QA 완료가 아니다.

현재 browse/원본은 실제400 장애 상태가 표시된다. **원본 접근 확인이 available이 되기 전에는 다운로드 버튼을 성공 경로로 활성화하지 않는다.** 다음 조사는 제공처 요청/서비스 상태·호환 인증·대상 DAAC 접근 경로의400 원인을 비밀 없이 확인하는 일이다. 인증 성공·전체 작은 TIFF 수신·실제 토큰 회전은 미검증이며, 새 토큰 발급/비용 경로 우회로 해결됐다고 주장하지 않는다. 공개/다중 worker 운영, HLS 픽셀 처리·폴리곤 클리핑·ST/LST 분석은 이번 범위 밖이다.

검증 파일은 ignored `frontend/test-results/hls/`의 `public-live.json`, `authenticated-live.json`, `runtime-browser.json`, 실제 오류/결과/mobile PNG 및 `frontend/test-results/hls-*.txt`, `test-results-workflow-hls*`에 있다. 토큰/서명 URL은 기록하지 않았다.

---

# AI 중심 자연어 조건 입력 — 2026-11-02 최신 변경 검증 (KST)

후속 GPT-4o 모델 변경과 **사용자 승인 후 서버 재시작 완료** 기록은 아래 `GPT-4o 모델 선택·설정 검증` 절을 따른다. 이 절의 “기존 지정 모델은 변경하지 않았다”는 최초 AI 중심 입력 구현 시점의 기록이다.

## 구현과 검증의 구분

기존 OpenAI Responses 호출·Next.js/MapLibre·FastAPI·단일 폼/AOI·목적별 과학 추천·검색·미디어·A2~A4·관측 합성/ML을 재사용했다. 초기 자연어 조건은 AI 전용이며 규칙 기반 추출/실패 fallback을 호출하지 않는다. 과거 독립 규칙 함수와 역사 문서는 삭제하지 않았지만 현재 조건 생성 경로와 분리했다. 기존 환경 파일·키·지정 모델은 변경하지 않았다. 배포·push·새 계정·유료 호출은 수행하지 않았다.

- 사용자 편집 후 1.2초 안정화/blur 자동 해석, IME 보호·취소·최신 세대·중복 억제·동일 문장 캐시·호출 상한을 구현했다. 초기 로딩만으로는 호출하지 않는다. 입력 옆에 전체 문장 전송/비용을 표시한다.
- 목적·대상·날짜·비교 기간/기준일·지명/공간 의도·구름/해상도/대상 크기에 원문 근거와 명시/추론/미지정을 보존한다. 스키마/달력/윤년/기간/원문 근거를 서버에서 검증한다. AI 좌표·경계·위성 사양·영상 존재 생성은 허용하지 않는다.
- 명확한 AI 결과와 실제 공간 자료가 있으면 날짜·목적·장소·좌표·지도 박스를 자동 채우고 같은 AOI를 확정한다. 새 문장에서는 이전 자동 값/AOI를 제거하고 검색을 막는다. 직접 수정값은 유지하고 충돌 유지/문장에서 다시 적용을 제공한다. 지도 꼭짓점 드래그와 좌표 수동 수정도 유지한다.
- AI 실패/설정 누락/응답 오류/시간 초과/429는 실패로 표시하고 재시도·직접 입력만 제공한다. 날짜·목적·지명을 키워드로 대신 채우지 않는다. `/recommend`와 `/search`도 확정 purpose_type 없이 원문을 다시 분류하지 않는다.
- 자동화는 조건 해석·위치 확인·폼/지도 반영까지다. 영상 검색·다운로드·픽셀 처리는 사용자 명시 실행이다. 전후 기간은 별도로 보존하며 사건 날짜/장면 선택을 임의 생성하지 않는다.

## 지역 데이터와 실제 외부 접근

자동 행정구역 전체 bbox는 **서울특별시와 제주특별자치도** 및 등록 별칭만 지원한다. Kakao 주소/장소 키워드 API는 기존 서버 설정을 재사용한다. 다른 한국 지명은 위치 확인까지 가능하지만 미등록 경계를 자동 전체 영역으로 바꾸지 않는다. 점 장소는 확인된 좌표와 명시 거리(0초과~100km)가 있을 때만 WGS84 측지 bbox를 만든다. 거리 없는 점은 범위를 확인한다. 제주시·구·군을 상위 시도 전체로 대체하지 않는다.

공식 자료: [SGIS 행정구역 통계 및 경계](https://www.data.go.kr/data/15129688/fileData.do), DBF BASE_DATE=20250630/2025년2분기, SGIS 서울11·제주39(행정코드50). 포털 이용허락범위 제한 없음/출처 표시 조건을 메타데이터에 기록했다. 통계 경계이며 최신 법적 측량 경계를 보증하지 않는다. EPSG:5179→4326, always_xy=True/경도·위도 순서, SHA-256·도형 유효성·코드/이름/기준일·면적·bounds를 검증했다.

- 실제 공식 ZIP **269,032,521 bytes**를 읽고 제주 원본 경계 **10,149,747 bytes**를 생성했다. 첫100MiB 상한 시도는 중단됐고 상한을 정한 재요청으로 ZIP 전체를 검증했다. 계정/키/유료 서비스는 사용하지 않았다.
- 제주 bbox `[126.14345549941781,33.112355758732,126.97265693471556,34.013233386819344]`, 원본 면적 약1865.0489km². 부속도서를 포함하는 전체 행정구역이다. bbox는 간소화 전 원본에서 계산한다. 지도 응답 윤곽만 topology 보존0.00005도 간소화와 방법 메타데이터를 적용했다. 기존 서울 원본 파일은 덮어쓰지 않았다.
- **행정경계 외접 범위이며 폴리곤 클리핑 미지원**이다. 사각형에는 경계 밖/바다도 포함된다. 검색 범위(가로/세로5도·366일)와 기존 픽셀 처리25km² 상한을 구분한다. 큰 AOI를 몰래 축소하지 않는다.
- [Kakao Local 공식 API](https://developers.kakao.com/docs/ko/local/dev-guide), [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses)를 확인했다. 개발 검증의 AI/Kakao는 모두 mock이며 실제 키로 호출하지 않았다. 실제 모델 이해·접근 가능 여부/Kakao 성공은 **미검증**이다. SGIS 다운로드 성공을 AI/Kakao 성공으로 간주하지 않는다.

## 변경 파일과 API 계약

서버:
- 신규 `backend/app/ai_conditions.py`, `backend/app/spatial_extent.py`.
- 수정 `backend/app/ai_interpretation.py`, `main.py`, `models.py`, `request_interpretation.py`, `provider_search.py`, `place_search.py`, `admin_boundaries.py`.
- 신규 `backend/app/data/boundaries/jeju-sgis-2025-q2.geojson`, `jeju-sgis-2025-q2.metadata.json`; 기존 importer `scripts/import-seoul-boundary.py`의11/39 선택 확장.
- `/request/interpret resolve_conditions=true`는 기본/명시ai/과거rules 값 모두 AI 전용. strict 추출·provenance·조건fields·전후기간을 반환한다. 실패 시 period/region absent이며 rule fallback 없음.
- `/places/search`는 기존 place에 kind(administrative/place), 선택 radius_m을 추가한다. canonical 후보와 기존 boundary/extent를 반환한다. `/places/config`의 준비와 실제 성공은 별도다.
- `/search`는 기존 확정 purpose_type에 requested_resolution_m, max_scene_cloud_cover, requested_reference_date, analysis_target을 추가한다. 전자는 메타데이터 필터이며 AOI QA/출력 격자를 보장하지 않는다. purpose_type 누락은 PURPOSE_REQUIRED다. 기존 컬렉션별 부분 실패를 유지한다.

프런트:
- `frontend/src/lib/useConditionInput.ts`, `types.ts`.
- `frontend/src/components/AutomaticConditions.tsx`, `MapPanel.tsx`, `NaturalWorkflow.tsx`, `AnalysisConditions.tsx`.
- `frontend/src/app/page.tsx`, `globals.css`.
- 초기 날짜는 미지정이며 테스트/앱이 과거 기본 연도를 현재 조건으로 간주하지 않는다. 지도 핸들의 값 기반 effect와 비대화형 안내의 pointer-events를 고쳐 실제 마우스 드래그 시 핸들 재생성/가림을 해결했다.

테스트:
- 신규 `backend/tests/test_ai_primary.py`, `backend/tests/conftest.py`(실제 유료 AI 전송 차단).
- 계약 갱신 `backend/tests/test_ai_interpretation.py`, `test_condition_proposals.py`, `test_place_search.py`, `test_request_interpretation.py`, `test_core.py`, `test_purpose_plan.py`, `test_sensor_recommendations.py`, `test_providers.py`, `test_public_paths.py`.
- `frontend/tests/ai-primary-fixtures.ts`, `automatic-conditions.spec.ts`, `ai-conditions.spec.ts`, `ai-camera.spec.ts`, `boundary-conditions.spec.ts`, `runtime.ts`.
- 기존 엔진/수동 회귀의 명시 테스트 날짜·목적/직접 입력 상태 반영: `analysis-conditions.spec.ts`, `auto-preview.spec.ts`, `change-analysis.spec.ts`, `cloud-workflow.spec.ts`, `earthdata-auth.spec.ts`, `estimate-mode.spec.ts`, `external-access.spec.ts`, `imagery-explorer.spec.ts`, `imagery-layout.spec.ts`, `media-access.spec.ts`, `next-work.spec.ts`, `operator-access.spec.ts`, `pixel-quality.spec.ts`, `provider-activation.spec.ts`, `providers.spec.ts`, `public-data.spec.ts`, `reliability.spec.ts`, `search.spec.ts`, `sensor-recommendations.spec.ts`.
- fixtures는 tests 안에서만 사용한다. AI/Kakao 테스트 transport는 실제 호출을 차단한다. UI용 synthetic 경계는 TEST ONLY이며 실제 도형 검증은 서버 테스트/공식 원본으로 별도 수행했다. 서비스 실패 시 fixture를 반환하지 않는다.

문서/설정:
- `docs/AI_PRIMARY_INPUT.md` 신규 현재 계약. `README.md`, `AGENTS.md`, `docs/AI_NATURAL_INPUT.md`, `ADMINISTRATIVE_AOI.md`, `AI_PLACE_CONDITIONS.md`, `AUTOMATIC_CONDITIONS.md`, 본 보고서에 과거 계약/현재 변경 구분.
- `.gitignore`에 별도 검증 build 디렉터리 추가. `frontend/next-env.d.ts`, `frontend/tsconfig.json`은 Next가 검증 dist/개발 dist의 타입 경로를 생성·추가했다. 사용자 include를 삭제하지 않았다. 실제 `.env`/`.env.example`/의존성 설정은 변경하지 않았다.

## 최신 실행 명령·종료 코드

아래는 이번 코드에서 실제 실행했다. 시각은 KST다. 과거 보고의 pytest/E2E 숫자를 현재 통과 근거로 재사용하지 않는다.

| 검사 | 명령/환경 | 시각 | 실제 결과 | 종료 코드 |
|---|---|---|---|---|
| backend 전체 | backend에서 `LIVE_STAC=0`, `..\.venv\Scripts\python.exe -m pytest -q --disable-warnings` |12:42:10~12:43:30| **449 passed,16 skipped**,1088warnings,77.45초 |0|
| 최종 production build | 아래 분리 환경 build |12:52~12:52:35| 성공, 최종 목적 미지정 검색 차단 포함 |0|
| 독립 typecheck | frontend에서 `npm.cmd run typecheck` |12:52 및12:55| 성공, 재시작 후 Next 타입 경로도 확인 |0|
| 전체 E2E |3015→8015, `LIVE_STAC=0`, `npx.cmd playwright test --timeout=45000` |12:41:59~12:48:12| **149 passed,5 skipped**,6.2분 |0|
| 최종 변경 관련 production E2E |아래4개파일,3015→8015|12:52~12:53:33| **27 passed**,39.9초 |0|
| 현재 사이트 재검증 |아래4개파일,3000→8000, AI/Kakao mock, 클라이언트 준비 대기 보완 후|12:55~12:57| **27 passed**,1.4분 |0|

중요: 전체149/5 통과 후 'AI 목적 미지정 상태 검색 차단'과 해당 테스트1개를 추가했다. 그 **최종 제품 코드**는 새 build/typecheck 및 관련27개로 검증했다. 최종 전체155개를 모두 재실행했다고 주장하지 않는다. 이후 테스트 helper에 클라이언트 준비 대기만 추가했으며 제품 코드 변경은 없다. 현재3000사이트 재검증 결과는 아래 운영 확인 절을 따른다.

production build 정확한 명령(frontend):
```powershell
node --input-type=module -e "import {spawnSync} from 'node:child_process'; import {frontendEnvironment} from '../scripts/server-env.mjs'; const r=spawnSync(process.execPath,['node_modules/next/dist/bin/next','build','--webpack'],{stdio:'inherit',env:frontendEnvironment({...process.env,NEXT_DIST_DIR:'.next-conditions-final',API_BASE_URL:'http://127.0.0.1:8015'})});process.exit(r.status??1);"
```
기존 `frontendEnvironment`로 서버 비밀 환경을 제거한 별도 dist에 build했다. 설치나 의존성 변경은 없다.

관련 E2E 명령(frontend):
```powershell
$env:LIVE_STAC='0'
$env:E2E_BASE_URL='http://127.0.0.1:3015' # 현재 사이트 확인에서는3000
$env:E2E_API_BASE_URL='http://127.0.0.1:8015' # 현재 사이트 확인에서는8000
npx.cmd playwright test tests/automatic-conditions.spec.ts tests/ai-conditions.spec.ts tests/boundary-conditions.spec.ts tests/ai-camera.spec.ts --timeout=45000
```

검사 범위: 축약 날짜/윤년/부정 날짜/상대 기간·비교 확인, AI 실패·타임아웃·스키마/근거/HTTP 오류, AI 목적 미지정, rule 함수 호출 금지, 서울→제주 교체, 수동 날짜/AOI 보호, 늦은 AI/지명 응답 무시, 후보 선택·경계 미지원·명시 거리, IME/중복/캐시/취소, 지도·좌표·검색 bbox 일치, 실제 마우스 핸들, 모바일 가로 넘침, 기존 추천/검색/비교/밴드·다운로드/A2~A4·관측 합성/ML 회귀.

전체 E2E의5skip은 명시 LIVE_STAC=1 공개 미디어/전체 파일 실연결 케이스다. 이번 자연어 작업에서 공개 다운로드를 새로 검증했다고 하지 않는다. 기존 일부 엔진 브라우저 회귀는 공개 STAC/래스터를 요청하지만 **AI와 Kakao는 차단/mock**이다. 백엔드16skip도 실연결 선택 테스트이며 pass에 포함하지 않는다.

중간 실패도 기록한다: 첫 backend 전체42failed/382passed는 이전 규칙 API/구 스키마 의존 테스트를 새 계약으로 수정한 뒤 최종449/16으로 확인했다. 첫 production 전체147passed/2failed/5skipped는 지도 핸들 effect/안내 가림과 새 문장 동안 검색 차단의 구 기대값이었다. 수정 후 실제 드래그1개와 전체149/5가 통과했다. 소스 수정 중 dev E2E는 중단(exit1)했으므로 완료 실행으로 세지 않는다. 현재 사이트 초기 재검증26passed/1failed(exit1)는 한 입력이 클라이언트 준비 전에 실행된 현상으로, helper에 실제 설정 effect 완료 대기를 추가해 다시 검증했다.

검증 로그/스크린샷은 ignored `frontend/test-results/ai-primary-*.txt`, `ai-primary-mobile.png`, `frontend/test-results-workflow-ai-primary*`에 있다. 모바일 이미지는 명시 TEST ONLY mock 화면이며 실제 Kakao/AI 성공 증거가 아니다.

## 운영 확인과 남은 검증

사용자가 진행 중 작업 없음과 재시작을 승인했다. 이전 런처17608/상위2372와 프로젝트 경로·부모 관계가 일치하는 서버 자식만 확인 후 종료하고 `.\start.cmd`로 재시작했다. 다른 앱/서버는 종료하지 않았다. 새 런처12184/상위39676, 현재3000(13036)·8000(45060). 검사 전용3015/8015 서버는 종료했다.

- 실제 주소 **http://127.0.0.1:3000**. 웹200, backend `/health`200, frontend `/api/health`200.
- `/catalog`와 `/api/catalog`200, 기존5개 제공처/7개 컬렉션 유지.
- AI 설정 인식 ready=true, provider=openai, 기존 model=gpt-5.6-luna, 누락 설정 없음. **모델의 계정 접근/실제 응답은 미검증**이다. 재시작 후 실제 AI requests/succeeded/failed=0/0/0을 확인했다. 키 값은 조회/출력/변경하지 않았다.
- 현재3000/8000 사이트에서 최종 관련27개 브라우저 검사가 모두 통과했다(exit0). `frontend/test-results/ai-primary-runtime-verified.txt`에 결과를 기록했다. AI/Kakao mock 검증이며 실제 제공처 접속 성공을 뜻하지 않는다. 검사 후에도 실제 AI 요청 집계는0건이다.
- 실제 유료 AI/Kakao 호출 검증·서비스 쿼터 사용은 수행하지 않았다. 실제 AI 검증은 예상 호출 수/비용 범위를 별도 제시하고 승인 후에만 한다. 현재 자동 해석 UI에 사용자가 입력하면 실제 요청/비용이 발생할 수 있다.
- 서버 AI 한도/캐시는 프로세스 기준이고 다중 서버의 공유 과금 통제가 아니다. 지명 자동 전체 경계는 서울/제주만이며 다른 경계·폴리곤 클리핑·열환경 계산 엔진 추가는 미구현이다. 기존25km² 처리 제한은 유지한다.

사용자 확인 순서: 새로고침 → `2025년 8/15~8/30까지 제주도의 지표면 온도를 알고 싶어` 입력(실제AI비용발생가능) → 날짜·thermal 목적·실제 위치/공간 상태·bbox 확인 → 서울/제주 문장 교체 시 이전 자동 영역 제거 확인 → 날짜/좌표를 직접 수정하고 충돌 유지/문장에서 다시 적용 확인 → 명시 검색. AI/Kakao 오류면 그 상태와 직접 입력을 사용한다.

---

# GPT-4o 모델 선택·설정 검증 (2026-11-02 KST)

- 사용자 지정 `gpt-4o`를 서버 전용 `backend/.env`, 비밀값 없는 `.env.example`, 새 설정의 기본값에 적용했다. 기존 `OPENAI_API_KEY` 값은 변경하거나 출력하지 않았다. 입력/출력 백만 토큰당 $2.50/$10.00을 보고 토큰 비용 추정 설정에 반영했다. GPT-4o는 공식 문서상 deprecated이며 기존 GPT-5.6 Luna보다 단가가 높다.
- `backend/tests/test_ai_interpretation.py`에 GPT-4o 요청이 기존 strict JSON schema를 쓰고 reasoning 전용 매개변수를 보내지 않는 fixture 테스트를 추가했다. 실제 OpenAI 네트워크 호출은 하지 않았다.
- `C:\Users\aicam\Documents\ChatGPT\바이브코딩\.venv\Scripts\python.exe -m pytest -q backend/tests/test_ai_interpretation.py backend/tests/test_ai_primary.py`: 종료 0, **50 passed, 1 warning**. 최초 샌드박스 실행은 출력 없이 멈춰 중단(종료 1); 동일 명령을 정상 프로세스 권한으로 다시 실행해 통과했다.
- `node --test scripts/server-env.test.mjs`: 최초 샌드박스 임시 폴더의 rename/Git 제한으로 종료 1, 14/16. `TEMP`와 `TMP`를 작업 폴더 `.tmp`로 지정해 동일 명령을 재실행한 결과 **종료 0, 16/16 passed**.
- 최초 실행 중 로컬 `GET /request/config`는 `gpt-5.6-luna`를 반환했다. 사용자가 **진행 중 작업 없음·재시작 승인**을 확인한 뒤 3000/8000 포트의 이 프로젝트 런처/자식 PID만 식별·종료하고 `scripts/start-local.mjs`를 다시 시작했다. 이후 `GET /request/config`는 `{"ready":true,"model":"gpt-4o"}`, 프런트 `GET /api/health`는 `phase=1`을 반환했다.
- `childEnvironments(process.cwd())`의 새 백엔드 환경은 `gpt-4o`, 프런트 환경의 모델 변수는 null로 확인했다. 실제 OpenAI 유료 호출·계정 모델 접근·자연어 추출 품질은 아직 미검증이다.
- 프런트 코드 변경이 없으므로 이번 범위에서 typecheck/build/E2E는 미실행. 이전 기록을 이번 통과로 재사용하지 않는다.

# 로그인 없는 공개 자료 경로 구현·검증 (2026-11-02, KST)

## 범위와 현재 판정

기존 FastAPI/Next.js/MapLibre, 목적 규칙·AOI/UTC 기간·추천 카드·장면/밴드 선택·비교·다운로드·A2~A4·관측 합성/ML을 재사용했다. 신규 앱/분석 엔진을 만들지 않았다. Planetary Computer 공개 STAC + 익명 SAS의 S2 L2A/Landsat8·9 C2 L2, NOAA NODD의 NOAA-20 VIIRS NDVI CDR v1 공개 객체 검색/NetCDF 전송을 연결했다. 현재 **5개 제공처·7개 내부 컬렉션**이다. 실제 backend/.env·키·운영자 인증 활성화·비용 동의·계정 생성·AI 호출·배포·push는 하지 않았다.

검증 전 계획과 구현/API/타입/테스트 범위를 보고하고 진행했다. 기존 날짜 해석 파일의 별도 편집을 덮어쓰지 않았고 최신 pytest/E2E 통합 검사에 포함했다. 아래 최신 결과와 과거 보고서를 구별한다.

## 실제 공개 연결·전체 파일 내용

공통 bbox126.7,36.4,126.71,36.41 / UTC2025-07-20~26. NOAA는2025-07-20 하루. 새 브라우저는 제공처 로그인 cookie가 없고 원본은 명시 클릭 후 수신했다. HEAD 성공으로 다운로드를 판정하지 않았다.

| 경로 | 실제 장면/제품 | 미리보기 | 명시 원본 다운로드·내용 확인 |
|---|---|---|---|
| Earth Search S2 MSI L2A | 기존 공개 S2 경로 | 기존 제공처 이미지 흐름 유지 | SCL **1,591,434 bytes**, GTiff5490×5490/uint8/1band/EPSG32652, 실제8×8 디코딩 |
| PC Landsat9 OLI-2/TIRS-2 C2 L2SP | LC09_L2SP_116035_20250723_02_T1 / 원천LC09_L2SP_116035_20250723_20250726_02_T1 | 실제 rendered_preview PNG **1,239,292 bytes**, 전체 디코딩/화면 표시200 | QA_PIXEL **3,718,793 bytes**, GTiff7841×7961/EPSG32652, 실제8×8 디코딩 |
| PC Sentinel-2B MSI L2A | S2B_MSIL2A_20250725T021539_R003_T52SBF_20250725T041758 | 실제 rendered_preview PNG **2,190,270 bytes**, 전체 디코딩/화면 표시200 | SCL **1,474,350 bytes**, GTiff5490×5490/uint8/1band/EPSG32652, 실제8×8 디코딩 |
| NOAA NODD NOAA-20 VIIRS NDVI CDR | VIIRS-Land_v001_JP113C1_NOAA-20_20250720_c20250728122022 | **missing_asset**, NetCDF를 이미지로 표시하지 않음 | **64,011,565 bytes**, HDF5-container/netCDF. NDVI/QA int16 7200×3600, 약0.05° 경위도 변환·NOAA-20/VIIRS 태그와 각4×4 실제 변수 디코딩 |

PC 원본은 공식 Data Authentication API가 계정 없이 발급한 SAS로 서버에서 접근했다. 토큰/서명 URL은 출력·저장·프런트 전달하지 않았다. 최초 TIFF 범위206/1024바이트 확인과 전체 원본 수신을 구분했다. **선택한 QA/SCL/NetCDF 파일만 검증했으며 모든 밴드/날짜/크기의 다운로드 성공 보장은 아니다.** 실제 AOI 픽셀 QA·Landsat LST 계산·NOAA QA 판정 결과로 부르지 않는다. 원본 전체 장면/제품 파일이며 AOI 추출본이 아니다.

NOAA 범위는2023년 이후 확인된 NOAA-20 JP113C1 filename v001만. 내부 product_version=v2r0와 NASA VNP09GA.002는 구별한다. 0.05° 일별 NDVI 파생 제품의 전 지구 격자는 실제 촬영/유효 픽셀 범위가 아니다. 작은 AOI 연결 성공이 상세 분석 적합성의 근거가 아니다. NOAA NetCDF 전체 자동 읽기는 미리보기8MiB 상한을 넘으므로 미리보기 생성기/폴리곤 클리핑/QA/합성/ML은 미지원이다.

## 변경 파일·API/타입

- 신규 서버: backend/app/planetary.py, noaa_nodd.py, public_media.py, access_paths.py, access_guidance.py.
- 기존 서버 확장: backend/app/provider_registry.py, provider_search.py, sensor_catalog.py, purpose_plan.py, recommendations.py, models.py, provider_transfer.py, media_access.py, assets.py, metadata.py, main.py, catalog_discovery.py.
- 프런트: frontend/src/lib/types.ts, frontend/src/app/page.tsx, frontend/src/app/globals.css, frontend/src/components/AssetDownloads.tsx, SceneProvenance.tsx, SensorRecommendations.tsx, Results.tsx. 기존 ProviderPreview/ManagedAssetAccess·큐/receipt/밴드 상태 재사용.
- 테스트: 신규 backend/tests/test_public_paths.py, frontend/tests/public-data.spec.ts. 기존 backend/tests/test_core.py, test_sensor_recommendations.py, test_providers.py, frontend/tests/provider-activation.spec.ts, sensor-recommendations.spec.ts 보완.
- 문서: docs/PUBLIC_DATA_ACCESS.md, README.md, docs/OPERATOR_DATA_ACCESS.md, AGENTS.md, 본 보고서. 실제 환경 파일·패키지/의존성 변경 없음. 검증 산출물은 ignored frontend/test-results* 안에 저장.
- /catalog에2제공처·3내부 컬렉션 추가. /search recommendation_id에 pc_s2_msi/pc_landsat_oli/pc_landsat_tirs/noaa_viirs_ndvi 추가. 기존 /media/inspect/previews/downloads에 공개 경로를 추가하고 새 임의 URL 프록시는 만들지 않았다.
- 검색 상태 outside_scope(기간/목적 미지원·요청0회), access_guidance(scene_confirmed=false), source_product/access_group/access_paths, geometry_role/temporal_role, 파일명·형식·크기·제공처·signing_required 추가. Item/Asset을 합치거나 다른 파일을 대신 연결하지 않는다. 기존 처리 ItemReference는 제한된 컬렉션만 허용한다.
- 모바일 실제 스크린샷에서 미리보기 버튼의 가로 폭이 scene-body 메타데이터를 압축하는 것을 확인했다. 해당 카드만 grid 한 열과 사실 행의 두 열로 정리해 체크박스/전역 input 규칙은 변경하지 않았다.

## 최신 실행 명령·결과

작업 디렉터리 backend 또는 frontend. 검증 서버는3015/8015, 운영자/AI/Kakao 비활성의 별도 프로세스이며 .env를 읽지 않았다. frontend production 빌드는 frontendEnvironment로 서버 비밀 변수 전달을 차단했다.

| 실행 시각(KST) | 명령 | 종료 코드·실제 결과 |
|---|---|---|
| 11:47:05~11:47:58 | backend: LIVE_STAC=0; ..\.venv\Scripts\python.exe -m pytest -q --disable-warnings | **0 / 424 passed,16 skipped**,1088 warnings,51.97s. 공개 경로 fixture·보안·만료/경합/크기·NetCDF·부분 실패 포함. 공개 API 실연결 성공으로 해석하지 않음 |
| 11:49 및11:50 | frontend: npm.cmd run typecheck | **0**, 독립 tsc --noEmit |
| 11:42~11:43 | frontend: node --input-type=module -e [spawnSync Next build --webpack; frontendEnvironment; NEXT_DIST_DIR=.next-conditions; API_BASE_URL=http://127.0.0.1:8015] | **0**, production compile·TypeScript·정적 페이지·trace 완료. .next-conditions는 기존 검증용 산출물 경로 |
| 11:39~11:40:50 | E2E_BASE_URL=http://127.0.0.1:3015; E2E_API_BASE_URL=http://127.0.0.1:8015; LIVE_STAC=1; npx.cmd playwright test tests/public-data.spec.ts tests/operator-access.spec.ts --grep '^LIVE' | **0 / 4 passed**,1.5min. Earth Search S2/PC Landsat/PC S2/NOAA 실제 파일 수신 |
| 11:43~11:49 | 동일 검증 주소, LIVE_STAC=0; npx.cmd playwright test | **1 / 162 passed,2 failed,5 skipped**. 기존 고정 추천 카드 수(3/1/3)가6/2/5로 늘어난 기대값 검사2건 실패. 새 제품 ID와 야간 제한을 명시 검사하도록 테스트 보완 |
| 11:49:44~11:56:26 | E2E_BASE_URL=http://127.0.0.1:3015; E2E_API_BASE_URL=http://127.0.0.1:8015; LIVE_STAC=1; npx.cmd playwright test | **0 / 169 passed**,6.7min, 미실행/실패0. 실제 공개 파일·기존 공개 미디어/A3/A4/관측 합성/ML 검사와 TEST ONLY fixture 모두 포함 |
| 11:56~11:57 | .\start.cmd 프로젝트 재시작; health/catalog 실제 HTTP 확인; frontend: node test-results/verify-public-runtime.mjs | **0**. 프로젝트만 승인 후 재시작. 8000/3000 health200, /catalog 및 /api/catalog200·5제공처/7컬렉션. 실제 3000 화면 새3컬렉션 선택 가능·PC Landsat200/1건·데스크톱/390px 미리보기 naturalWidth>0·가로 넘침 없음. 이 runtime smoke에서는 원본 재다운로드 안 함 |
| 11:57 | frontend: npm.cmd run typecheck | **0**, 재시작 후 Next 생성 타입 포함 독립 검사 |

실제 production build 명령(작업 위치 frontend, 서버 비밀 변수를 제거한 환경):

```powershell
node --input-type=module -e "import {spawnSync} from 'node:child_process'; import {frontendEnvironment} from '../scripts/server-env.mjs'; const r=spawnSync(process.execPath,['node_modules/next/dist/bin/next','build','--webpack'],{stdio:'inherit',env:frontendEnvironment({...process.env,NEXT_DIST_DIR:'.next-conditions',API_BASE_URL:'http://127.0.0.1:8015'})});process.exit(r.status??1);"
```

전체 E2E는 TEST ONLY fixture와 기존 공개 실제 검색/A3/A4/합성/ML 검사가 섞여 있다. 명시 LIVE3개 새 제품과 기존 공개 S2/제공처 미디어 검사는 개별 결과로 구분한다. 실제 유료 AI·Kakao·운영자 인증 원본은 호출하지 않는다. 세부 로그: frontend/test-results/public-pytest-verified.txt, public-full-verified.txt, public-live-final.txt. 이미지: public-live-*-desktop.png / mobile.png. signed URL/토큰을 증거 파일에 포함하지 않는다.

중간 실패도 보존했다. 최초 SAS 검증은 공식 응답의 spr 생략을 허용하지 않아 sas_invalid_response였고, HTTPS 전송을 강제하면서 공식 읽기 SAS 형식을 수용하도록 수정했다. 첫 실브라우저에서 PC S2의 Sentinel-2B 대소문자 차이로 추천 필터가0건을 반환했으며 명시적 플랫폼 표준 매핑·원문 보존과 회귀 테스트로 수정했다. 초기 추천 목록/출처 확인일 기대값과 단축 날짜 관련 실패가 있었으나 날짜 사용자 편집은 덮어쓰지 않고 위 최신 전체 pytest에 통합해 검사했다.

## 남은 제한·인증·운영

Earth Search Landsat requester-pays는 계속 비활성이다. PC 같은 원천 제품은 공개 대안이지만 파일 바이트/처리가 동일하다는 보장은 아니다. NASA VNP09GA 원본은 해당 DAAC Earthdata 권한, CDSE Sentinel-1 원본은 OData 토큰, 다른 USGS 경로는 M2M Application Token/권한이 별도다. 모두 이번에 발급/설정하지 않았다. EUMETSAT은 consumer key/secret·제품 조건, GK2A는 API 활용 신청/authKey, Planet은 계정/API key 또는 지원 OAuth·구매·재제공 계약이 후속 조건이며 앱 내 미연결이다.

PC 익명 SAS에는 새 환경 변수/키가 필요 없다. 제한/만료·429를 우회하지 않는다. 공개 자료라도 자체 서버 전송·클라우드 연산 비용은 별도다. 원본256MiB/미리보기8MiB·16MP, 외부35초·검사60초·스트림120초·동시2, 사용자·새 공개 제공처 각각512MiB/시간. 공개 PNG는16MiB/60초 캐시·요청 합치기, 원본은 영속 캐시하지 않는다. 캐시/receipt/한도는 단일 worker 프로세스 기준으로 공개 다중 서버 운영 완료가 아니다.

공식 제품/라이선스·등록 범위·추가 경로·화면 확인 순서는 [PUBLIC_DATA_ACCESS](docs/PUBLIC_DATA_ACCESS.md)에 기록했다. 현재 실행 주소는 http://127.0.0.1:3000 (백엔드8000). 사용자 작업 부재/재시작 승인을 받은 뒤, 경로·부모/자식 프로세스를 다시 확인해 해당 start.cmd 런처와 서버만 종료·재실행했다. .env 수정 없이 반영했으며 다른 서버·편집기는 종료하지 않았다. 검증 전용3015/8015 서버는 완료 후 종료한다. 최종 파일 디코딩 증거는 frontend/test-results/public-file-decoding.json, 실제 사이트 미리보기는 public-runtime-desktop.png/mobile.png다.

---

# 축약 날짜 범위 규칙 해석 보완 (2026-11-02, 약 11:40 KST)

사용자 입력 `2025년 8/15~8/30까지 서울시의 지표면온도를 알고 싶어`의 연도 공유 범위를 규칙으로 `2025-08-15`~`2025-08-30`에 적용한다. 같은 해의 월·일이 모두 있는 `8월 15일부터 9월 2일까지`도 처리한다. 잘못된 날짜·역전·연말을 넘는 연도 생략·여러 범위는 확인 상태로 남긴다. AI 명시 호출에서는 축약 종료일의 원문 근거와 규칙 결과가 일치해야 한다. 기존 수동 AOI는 바꾸지 않는다.

변경: `backend/app/condition_proposals.py`, `ai_interpretation.py`, 두 파일의 pytest, `frontend/tests/automatic-conditions.spec.ts`, `README.md`, 본 보고서. 기존 사용자 서버 3000/8000은 재시작하지 않았으며 화면 검증은 별도 최신 백엔드 8011을 잠시 띄워 `E2E_API_BASE_URL`로 연결한 뒤 종료했다. 실제 OpenAI/Kakao·위성 검색은 이번 테스트에서 호출하지 않았다.

| 최신 실행 | 종료 코드 | 결과 |
|---|---:|---|
| 루트 `.\.venv\Scripts\python.exe -m pytest backend/tests/test_condition_proposals.py backend/tests/test_ai_interpretation.py -q --disable-warnings` | 0 | 66 passed, 1 warning. 테스트 전용 AI 응답 사용 |
| backend `..\.venv\Scripts\python.exe -m pytest -q --disable-warnings` | 0 | 423 passed, 16 skipped, 1088 warnings. 16개 LIVE_STAC opt-in 미실행 |
| frontend `npm.cmd run typecheck` | 0 | 통과 |
| frontend `$env:E2E_API_BASE_URL='http://127.0.0.1:8011'; $env:E2E_OUTPUT_DIR='test-results-short-date'; npm.cmd run test:e2e -- tests/automatic-conditions.spec.ts -g '축약 날짜 범위'` | 0 | 실제 UI 1 passed. 규칙 응답에서 시작/종료일·열환경 목적 반영, AOI 미확정 확인 |

제한된 샌드박스의 Windows TestClient 소켓 정체로 첫 pytest 시도는 중단(종료 1)하고 허용된 로컬 실행에서 재검증했다. 처음 추가한 축약 범위의 단위 테스트는 `IndexError`와 잔여 날짜 검증 순서 문제로 실패했고 수정 후 전체 pytest를 재실행했다. production build와 전체 E2E는 이번 백엔드 중심 변경 이후 미실행이며 실행 중인 dev 서버의 `.next` 산출물을 건드리지 않았다. 최신 코드가 기존 8000 서버에 반영되려면 진행 중 작업을 확인한 뒤 해당 백엔드만 재시작해야 한다.

# 운영자 자료 접근 구현·검증 (2026-11-02, KST)

## 현재 판정

운영자 모드를 기존 FastAPI/Next.js/MapLibre의 검색·장면·밴드·미디어 API에 추가했다. 초기 `docs/OPERATOR_DATA_ACCESS.md`의 설계를 구현 증거로 사용하지 않고 실제 모듈/테스트를 작성했다. 기존 개인 NASA OAuth/DPAPI 세션, 추천·A2~A4·관측 합성·ML 엔진은 보존했다. **운영자 모드는 기본 비활성이고 현재 실제 운영자 자격증명이 없다.** 코드/fixture 통과와 실제 인증·다운로드·재제공 권한 확인은 별개다.

공개 경로를 먼저 시도하고 실패한 경우에만 해당 제공처의 운영 자격을 사용한다. USGS 세션 키는 M2M API에만, CDSE access는 공식 download 호스트에만, NASA User Token은 허용 LP DAAC 경로에만 보낸다. requester-pays S3에는 접근하지 않고 인증·비용 동의를 대신 수행하지 않았다. 새 계정/토큰 발급, 키 활성화, 유료 AI, 공개 배포·push는 없다.

## 제공처·제품별 상태와 실제 연결

| 제품/기능 | 실제 코드 | 이번 실연결 |
|---|---|---|
| S2 L2A 공개 원본 | 기존 canonical/전송 재사용, 기존 밴드 UI의 접근 확인·명시 원본 수신 연결 | 새 브라우저, 제공처 로그인 cookie 없음, SCL 전체 **1,591,434바이트** 실제 저장. GTiff 5490×5490/1band/uint8/EPSG:32652, 실제8×8 픽셀 디코딩 확인. 픽셀 QA 판정 아님 |
| Landsat C2 L2SP/L2SR 미리보기 | 기존 동일 제품 USGS STAC 대응 + M2M scene-metadata가 제공한 동일 Product ID browse 후보 | 실제 LC09_L2SP_116035_20250723_20250726_02_T1은 public USGS 경로에서 **302/usgs_login_required**. 10:51:50 KST HTTP 검색200/1건. 운영자 browse는 자격 없음/fixture만, 실제 해결 완료가 아님 |
| Landsat 개별 원본 | M2M login-token·scene-list·secondary download-options·download-request, 정확한 파일명/제품 대응 | 실제 M2M 자격 없음. 다운로드 미검증. M2M 상세 문서/예제는 비로그인 요청에서 ERS 로그인 화면으로 이동하여 계정별 스키마/실제 옵션도 재검증 필요 |
| Sentinel-1 GRD/COG | canonical OData Product UUID/동일 SAFE measurement Nodes, 공식 목록에 있는 quick-look PNG만 대체 후보. CDSE access/refresh 분리 | 실제 STAC Item200/asset 형태 확인. 운영자 원본·노드 파일·미리보기 인증은 자격 없음/fixture만. 흔한 큰 Product ZIP은256MiB 제한으로 막힐 수 있음 |
| VNP09GA.002 공개 browse | 기존 canonical CMR + 실제 이미지 수신/디코딩/receipt 경로 | LIVE 브라우저 검사 통과. NASA 인증 원본/운영자 연결 성공의 근거 아님 |
| VNP09GA.002 인증 원본/renew | 개인 OAuth와 별도 User Token/renew_token·발급 만료 검증 | 실제 운영 토큰 없음. fixture에서는 새 브라우저/서버 세션만으로 원본 수신, 만료/갱신/폐기/형식·한도를 검사 |
| 공개 재제공 검토 | 제품/컬렉션/Asset/호스트 allowlist와 제공처별 REDISTRIBUTION_REVIEWED 명시 조건 | Landsat public-domain/Sentinel 배포 라이선스/CMR VNP09GA.002 AccessConstraints=None 근거 확인. 모든 제품·계정의 포괄 허가로 간주하지 않음. 실제 운영 대상/DAAC 앱 승인·EULA·계정 쿼터 검토는 운영자 준비 사항 |

공식 문서·이용 조건·설정 이름은 [운영자 자료 접근 계약](docs/OPERATOR_DATA_ACCESS.md)에 링크와 함께 기록했다. 실제 CMR collection UMM의 ShortName=VNP09GA/Version=002/AccessConstraints=None를 읽었고, 다른 NASA 제품으로 넓히지 않았다.

## 변경 파일·API

- 신규 서버: `backend/app/operator_access.py`, `operator_adapters.py`, `operator_store.py`, `operator_preview_cache.py`.
- 기존 서버: `backend/app/media_access.py`, `provider_transfer.py`, `earthdata_auth.py`, `main.py`, `log_safety.py`.
- 서버 설정/관리자 콘솔: `scripts/server-env.mjs`, `scripts/server-env.test.mjs`, 신규 `scripts/operator-access.py`, `scripts/operator-admin.mjs`, 비활성·빈 값만 추가한 `backend/.env.example`. 실제 `backend/.env`는 변경하지 않았다.
- 프런트: `frontend/src/components/EarthdataConnection.tsx`, `AssetDownloads.tsx`. 기존 `ManagedAssetAccess`, `ProviderPreview`, 요청 큐/밴드 선택/다운로드 코드를 재사용한다.
- 테스트: 신규 `backend/tests/test_operator_access.py`, `frontend/tests/operator-access.spec.ts`.
- 문서: `AGENTS.md`, `README.md`, `docs/OPERATOR_DATA_ACCESS.md`, 본 보고서.
- 기존 `/media/inspect`/previews/downloads를 확장했다. `/auth/providers/status`, `/auth/earthdata/status`는 operator_mode/access_state/integration=operator 등 공개 상태만 추가한다. 운영 모드의 `/auth/earthdata/start`는409로 개인 연결을 막는다. 설정 이름/재연결 조치는 서버 콘솔에만 제공한다. 토큰 입력·관리 HTTP API는 만들지 않았다. 검색/분석 요청 계약과 엔진은 바꾸지 않았다.

## 보안·회전·저장·실행 제한

Windows 사용자 범위 DPAPI/보호 ACL/SQLite FULL 동기화로 별도 운영 grant를 암호화 저장한다. asyncio lock와 DB generation claim으로 중복 갱신을 막는다. renewing을 **외부 요청 전에 커밋**하며, 회전 후 저장 실패/프로세스 종료는 이전 seed로 되돌리지 않고 차단한다. 새 token seed·단조 증가 revision을 요구하고 이미 사용/폐기한 token seed와 이전 revision을 거부한다. 정적 자격의 명시 재시도와 로컬 폐기도 구분한다. 로컬 revoke는 원격 제공처 전체 철회가 아니다. 디스크 seed 이력을 삭제하는 운영은 이 보장을 유지할 수 없다.

원본256MiB/미리보기8MiB·16MP/동시2/검사60초·외부35초·스트림120초, 사용자512MiB/시간. 인증 경로는 공유 DB의 제공처1GiB·120회/시간 상한이며 인증/M2M 요청도 합산한다. 운영자 공개 경로 추가 제공처512MiB/시간은 프로세스 기준이다. 미리보기 캐시16MiB/60초/동시 작업2/요청 합치기, 같은 원본 동시 요청은 busy. 원본 영속 캐시는 없다. 기존 receipt 방문자 소유권과 운영자 세대를 함께 검사한다. 서명 URL/헤더를 로그·브라우저·링크 목록에 반환하지 않는다.

**Windows 단일 worker 실행 한정**이다. 다중 worker 설정/uvicorn multiprocessing이면 운영자 인증을 거부한다. 실제 두 별도 Python 프로세스가 같은 DB generation을 claim할 때 정확히1개만 성공하는 검사는 통과했다. 이는 웹 다중 worker 지원 완료가 아니다. 미디어 cookie/receipt/캐시는 여전히 단일 프로세스여서 다중 서버/공개 규모의 공유 secret/receipt/cache/admission 저장소는 미구현이다. 기존 개인 OAuth의 공개 callback 차단도 해제하지 않았다.

## 이번 실제 명령·시각·종료 코드

시각은 모두 **2026-11-02 Asia/Seoul(KST)**이며, 최종 결과를 과거 보고서 수치로 대체하지 않는다. 검증 서버3015/8015는 실제 .env를 로드하지 않고 AI/GEOCODER/OPERATOR를 비활성화했으며, 활성 운영자 흐름은 TestClient/HTTP mock+실제 DPAPI로 검사했다. Kakao·유료 AI는 실행하지 않았다.

| 실행 시각 KST | 명령/실행 위치 | 종료 코드 | 실제 결과 |
|---|---|---:|---|
| 11:05:02 시작/11:06:29 결과 확인 | backend: `LIVE_STAC=0 ..\.venv\Scripts\python.exe -m pytest -q --disable-warnings` | 0 | **398 passed,16 skipped**,50.43초. 기존 의존성 경고1088개. 신규 운영자 검사26건/실제 DPAPI·ACL·두 프로세스 claim 포함 |
| 11:01:15 | 루트: `node.exe scripts/frontend-check.mjs typecheck` | 0 | 독립 typecheck 통과 |
| 10:50대 | 루트: `NEXT_DIST_DIR=.next-conditions API_BASE_URL=http://127.0.0.1:8015 node.exe scripts/frontend-check.mjs build` | 0 | production compile/type/static/prerender 통과. 이후 프런트 기능 코드 변경 없음 |
| 10:50대 | 루트: `node.exe --test scripts/server-env.test.mjs` | 0 | 16 passed. 실제 child env 분리·우선순위·예시/ignore 검사 |
| 10:41대 및 10:57~10:58 | frontend: `... playwright test operator-access.spec.ts media-access.spec.ts earthdata-auth.spec.ts external-access.spec.ts` | 0 | 각32 passed/2 opt-in skipped. 두 번째는 미리보기 후보 보강/응답 검증 후 재확인 |
| 10:51~10:57 | frontend 전체 `... playwright test`, `test-results-workflow-operator-all` | 0 | 159 passed/2 skipped,5.4분. 이후 서버 전용 후보 검증 보강은 아래 최종 실행으로 확인 |
| 10:59:52~11:05대 | frontend 최종 전체 `... playwright test`, `test-results-workflow-operator-latest-all` | 0 | **159 passed,2 skipped**,5.7분. 최신 서버 후보/응답 검증 포함 |
| 별도 LIVE_STAC=1 | `... playwright test operator-access.spec.ts media-access.spec.ts --grep LIVE` | 1 | 첫 실행 NASA/Landsat public 검사1통과, S2 원본1실패: 자동 미리보기 두 전송 중 busy429 후 원본 버튼 없음. 성공으로 포장하지 않음 |
| 10:49~10:50대, LIVE_STAC=1 | `... playwright test operator-access.spec.ts --grep LIVE`, `test-results-workflow-operator-live-s2-final` | 0 | 1 passed,10.9초. 기존 미리보기 전송 종료를 기다린 후 명시 원본 접근/다운로드 성공 |
| LIVE S2 저장 후 | rasterio.open + read(window8×8) | 0 | 1,591,434바이트 GTiff/CRS/실제8×8 디코딩. evidence JSON 저장 |

E2E 공통 PowerShell 설정: `$env:E2E_BASE_URL='http://127.0.0.1:3015'`, `$env:E2E_API_BASE_URL='http://127.0.0.1:8015'`, `$env:LIVE_STAC='0'`(별도 live는1), `$env:E2E_OUTPUT_DIR='<표의 폴더>'`. 실제 명령 `node.exe node_modules/@playwright/test/cli.js test ...`는 frontend에서 실행했다. 기본1worker/msedge headless. fixture는 tests 밖 서비스 실패 대체에 사용하지 않는다.

추가 중간 실패: 새 테스트를 삽입하며 기존 함수의 마지막2줄이 잘못 이동해 nan/inf 만료값 검사4건이 NameError로 실패했다(exit1/18 passed). 테스트 범위를 고친 뒤22건, 이후26건과 전체398건으로 확인했다. 라이브 S2 진단1회는 busy 오류 확인 후 중단했으며 완료로 세지 않는다. 다른 중간 pass 수치를 최신 전체의 대용으로 사용하지 않았다.

## 남은 검증·반영

사용자가 진행 중 분석/다운로드가 없음을 확인하고 최종 검증 후 프로젝트 재시작을 승인했다. 실제 포트3000/8000 소유 프로세스의 프로젝트 절대 경로와 부모 `start.cmd` 런처43816/부모35604를 대조하고 그 tree만 종료했다. `.\start.cmd`로 숨김 재실행했으며 다른 서버/IDE 편집/실제 .env는 건드리지 않았다.

2026-11-02 **11:08:03 KST**, 웹3000·/api/health·백엔드8000/health HTTP200, `/catalog`와 `/api/catalog` 모두200/3개 제공처/4개 컬렉션. `/api/auth/providers/status`에서 세 제공처 configured=false/operator_mode=false를 확인했다. 자격증명/활성화 설정을 대신 추가하지 않아 **현재 운영자 모드는 비활성**이며, 이를 인증 성공으로 표현하지 않는다. 실제 주소는 http://127.0.0.1:3000 이다.

현재 사이트 반영 후 frontend에서 `E2E_BASE_URL=http://127.0.0.1:3000 LIVE_STAC=0 E2E_OUTPUT_DIR=test-results-workflow-operator-runtime node.exe node_modules/@playwright/test/cli.js test operator-access.spec.ts`를 실행했다. E2E_API_BASE_URL 포워딩을 해제했으며, 운영자 활성/실패와 파일 응답은 명시 TEST ONLY fixture다. 결과는 **exit0/6 passed/1 opt-in skipped,12.7초(11:08대)**. 실제 제공처 인증 성공이 아니다. 검증용 별도3015/8015 서버는 종료했다.

관리자는 `node scripts/operator-admin.mjs status <usgs|cdse|nasa>`에서 누락 설정 이름을 확인하고 공식 계정/제품별 권한·이용 조건을 직접 준비한다. 공통/제공처별 정확한 이름과 새 seed/revision/로컬 폐기 방식은 docs/OPERATOR_DATA_ACCESS.md 및 비밀 없는 backend/.env.example에 있다. 키 값을 채팅/브라우저에 전달하도록 요청하지 않았다.

실제 운영 자격을 사용한 USGS 개별 파일/browse, CDSE Product/measurement/quick-look, NASA 보호 원본/실제 renew·철회·2FA·계정별 권한 검증은 **미실행**이다. 입력할 자격값은 요청하거나 출력하지 않는다. 운영자가 제품 공개 제공 조건과 계정 한도를 검토하고 서버 전용 이름을 설정해야 한다. public S2/NASA 성공을 세 제공처의 인증 성공으로 확대하지 않는다. 실제 과금/AWS 동의·계정 발급·공개 배포·push는 하지 않았다.

---

# 자연어·공통 지명 조회·서울 행정경계 AOI (2026-11-02)

## 구현 범위와 판정

기존 Next.js/MapLibre/FastAPI, 추천·검색·품질/합성/ML 기능을 재사용했다. 규칙 해석과 AI 추출, 직접 지명 입력이 같은 `POST /places/search {place}`를 사용한다. AI 미설정이어도 명시 절대 날짜·목적·지명 조회가 가능하다. 800ms 안정화/blur, IME 보호, 진행·완료 중복 억제, 60초 반복 조회 억제, 취소/9초 상한/세대 확인을 적용한다. 추출 캐시10분과 공식 경계 캐시를 사용하며 Kakao 결과는 현재 표시용 일시 상태만 재사용한다. 새 서버/DB/localStorage 지명 좌표 캐시는 만들지 않았다.

서울이 위치 검색에서 확인되면 등록 별칭·시도 단계·상위 지역·제공된 행정코드·중심점 포함 여부를 검증해 **서울특별시 SGIS 2025년 2분기 경계**를 제안한다. 주황 점선은 미확정 제안, 파란 실선은 확정 경계 참고, 녹색 사각형은 실제 검색 bbox다. `이 영역 적용`을 눌러야 좌표/지도/검색이 동일한 외접 bbox로 확정된다. 입력 변경·직접 지명 수정은 이전 제안을 무효화하며 수동 날짜·AOI를 응답으로 덮지 않는다. 기간·목적 충돌은 `문장에서 다시 적용`, AOI 교체는 별도 명시 버튼으로 처리한다.

예문 `2025년 8월 서울시 지표면 온도 알고싶음`: `thermal`, UTC `2025-08-01`~`2025-08-31`, 지명 `서울시`를 추출한다. 지도 이동만으로 AOI를 생성하지 않는다. 제안/변경만으로 영상 검색·다운로드·픽셀 처리·유료 AI를 실행하지 않는다. 후보·0건·실패·미설정·시간 초과·경계 미지원 상태를 구분한다.

## 공식 경계 출처·범위

- [공공데이터포털 국가데이터처 SGIS 행정구역 통계 및 경계](https://www.data.go.kr/data/15129688/fileData.do), 기준2025-06-30/2025년2분기. 포털 원문 HTTP200, 무료·이용허락범위 제한 없음 표기를 확인하고 공개 ZIP을 실제 수신했다. 새 계정/키는 사용하지 않았다.
- `bnd_sido_00_2025_2Q`의 서울 레코드(SGIS SIDO_CD11)만 등록했다. 원본 EPSG:5179 → pyproj always_xy EPSG:4326 경도·위도. 꼭짓점/홀/다중 폴리곤 유지, 간소화 없음. geometry validity·코드/이름·출력 해시·bbox 재계산·중심점 포함을 검사한다. 원본 ZIP/컴포넌트/출력 해시는 metadata에 기록했다.
- bbox: `[126.76448395994285,37.42829747715147,127.18379492887969,37.70145527232949]`. 경계605.3012km², 외접 bbox 약1123.12km². **bbox 검색만 지원하고 폴리곤 클리핑은 미구현**이다. 서울 경계로 잘라 처리했다고 표시하지 않는다.
- 서울 bbox는 기존 검색 크기 상한 안이지만 S2 픽셀 처리25km² 제한을 초과한다. 사용자가 작은 AOI를 직접 지정해야 한다. Landsat 지표면온도 픽셀 계산 엔진은 이번에 추가하지 않았다.
- 이번 폴리곤 등록은 서울 전체1곳이다. 다른 한국 행정지명은 기존 Kakao REGION 조회 범위에서 점 위치/후보를 확인하고, 경계 미등록이면 수동 AOI를 안내한다. 기존 충남·상주·옛 영천군 로컬 카메라 참고는 유지했다. 전국 경계 지원 완료가 아니다.

## 변경 파일

- 서버: `backend/app/condition_proposals.py`, `place_search.py`, 신규 `admin_boundaries.py`, `data/boundaries/seoul-sgis-2025-q2.geojson`, 같은 이름의 `.metadata.json`.
- import/단위 테스트: 신규 `scripts/import-seoul-boundary.py`, `backend/tests/test_admin_boundaries.py`.
- 화면/상태: `frontend/src/lib/useConditionInput.ts`, `types.ts`, `components/AutomaticConditions.tsx`, `MapPanel.tsx`, `app/page.tsx`, `app/globals.css`.
- E2E: 신규 `frontend/tests/boundary-conditions.spec.ts`, 기존 `runtime.ts`, `ai-conditions.spec.ts`, `automatic-conditions.spec.ts`, `auto-preview.spec.ts`.
- 문서: `README.md`, 신규 `docs/ADMINISTRATIVE_AOI.md`, `docs/AI_PLACE_CONDITIONS.md`, `docs/AI_NATURAL_INPUT.md`, 본 보고서. 검증용 Next 출력 경로가 자동 추가한 tsconfig/next-env 경로는 원래 `.next` 계약으로 정리했다.
- API 변경: 기존 `PlaceRequest.text`를 선택형 호환 필드로 유지하고 `place` 단독 요청을 허용한다. 응답 후보에 선택형 `boundary` 제안을 추가했다. 검색 API bbox 계약·AI 제공처/모델·환경변수/키 설정은 변경하지 않았다.

## 이번 수정의 실제 검증

| 명령 / 실행 위치 | 종료 코드 | 실제 결과 |
|---|---:|---|
| `..\.venv\Scripts\python.exe -m pytest -q`, backend, `LIVE_STAC=0` | 0 | **372 passed,16 skipped**,26.89초. 라이브 opt-in 제외,1088개 기존 의존성 경고 |
| `node.exe scripts/frontend-check.mjs typecheck`, 루트 | 0 | 최신 소스와 테스트 독립 TypeScript 검사 통과 |
| `NEXT_DIST_DIR=.next-conditions-final`, `API_BASE_URL=http://127.0.0.1:8015`, `node.exe scripts/frontend-check.mjs build`, 루트 | 0 | 최신 production compile/type/static/prerender 완료 |
| 관련 규칙/AI/지도/경계 E2E | 0 | 중간40 passed,49.1초. 이후 직접 지명 변경 시 제안 즉시 무효화 검증도 최종 전체에 포함 |
| 전체 E2E 첫 완주, `test-results-workflow-boundary-complete` | 1 | 144 passed,5 failed,1 skipped,4 did not run(4.5분). 아래 테스트 transport 정리 후 재실행 |
| 최종 전체 E2E, `test-results-workflow-final-all` | 0 | **153 passed,1 skipped**,4.9분. 미실행1건은 LIVE_STAC=1 opt-in 공개 Landsat/NASA media 검사 |

실행 transport는 production3015 → backend8015이며 실제 사용자 .env를 로드하지 않고 AI/지명 서비스를 비활성화한 별도 검증 서버를 사용했다. 기본 Playwright msedge headless,workers1. 전체 명령은 frontend에서 `E2E_BASE_URL=http://127.0.0.1:3015 E2E_API_BASE_URL=http://127.0.0.1:8015 E2E_OUTPUT_DIR=test-results-workflow-final-all node.exe node_modules/@playwright/test/cli.js test`(PowerShell에서는 각 `$env:`로 설정).

전체 첫 완주의5실패는 모두 테스트 종료 후 미리보기 `route.fetch`가 취소되며 다음 테스트에 귀속된 오류였다. 동작 assertion을 약화하지 않고 `afterEach`에서 page/context route를 명시적으로 정리했다. 정리만으로 남은 Playwright transport 취소 오류는 `Test ended`/context 종료에 해당하는 경우에만 포워딩 callback에서 종료하도록 보완했다. 실제 네트워크/제공처 오류는 다시 throw하며 앱의 성공 결과로 대체하지 않는다. 중간 ignoreErrors/wait 방식 확인 실행은 완주 성공으로 세지 않았다. 최종 수정 후 수동 제공처 선택3건과 전체153건 통과를 확인했다. 별도 cloud QA fixture1건은 먼저 exit0/1 passed로 진단 확인했다. 루트에서 실행한 추가 pytest는 자식 인터프리터의 `app` 모듈 검색 경로가 맞지 않아369 passed/3 failed/16 skipped(exit1)였고, 문서의 backend 디렉터리에서 재실행해372 passed를 확인했다.

데스크톱/390px 모바일 실제 브라우저 스크린샷을 열어 경계/bbox·지도 출처·설명 위치와 가로 넘침을 확인했다: `frontend/test-results/seoul-boundary-desktop.png`, `boundary-mobile.png`. 입력→기간/목적→위치→제안→확정 좌표/지도/API bbox 검증은 Kakao mock과 실제 공식 로컬 경계로 수행했다.

초기 시행에서 로컬 지역 목록 오류가 추출까지 전파되는 단위 테스트1건을 고쳐 후속 통과를 확인했다. 관련 E2E는 중간39통과/1실패(blur 재해석이 후보 선택 UI를 지움)를 재현해 완료 문장 중복 억제로 고친 뒤40통과했다. 최초 E2E 로더의 CJS/import.meta 오류도 수정했다. 전체 실행 중 선택 전 장면의 목록 썸네일까지 금지하던 미리보기 테스트는 **새 선택 상세 영역에 이전 이미지가 표시되지 않는지** 검증하도록 범위를 바로잡았다. 기존 장면의 목록 미리보기 기능은 보존했다. 중간 전체 실행은 마지막 UI/직접 지명 제안 무효화 보완을 반영하기 위해 중단했으며 완주 성공으로 세지 않았다.

## 실연결·설정·남은 검증

사용자가 진행 중 분석/다운로드가 없다고 확인하고 최종 검증 후 프로젝트 재시작을 승인했다. 포트3000/8000 프로세스의 부모 런처22120와 절대 `start.cmd` 경로/해당 venv·Next 자식을 대조하고, 그 런처 tree만 종료한 뒤 `.\start.cmd`로 재시작했다. 다른 앱/서버/환경변수와 IDE 편집은 건드리지 않았다. 재시작 뒤 localhost3000 웹·/api/health·backend8000/health는 모두200, `/catalog`와 `/api/catalog`는200/3개 제공처/4개 컬렉션이다. 현재 프론트 PID6556/백엔드 PID3176(검증 당시)이다.

현재 접속 주소: **http://127.0.0.1:3000**. `/api/places/config`는200/provider=kakao/ready=true/누락 설정없음으로 확인했다. 이는 설정 인식이며 실제 Kakao 서울 조회 성공은 아니다.

재시작된 현재3000에 대한 `E2E_BASE_URL=http://127.0.0.1:3000 E2E_OUTPUT_DIR=test-results-workflow-runtime-boundary node.exe node_modules/@playwright/test/cli.js test boundary-conditions.spec.ts` 결과는 **exit0 / 9 passed,31.0초**. 별도 backend forwarding을 해제하고 실제 현재 규칙 API를 사용했으며 Kakao·AI·영상 검색 응답만 명시 fixture다. 검증용3015/8015 서버는 종료했다.

공개 영상 E2E에서는 기존 Element84/CDSE/CMR 검색과 작은 S2 AOI QA·NDVI·관측 합성·ML/ZIP 실행이 실제 통과했다. 이 결과도 Kakao 서울 실조회·열환경 픽셀 계산 성공으로 해석하지 않는다.

**이번 작업의 실제 Kakao API 조회는 미실행**이다. 모든 새 위치 성공/후보/오류·AI 응답은 TEST ONLY fixture이며 E2E 기본 transport가 Kakao 호출을 차단한다. 서버 Kakao ready는 설정 인식일 뿐 실제 서울 조회 성공의 근거가 아니다. 실제 조회가 필요하면 대상/횟수를 먼저 알린 뒤 별도 수행한다. 유료 OpenAI 호출, 키/인증 설정 변경, 계정 생성, 배포·push는 하지 않았다. 이전 보고서의 연천군 실조회와 과거 테스트 수치를 이번 서울 흐름 실연결 증거로 사용하지 않는다.

제공처 정책상 Kakao 결과의 영속 캐시를 추가하지 않았다. 자동 API 호출 상한과 현재 표시 결과 재사용 범위는 [ADMINISTRATIVE_AOI](docs/ADMINISTRATIVE_AOI.md)에 있다. 전국 폴리곤 확장, 서울 폴리곤 클리핑, 서울 전체 픽셀 계산, 실제 Kakao 서울 조회는 남은 범위다.

---

# 자동 미리보기·명시 다운로드 복구·선택형 로그인 유지 (2026-10-30)

## 현재 판정과 적용 범위

**코드는 구현했으며 핵심 검증은 통과했다. 운영 3000/8000 묶음 반영, production build·실제 브라우저와 전체 ACL을 포함한 로그인 저장 검증은 미완료다.** 과거 보고서의 build/E2E 성공을 이번 코드의 통과로 재사용하지 않는다.

화면에 보이는 제공처 미리보기를 클릭 없이 요청한다. provider/collection/Item/인증 세대별 공유 큐, 동시2·가시성·중복 제거·만료/서버 세션 복구·이미지 오류 자동복구1회를 구현했다. 원본은 사용자가 다운로드를 누른 때만 받는다. 원본/browse 저장의 receipt 만료는 같은 선택 파일을 재확인해 최대1회 복구하고, 부분 수신·인증/장면 변경·크기 초과·반복 실패를 완료로 표시하지 않는다.

NASA는 `EARTHDATA_PERSIST_SESSIONS=1` 명시 opt-in일 때만 Windows OS 사용자 DPAPI+SQLite+별도 암호화 폐기 journal로 연결을 보관한다. 기본은 기존 최대8시간 메모리이며 재시작 시 해제된다. 영속 연결은 최대30일이고 실제 access/refresh 수명과 철회는 제공처 발급값을 따른다. 이전 저장소 형식·다른 앱 설정·journal 손상/누락은 자동 복원하지 않고 격리를 요구한다. 공개 callback·다중 worker는 지원하지 않는다.

폐기 기록 저장 성공 후 DB 삭제만 실패하면 재시작 후 같은 SID 복원을 거부한다. **모든 지속 쓰기가 실패하면 영구 폐기는 보장할 수 없다.** 503, cookie 보존, 현재 프로세스 사용 차단, 구체 안내와 명시 재시도를 제공한다. 실패를 성공으로 표시하지 않고 현재/다른 탭의 큐·요청·표시를 무효화한다. 필요시 저장소 전체 격리·권한 복구 및 NASA 측 철회가 필요하다. 로컬 폐기와 NASA 계정 전체 로그아웃은 다르다.

검색 범위는 기존 3개 제공처·4개 컬렉션이다. **USGS/CDSE 신규 원본 인증은 미연결**, NASA 앱 등록 정보도 아직 미설정이다. 범용 `.env` 비밀번호나 한 제공처의 토큰으로 다른 제공처를 우회하지 않았다. 모든 사이트·위성의 인증/원본 지원 완료가 아니다. [설정과 정확한 제한](docs/AUTOMATIC_PREVIEWS.md)을 따른다.

## 실제 연결 확인

기존 `childEnvironments`의 서버 허용 이름만 메모리에서 전달해 별도 backend8015를 실행했다. 사용자 `.env` 값은 출력/복사/변경하지 않았고 키를 명령 인자·URL·결과 파일에 넣지 않았다. 기존 운영 서버를 종료하지 않았다.

| 경로 | 실제 결과 | 의미 |
|---|---|---|
| Kakao 공식 주소 API, 연천군 exact | HTTP200, REGION 결과1 | 실제 입력 키와 지명 조회 확인. 첫 stdin 한글 인코딩 손상 요청의200/0건은 진단 실패로 분리 |
| 새 앱8015 `/places/config` | HTTP200, ready=true | 서버 전용 설정 인식 |
| 새 앱8015 `/places/search` | API200, resolved, upstream200, 후보1, camera_only | 실제 앱 경유 위치 조회. 브라우저 지도 이동/AOI 확정은 미검증 |
| NASA CMR `G3626199201-LPCLOUD` preview-only inspect | API200, preview available/upstream200, access_verified=true, 원본 assets=0 | canonical 조회와 공개 browse 전체 수신·디코딩. 인증 원본/픽셀 QA 아님 |
| 같은 NASA browse receipt 이미지 | HTTP200, 전체70,963바이트 수신 | 같은 출처 실제 이미지 API 확인. 브라우저 자동 렌더 성공 아님 |
| 새 `/media/session`, `/auth/providers/status` | HTTP200, 세션 generation/epoch/HttpOnly 및 기존3개 제공처 확인 | 로컬 TestClient와 HTTP 확인 |
| 세션 없는 새 inspect | HTTP409, MEDIA_SESSION_REQUIRED | 외부 수신 전 협상 요구, TestClient 검사 |
| 기존3000/8000 위치 config | HTTP200, ready=false, 두 설정 누락 | 파일 변경 전 실행 프로세스 상태. 기존 서버에 재시작 반영 필요 |

실제 NASA 사용자 로그인/발급·갱신·인증 원본 다운로드, USGS/CDSE 인증은 실행하지 않았다. Kakao는 위성 파일 로그인과 별개다. 자세한 리더 확인은 [실연결 기록](docs/agent-runs/auto-preview-auth/leader-live-checks.md)에 있다.

## 검증 명령과 실패·미실행 구분

| 실행 | 종료 코드 | 결과 |
|---|---:|---|
| backend 전체 pytest, 테스트 전용 작업 폴더 fixture 등록 | 0 | **359 passed / 17 skipped**, 97.63초, 1089 warnings. 전체 실행 뒤 작은 성공 응답 메타데이터 보강은 아래 최종 담당 검사로 확인 |
| 최종 backend auth/persistence/media pytest | 0 | **68 passed / 1 skipped**, 7.61초. 마지막 메타데이터 변경 포함. TEST ONLY OAuth·grant |
| QA 독립 최종 backend 동일 핵심 검사 | 0 | **68 passed / 1 skipped**, 8.36초. 이전 독립65개 이후 늦은 변경 재확인 |
| root `node.exe scripts/frontend-check.mjs typecheck` | 0 | 담당·QA 최종 strict TS 통과 |
| frontend Playwright `--list`, auto-preview/media/Earthdata 3파일 | 0 | **31개 수집**. 브라우저 실행/통과가 아님 |
| 실제 큐·전송·연결 컴포넌트를 transpile한 Node VM fixture | 0 | 큐5그룹, 명시 전송20검사, 최종 연결 상태 전이16검사. 실제 React DOM·브라우저/제공처 인증 아님 |
| root `node.exe --test scripts/server-env.test.mjs` | 1 | runner 하위 프로세스 시작 `spawn EPERM` |
| 같은 Node `--test-isolation=none` | 1 | **13 passed / 2 failed**. 자식 환경·임시 Git 검사는 프로세스 생성 권한 오류. 전체 통과 아님 |
| 격리 `.next-auto-preview-qa` production build | 1 | 최적화 단계 `spawn EPERM`, 완료 안 됨 |
| 격리 전체 Playwright | 1 | WorkerHost `spawn EPERM`, 브라우저 assertion 전 중단. 통과0으로 구분 |
| Computer Use 화면 관찰 | 미완료 | 브라우저 host unavailable 후 native Windows의 현재 URL 신뢰 확인 실패로 중단. 이후 UI 입력 중단, 스크린샷/실제 렌더 성공 근거 없음 |

17 skip은 LIVE_STAC opt-in16개와 **실제 Windows ACL 설치를 포함한 저장 준비1개**다. 실제 DPAPI 암복호화·새 인터프리터 복원 거부 검사는 수행했으나 ACL 함수는 해당 fixture에서 명시 mock했다. 제품의 ACL 준비 조건을 완화하거나 실패를 메모리 성공으로 바꾸지 않았다. 실제 정상 OS 권한 환경의 저장 준비·서버 재시작·NASA 인증 검증이 필요하다.

전체 pytest에서 기존 TEMP mode0700의 접근 거부가 발생해 테스트 전용 상속 ACL 임시 fixture를 저장소 안의 새 무작위 경로에 등록했다. 다른 테스트를 지우거나 제품 권한을 우회한 실행이 아니다. 회차1 전체의 TEMP setup43오류·초기 새 fixture5 teardown오류, 회차2 초기 재연결 표시 회귀2실패는 역할별 보고에 남겼고 수정 후 통과했다. 프런트 편집 중 TS 구문 오류와 VM harness 인코딩/탐색 오류도 수정 후 최종 검사와 분리 기록했다. 동일한 EPERM 환경의 build/브라우저 실패를 반복해 통과로 바꾸지 않았다.

대표 최종 핵심 명령(backend):

```powershell
..\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --disable-warnings tests/test_earthdata_auth.py tests/test_earthdata_persistence.py tests/test_media_access.py
```

전체 실행의 작업 폴더 fixture 등록 명령과 정확한 변경/중간 실패는 [Auth 회차2](docs/agent-runs/auto-preview-auth/round-2/auth.md), 독립 판정은 [QA](docs/agent-runs/auto-preview-auth/round-2/qa.md)와 [보안](docs/agent-runs/auto-preview-auth/round-2/security.md)을 따른다. 두 차례 구현·검토와 양쪽 상호 토론·분석관 인계를 마쳤으며 [리더 최종 인계](docs/agent-runs/auto-preview-auth/leader-result.md)에 잔여 조건을 기록했다. 세 번째 구현 루프는 진행하지 않는다.

## 운영 반영과 남은 작업

기존 3000/8000 서버는 진행 중 분석·다운로드 확인 답변을 기다려 종료하지 않았다. 검증용8015만 리더가 시작해 API를 확인한 뒤 종료했으며 해당 포트 listen 없음과 기존3000/8000 listen 유지를 확인했다. production build·실제 브라우저·전체 ACL·실제 제공처 로그인/원본 접근, USGS/CDSE 연동과 공개 운영은 남은 범위다. 코드·설정 인식·실제 공개 browse 수신을 웹사이트 전체 인증/다운로드 완료로 표현하지 않는다.

# 이전 기록: AI 자연어 → 단일 검색 조건·Kakao 위치 확인 (2026-10-30)

## 변경 내용과 실제 제약

기존 OpenAI Responses/strict schema, 목적 규칙·추천, Next.js 폼, MapLibre 카메라와 수동 AOI를 확장했다. 기존 코드가 AI 목적을 간접 계산하고 미등록 지명을 고정 3개 목록으로 처리하던 문제를 수정했다. `FormConditions`가 목적·기간·분석 형태·좌표/확정을 관리하며 AI/수동 출처를 보존한다. 목적 추출/기간 검증/지명 원문/위치 검색/AOI 확정을 별도 표시한다. 지명 위치는 카메라 전용이고 자동 AOI·자동 검색·자동 픽셀 처리는 없다.

사용자는 지명 서비스 선택 질문에서 **Kakao 서버 키 방식, 설정 전 위치 검색 비활성**을 선택했다. 현재 `KAKAO_LOCAL_REST_API_KEY`와 `GEOCODER_ENABLED`가 없음을 존재 여부로만 확인했다. 실제 키·OpenAI 키 값은 출력/복사/수정하지 않았다. Kakao 결과를 실제로 얻은 것처럼 표시하지 않는다. API 키가 없는 현재의 실제 동작은 **“연천군 인식됨 · 위치 검색 미설정”**이며 수동 지도/좌표 입력을 유지한다.

`2026년 7월 연천군의 지표면온도를 분석하고 싶어`의 AI 추출/검증 fixture에서는 thermal·지표면온도, UTC 2026-07-01~31, 원문 연천군이 반영된다. Kakao 모의 REGION 결과의 명칭·상위 지역·중심점·출처·확인 시각을 표시하고 지도만 이동한다. 빈 AOI/좌표는 유지하며 수동 AOI 확정 뒤 같은 목적·기간·bbox가 기존 Landsat 검색 요청에 전달되는 것을 브라우저에서 검증했다. **실제 OpenAI 유료 추출과 인증된 Kakao 지명 결과 검증은 미실행**이다.

실제 제공처 확인: Kakao 공식 주소 검색 endpoint에 인증 헤더 없이 읽기 전용 요청 1회 → **HTTP 401**, 명령 종료 코드0. 인증 필요 응답이며 위치 검색 성공이 아니다. 조사 중 받은 Nominatim 연천군 공개 응답은 제품에 연결/대체하지 않았다. 기존 로컬 충남·상주·영천 카메라 참고 자료는 그대로 유지한다. 전국 지명이 3개뿐이거나 목록 밖 지명이 존재하지 않는다고 판정하지 않는다.

## 실제 변경 파일

- backend: `backend/app/ai_interpretation.py`, `condition_proposals.py`, `main.py`; 새 `place_search.py`; `backend/tests/test_ai_interpretation.py`, 새 `test_place_search.py`.
- frontend: `frontend/src/lib/useConditionInput.ts`, `types.ts`, `frontend/src/components/AutomaticConditions.tsx`, `MapPanel.tsx`, `frontend/src/app/page.tsx`, `globals.css`; `frontend/tests/ai-camera.spec.ts`, 새 `ai-conditions.spec.ts`.
- 서버 설정: `scripts/server-env.mjs`, `scripts/server-env.test.mjs`, `backend/.env.example`(기존 값 보존, 새 변수 이름·비활성/빈 예시만 추가). 실제 `backend/.env`는 변경하지 않았다.
- 문서: `README.md`, `docs/AI_NATURAL_INPUT.md`, 새 `docs/AI_PLACE_CONDITIONS.md`, 이 보고서.

`request_interpretation.py`, `data/regions.json`은 검토 후 재사용했으며 기존 사양·추천·검색·A2~A4·합성·ML·미리보기/다운로드 엔진은 교체하지 않았다. 의존성/lock 설치·변경, 계정 생성, 키 발급·설정, 배포·push는 하지 않았다.

## API·보안·모호성

기존 AI 스키마에 원문 분석 대상과 응답의 지명/근거 보존을 추가했다. 원문에 없는 지명/대상, 좌표·임의 필드, 잘못된 날짜/기간은 거부한다. 상대 날짜·연도 없는 월·일대/주변·사건 전후 기준은 자동 확정하지 않는다. 최종 서버 보완은 AI가 플래그를 빠뜨려도 raw “지난 장마/전후”를 별도 확인하도록 한다.

새 `GET /places/config`, `POST /places/search {text,place}`를 추가했다. Kakao 고정 HTTPS 주소의 헤더에만 REST 키를 사용하고 응답/프런트/URL/로그에 키를 넣지 않는다. REGION만 사용하고 다른 주소/POI·부모 구역으로 대체하지 않는다. 결과 0건·미설정·401/403·429·시간 초과·장애·잘못된 응답·동명 후보/미조회 페이지를 구별한다. 중심점은 분석 bbox가 아니다. 서버 제공처 데이터 캐시/DB/localStorage/manifest 저장 없음. UI의 현재 일시 상태만 유지한다. 후보 선택은 새 AI 호출을 하지 않는다.

수동 날짜/목적/분석 형태/좌표는 늦은 응답으로 덮지 않는다. 지도/AOI 수동 조작 뒤 온 위치는 자동 적용하지 않으며 명시 이동으로 확인한다. 문장/후보 변경·취소·IME 시 이전 응답을 폐기한다. 목적·날짜 변경은 기존 결과/계획/레이어 무효화에 연결한다. 기존 Landsat 열환경 규칙을 쓰고 Sentinel-2를 직접 열적외선 대안으로 만들지 않았다.

## 실제 검증 명령과 종료 코드

검증용 앱은 `http://127.0.0.1:3015` → backend8015, production `.next-conditions`이며 실제 3000의 `.next`와 분리했다. 서버 AI/외부 위치 처리는 비활성으로 시작하고 E2E의 명시 TEST ONLY 응답만 AI/Kakao 성공을 모사했다. 서비스 장애 시 fixture로 대체하는 앱 코드는 없다.

| 위치 / 명령 | 종료 코드 | 결과 |
|---|---:|---|
| backend `..\.venv\Scripts\python.exe -m pytest -q --disable-warnings` | 0 | **323 passed / 16 skipped**, 최종 19.61초, 1088 warnings. LIVE_STAC opt-in 16개 미실행 |
| root `node.exe scripts/frontend-check.mjs typecheck` | 0 | 최신 TS/테스트 독립 검사 통과 |
| root `node.exe --test scripts/server-env.test.mjs` | 0 | **14 passed**. Kakao 키의 서버 전용 전달/프런트 차단·환경 우선순위 추가 |
| root `NEXT_DIST_DIR=.next-conditions`, `API_BASE_URL=http://127.0.0.1:8015`, `node.exe scripts/frontend-check.mjs build` | 0 | 최신 production build·TypeScript·정적 페이지·traces 통과 |
| frontend `E2E_BASE_URL=http://127.0.0.1:3015`, `E2E_OUTPUT_DIR=test-results-workflow-ai-place-focus`, `npm.cmd run test:e2e -- tests/ai-conditions.spec.ts tests/ai-camera.spec.ts tests/automatic-conditions.spec.ts` | 0 | 중간 관련 검증 **31 passed (37.6초)** |
| frontend `E2E_BASE_URL=http://127.0.0.1:3015`, `E2E_OUTPUT_DIR=test-results-workflow-ai-place-all`, `npm.cmd run test:e2e` | 0 | 최종 raw 상대 날짜/전후 서버 보완 직전 backend의 **125 passed (4.4분)**. 최신 서버 전체 근거로 재사용하지 않음 |
| frontend `E2E_BASE_URL=http://127.0.0.1:3015`, `E2E_OUTPUT_DIR=test-results-workflow-ai-place-final`, `npm.cmd run test:e2e` | 0 | 최종 backend 재시작·build 후 **125 passed (4.1분)**. 자동 test retry 없음 |
| frontend `E2E_BASE_URL=http://127.0.0.1:3000`, `E2E_OUTPUT_DIR=test-results-workflow-ai-place-applied`, `npm.cmd run test:e2e -- tests/ai-conditions.spec.ts` | 0 | 실제 사용 사이트 재시작 후 **9 passed (14.0초)**. AI/Kakao 성공은 명시 fixture이며 실제 유료/인증 호출 아님 |

새 테스트는 연천군 원문/목적/명시 월·빈 AOI, 실제 API 계약과 단일 검색 값, 미설정/0건/장애/상한/시간 초과, 동명 후보 선택, 잘못된 좌표/상위 구역/POI 거부, 지명·대상 원문 근거, 상대 날짜 플래그 누락, 수동 필드 보호·빠른 새 문장/늦은 응답 폐기·모바일을 검사한다. 기존 영천군 옛 지명과 날짜, 추천·비교·밴드·다운로드·실 S2 QA/NDVI·관측 합성/ML·지도·모바일은 전체 E2E에 포함한다. Kakao 모의 응답은 실제 사용자 키/권한/지명 정확성의 증거가 아니다.

모바일 스크린샷 `frontend/test-results/ai-place-mobile.png`를 열어 확인했다. 비밀값은 포함하지 않는다. 초기 조사용 Python 출력은 CP949 인코딩으로 공개 지명 출력에 실패해 UTF-8로 다시 확인했고, PowerShell의 Node `-e` 인용 오류는 값을 출력하지 않는 Python 존재 여부 검사로 대체했다. 해당 진단 실패는 서비스 테스트 통과 증거로 사용하지 않는다.

## 설정과 남은 확인

실제 지원 대상은 Kakao 주소 서비스가 반환하는 국내 REGION 행정 지명이다. 완전한 전국/해외 목록, 정부 행정경계, 경계 AOI 자동 확정은 지원하지 않는다. 기존 3개 로컬 자료의 출처/옛 지명 안내는 유지한다. 운영자가 Kakao Developers에서 앱/카카오맵 사용 설정·현재 권한/쿼터를 확인하고 `backend/.env`에 `GEOCODER_ENABLED=1`, `KAKAO_LOCAL_REST_API_KEY`를 직접 준비해야 인증된 실위치 검증을 진행할 수 있다. 키 값은 채팅에 요청하지 않는다. 공식 API/MapLibre 실시간 사용·저장 제한 근거와 설정 절차는 [AI_PLACE_CONDITIONS](docs/AI_PLACE_CONDITIONS.md)를 따른다.

재시작 반영: 사용자가 진행 중 분석/다운로드 없음과 최종 검증 후 프로젝트 재시작을 승인했다. 최종 전체125 E2E 통과 뒤 기존 런처19520·프로젝트 자식 경로/부모 관계를 재확인하고 해당 트리만 종료해 루트 `.\start.cmd`로 재시작했다. 현재 런처14192, backend9156(8000), frontend13884(3000)이다. 검증용 3015/8015 서버는 종료했다. 다른 서버·사용자 편집·실제 `.env` 설정은 보존했다. **http://127.0.0.1:3000/** 에 최신 코드 반영 완료.

실제 사용 사이트 `/`, backend `/health`, `/api/health`, `/api/places/config`는 모두200이다. 실제 `/api/places/search`에 예시의 원문+연천군을 보내 API200, status=not_configured, mentioned_text=연천군, upstream 요청 없음(http_status=null)을 확인했다. `/api/request/config`는 ready=true/provider=openai/model=gpt-5.6-luna/missing_settings=[]이며 기존 사용자 모델을 바꾸지 않았다. 이는 설정 인식 성공이지 실제 OpenAI 모델 응답 성공이 아니다. Kakao는 ready=false, 누락 이름 GEOCODER_ENABLED/KAKAO_LOCAL_REST_API_KEY다. 실제 앱의 브라우저9개 추가 검증도 모두 통과했다. 설정·키 값은 출력하지 않았다.

# 이전 기록: 제공처별 미리보기·원본 접근·조건부 OAuth 갱신 (2026-10-30)

## 변경 범위와 실제 원인

기존 검색·추천·장면/밴드 선택·AOI/기간·비교·A2~A4·합성·ML 엔진은 재사용했다. Earth Search Landsat는 미리보기 Asset이 없는 것이 아니라 S3 requester-pays여서 기존 공개 HTTP 이미지 경로에서 빠졌다. 같은 전체 제품·파일의 USGS 경로를 검증했지만 표본은 실제 GET에 USGS 로그인 **302**였다. NASA browse는 공개 이미지와 Earthdata 인증 원본을 분리했다. 기존 OAuth 코드에는 갱신과 원본 전송이 없어 해당 경로를 확장했다. 구현 전 원인·수정 파일·검증 명령을 안내했다.

**변경 파일:**

- backend 수정: `backend/app/earthdata_auth.py`, `main.py`, `assets.py`, `metadata.py`, `backend/tests/test_earthdata_auth.py`.
- backend 추가: `backend/app/provider_transfer.py`(제한된 제공처 통신), `landsat_access.py`(동일 USGS 제품/파일 대조), `media_access.py`(진단·세션 귀속 이미지/원본 전송), `log_safety.py`(OAuth query/receipt 로그 가림), `backend/tests/test_media_access.py`.
- frontend 수정: `frontend/src/components/Results.tsx`, `AssetDownloads.tsx`, `ImageryExplorer.tsx`, `SceneComparison.tsx`, `EarthdataConnection.tsx`, `frontend/src/lib/types.ts`, `frontend/src/app/globals.css`.
- frontend 추가: `frontend/src/components/ProviderPreview.tsx`, `ManagedAssetAccess.tsx`, `frontend/src/lib/useProviderAccess.ts`, `frontend/tests/media-access.spec.ts`.
- 문서: `README.md`, `docs/EARTHDATA_USER_AUTH_DESIGN.md`, `docs/PROVIDER_MEDIA_ACCESS.md`, 이 보고서. `.env`, 예시 환경 파일, 패키지/lock, 기존 추천·분석 엔진은 수정하지 않았다.

## 실제 제공처 접근

검증용 웹 `http://127.0.0.1:3015` → 최신 backend `8015`에서 **실제 HTTP 요청**으로 다음을 확인했다. mock을 서비스 실패 대체로 사용하지 않았다.

| 표본 / 경로 | 실제 결과 | 판정 |
|---|---|---|
| Earth Search `LC09_L2SP_116035_20250723_02_T1` | canonical 200, thumbnail·browse·원본 S3 Asset 존재/requester-pays | 자료 없음 아님. AWS 인증/비용 우회 안 함 |
| USGS 전체 제품 `LC09_L2SP_116035_20250723_20250726_02_T1` SR/ST | Item 200, 플랫폼·UTC 촬영시각·L2SP·Collection 02·scene ID·제품/파일명 일치 | 다른 처리일/제품 파일 대체 금지 |
| 대응한 USGS thumbnail/큰 browse/`lwir11` | GET **302**, ERS 로그인 이동 | `usgs_login_required`, 익명 이미지·원본 성공 아님 |
| CMR `G3626199201-LPCLOUD` VNP09GA.002 | canonical 200 | 실제 granule |
| 같은 NASA granule 공개 browse | LP DAAC/허용 CloudFront 리다이렉트, 전체 JPEG **70,963바이트**, 최종 GET 200·디코딩·브라우저 표시 | 공개 browse 성공. 원본/픽셀 QA 성공 아님 |
| NASA 원본 | 익명 직접 접근은 Earthdata 로그인 이동 후 401. 최신 앱의 선택 원본 확인은 `earthdata_not_configured` | 실제 사용자 원본 전송 미실행 |
| Earthdata 앱 설정/사용자 OAuth | ID·secret·callback 모두 미설정(존재 여부만 확인), status configured=false/connected=false | 실제 발급·갱신·사용자 권한 미검증 |

초기 진단 구현에서 로그인 이동을 내부 401로 분류한 것을 고쳐, 최종 보고/API에는 실제 upstream **302**를 유지한다. HTTP HEAD나 GET Range 성공은 전체 파일 다운로드로 기록하지 않는다. Landsat 원본이 익명 접근되지 않아 RGB 생성하지 않았다. 공식 근거/정확한 Item 링크/인증 구분은 [제공처 접근 문서](docs/PROVIDER_MEDIA_ACCESS.md)를 따른다. 사용자 지정 USGS FAQ 페이지는 조회 시간 초과로 직접 확인하지 못했고 STAC 공식 문서·실제 Item/Asset 응답을 근거로 삼았다.

## 최신 변경 후 검증

| 실행 위치 / 명령 | 종료 코드 | 결과 |
|---|---:|---|
| backend `..\.venv\Scripts\python.exe -m pytest -q --disable-warnings` | 0 | **301 passed, 16 skipped**, 15.32초. LIVE_STAC opt-in 16개는 미실행. 1088 warnings 출력. 실제 공개 접근은 아래 E2E/별도 HTTP 검증으로 확인 |
| root `node.exe scripts/frontend-check.mjs typecheck` | 0 | 독립 TypeScript 검사 통과 |
| root `node.exe --test scripts/server-env.test.mjs` | 0 | **13 passed**. 앱 설정의 backend 전용 전달, 개인 User Token 미로딩, frontend/build 비밀 제거·환경 우선순위 |
| frontend `E2E_BASE_URL=http://127.0.0.1:3015`, `E2E_OUTPUT_DIR=test-results-workflow-media-latest`, `npm.cmd run test:e2e` | 1 | **115 passed / 1 failed (7.4분)**. 추천 카드 완료 0건 fixture 테스트에서 카드가 나오지 않아 120초 click timeout. 실패 snapshot은 지도/AI 설정도 초기화되지 않은 상태. 원인은 확정하지 않았으며 이번 media 9개는 모두 통과. 실패 결과 보존 |
| root `NEXT_DIST_DIR=.next-conditions`, `API_BASE_URL=http://127.0.0.1:8015`, `node.exe scripts/frontend-check.mjs build` | 0 | 검증용 dev 서버 종료 후 production build·독립 build TypeScript·정적 페이지·traces 통과. 기존 3000의 `.next`와 분리 |
| frontend `E2E_BASE_URL=http://127.0.0.1:3015`, `E2E_OUTPUT_DIR=test-results-workflow-media-production`, `npm.cmd run test:e2e` | 0 | 같은 최신 코드의 production 실행 서버에서 **116 passed (4.2분)**. 앞선 실패한 추천 카드 0건 테스트 포함 전체 통과. 테스트 자동 retry 없음 |
| frontend 실제 3000 사이트 선별 E2E (아래 명령) | 0 | **2 passed (15.4초)**. 재시작 후 실제 Landsat 대응/NASA 공개 browse 표시, catalog와 현재 제공처 옵션 |


재시작 후 선별 검증의 실제 PowerShell 명령(frontend):

```powershell
$env:E2E_BASE_URL='http://127.0.0.1:3000'
$env:E2E_OUTPUT_DIR='test-results-workflow-media-applied'
npm.cmd run test:e2e -- tests/media-access.spec.ts tests/provider-activation.spec.ts --grep 'LIVE 공개|현재 실행 백엔드'
```

첫 pytest 수집은 새 이미지 코드의 Pillow 의존성으로 19개 수집 오류가 발생했다. 설치하지 않고 기존 rasterio/GDAL 디코딩으로 수정했다. 초기 새 테스트 중 AsyncClient mock 중복 교체 1개 실패는 mock 구성 수정 후 통과했다. 이전 중간 실행 273/296/300 pytest와 16개 focused E2E, 마지막 소규모 보완 전 전체 **116 passed (5.3분)**도 실행했으나 최신 전체 코드 근거는 위 최종 실행을 사용한다.

추가 테스트는 Asset 없음/형식, 공개 이미지 수신, 401/403/404·EULA/앱 승인 원인 구별, requester-pays, 정확한 Landsat 대응 불일치, 갱신 동시성/회전/거부·만료/로그아웃 경합, 사용자간 receipt 격리, 비공개 세션 결합, URL/리다이렉트/사설 DNS 차단, 인증 헤더의 다른 호스트 유출 차단, 로그 마스킹, 시간/용량/전송량/동시성 상한, HTTP 200 오류 JSON 거부, 늦은 선택/밴드 응답 폐기를 검사한다. 인증 성공·원본 전송·OAuth 갱신은 **가짜 키와 모의 응답** 테스트이며 실사용자 인증 성공 증거가 아니다.

브라우저에서 390px 모바일 레이아웃과 실제 NASA JPEG 표시를 확인했다. `frontend/test-results/media-mobile.png`, `media-nasa-live.png`를 열어 확인했으며 비밀값/서명 URL은 포함하지 않았다. 기존 원본 링크 저장·밴드 선택·비교·모바일, 실 S2 QA/NDVI ZIP·관측 합성·ML 결과/지도 회귀는 전체 E2E 범위에 포함된다.

## 구현 상태와 제약

| 기능 | 상태 | 제한 |
|---|---|---|
| Landsat 미리보기 | 부분 구현 | 정확한 공식 대응/원인 진단 완료. 표본은 USGS 로그인 필요, 익명 표시 불가 |
| Landsat 원본 다운로드 | 부분 구현 | 정확한 파일 대조·범위 확인/안전 전송 경로. 현재 표본은 USGS 로그인 필요. USGS 인증/AWS 비용 동의 연동 미구현, EarthExplorer 절차 제공 |
| NASA 공개 미리보기 | 구현·실접근 확인 | 해당 VNP09GA granule 전체 JPEG 확인. 비공개 browse는 모의 인증 검증만 |
| NASA 인증 원본 | 부분 구현 | 사용자 세션·canonical Asset·제한된 전체 전송 구현/모의 테스트. 실사용자 권한·원본 다운로드 미실행 |
| OAuth 갱신 | 부분 구현 | 실제 발급된 refresh token만 잠금/원자 교체·제한 재시도. 실제 발급 응답·갱신 허용 여부 미검증 |
| 공개 다중 사용자 운영 | 미구현 | 공유 암호화 저장소/키 관리·분산 잠금 전 공개 callback 차단. 로컬 메모리 최대8시간·재시작 시 해제 |

토큰/인증 헤더/서명 URL은 브라우저·링크 목록·manifest·로그에 전달하지 않는다. 새 의존성 설치·사용자 계정/키 설정·유료 AI 호출·SAR/VIIRS 분석 엔진·배포·push는 하지 않았다.

실행 반영: 사용자가 진행 중 작업 없음을 확인하고 검증 후 3000/8000 프로젝트 재시작을 승인했다. 최종 build/전체 production E2E 통과 후 경로·부모 관계를 재확인하여 기존 런처 **43896**와 자식 2024/43852·2944/37084만 종료하고 루트 `.\start.cmd`로 재시작했다. 현재 런처 **19520**, backend **36092**(8000), frontend **33460**(3000)이다. 웹 `/`, backend `/health`, 웹 `/api/health`·`/api/catalog`·`/api/auth/earthdata/status`·`/api/media/session` 모두 **200**. Earthdata status는 configured=false/connected=false/refresh_available=false다. 실제 사이트에서 추가 E2E 2개도 통과했다. 검증용 3015/8015 서버만 종료했고 다른 서버·환경 파일·사용자 편집은 유지했다. 실제 사용 주소는 **http://127.0.0.1:3000/** 이다.

재시작 후 실제 3000의 `/api/media/inspect`에 두 canonical 표본의 선택 원본만 POST한 읽기 전용 확인도 종료 코드0이었다. Landsat `lwir11`은 API200/상태 usgs_login_required/upstream302/access_verified=false, NASA `granule-0`은 API200/earthdata_not_configured/upstream 미요청/access_verified=false였다. API200은 진단 응답 성공일 뿐 파일 접근 성공이 아니다. 이 확인에서도 원본 자동 다운로드·사용자 인증·유료 API 호출은 실행하지 않았다.

# 이전 기록: Earthdata 사용자별 계정 연결 코드 검증 (2026-10-30 15:04 KST)

**현재 범위:** `backend/app/earthdata_auth.py`와 `main.py`에 Earthdata OAuth authorization-code 시작·콜백·상태·사이트 연결 해제 API를 추가했다. `scripts/server-env.mjs`는 앱 등록 정보 3개만 서버로 전달하고 프런트에서 제거한다. 화면 상단 `Earthdata 계정 연결`은 등록 정보가 있을 때만 활성화된다. 사용자별 접근 토큰은 로컬 단일 서버의 메모리에만 저장하고 브라우저/공용 `.env`에 내보내지 않는다. 기존 CMR 검색과 원본 직접 링크 차단을 유지한다. 사용자 `backend/.env` 값은 읽거나 수정하지 않았다.

| 최신 실행 명령 | 종료 코드 | 실제 결과 |
|---|---:|---|
| backend `..\.venv\Scripts\python.exe -m pytest -q tests/test_earthdata_auth.py --disable-warnings` | 0 | **4 passed**. 가짜 코드/토큰 fixture의 설정 누락, 잘못된 callback, state·1회 사용, 사용자 분리, 거부/교환 실패, 사이트 연결 해제 |
| backend `..\.venv\Scripts\python.exe -m pytest -q --disable-warnings` | 0 | **273 passed, 16 skipped**. 기존 16개 opt-in 실연결은 실행하지 않음 |
| root `node.exe --test scripts/server-env.test.mjs` | 0 | **13 passed**. 앱 비밀의 백엔드 전용 전달, 개인 User Token 파일 미로딩 포함 |
| root `node.exe scripts/frontend-check.mjs typecheck` | 0 | 최신 TS/테스트 독립 검사 통과 |
| root `$env:NEXT_DIST_DIR='.next-earthdata-check'; node.exe scripts/frontend-check.mjs build` | 0 | production build·TypeScript·정적 페이지 생성 통과. 임시 build 경로의 자동 `tsconfig` 추가는 제거 |
| frontend `$env:E2E_OUTPUT_DIR='test-results-earthdata-auth'; npm.cmd run test:e2e -- tests/earthdata-auth.spec.ts tests/providers.spec.ts` | 0 | **5 passed**. 연결 상태 버튼/연결 해제 UI fixture 2건, 기존 제공처·모바일·공개 검색 3건 |

샌드박스 내 pytest/TestClient는 Windows 로컬 소켓 생성에 대기했고, 환경변수 테스트 2건은 임시 폴더 권한, build는 mkdir, Playwright는 Edge 실행 권한에 막혔다. 해당 명령을 승인된 샌드박스 밖에서 다시 실행해 위 결과를 얻었다. 첫 E2E의 안내 문구 단언 1건은 테스트 기대문을 실제 문구로 수정한 뒤 전체 5건을 재실행해 통과했다. fixture는 테스트 전용이며 NASA 연결 성공 증거가 아니다.

**미검증/미구현:** Earthdata 애플리케이션 등록·client 자격·실제 사용자 로그인 왕복은 아직 없어서 라이브 OAuth 테스트는 **미실행**이다. 현재 발급된 개인 User Token은 이 OAuth 흐름에 사용하지 않는다. 서버 세션은 단일 프로세스 메모리·최대 1시간이며 재시작 시 해제된다. refresh·다중 서버 공유 암호화 세션·NASA HDF5 인증 다운로드는 구현하지 않았다. 기존 3000/8000 실행 프로세스는 진행 중인 분석 작업을 확인할 수 없어 재시작하지 않았다. 실제 `http://127.0.0.1:3000/api/auth/earthdata/status`는 **404**였으므로 현재 열린 사이트는 새 백엔드 경로를 아직 제공하지 않는다. 화면은 이전 서버라는 안내를 표시한다. 등록 조건과 남은 단계는 [설계](docs/EARTHDATA_USER_AUTH_DESIGN.md)에 기록했다.

# 이전 기록: 3000/8000 웹사이트 반영·실검색 검증 (2026-10-30)

## 실행 버전 불일치와 안전한 적용

프로젝트 `C:\Users\aicam\Documents\ChatGPT\바이브코딩`의 AGENTS·README·최신 코드·기존 검증 기록을 확인했다. 실행 전 3000/8000 health는 200이지만 `/catalog`, `/api/catalog`는 404였고 실행 중 OpenAPI에도 catalog 경로가 없었다. 디스크 `backend/app/main.py`에는 해당 경로와 신규 어댑터가 존재했다. `scripts/start-local.mjs`의 uvicorn에는 자동 reload가 없다. 기능 부재가 아닌 실행 버전 불일치로 확인했다.

실행 트리: 프로젝트 런처 17560 → venv Python 14112 → backend 31584, 같은 런처 → Next CLI 1856 → frontend 34344. 경로와 부모 관계를 재확인했다. 기존 서버는 JOBS 전체 목록 API가 없어 작업 부재를 확정할 수 없었으므로 사용자에게 먼저 물었다. 사용자가 **“진행 중인 작업 없음 — 프로젝트 재시작 진행”**이라고 확인한 뒤에만 해당 트리를 종료했다. 다른 Python `server.py`, 도구 서버, IDE/편집기는 건드리지 않았다.

루트 `.\start.cmd`로 재실행했다. 현재 런처 43896 → Python 2024 → backend 43852(8000), 런처 → Next CLI 2944 → frontend 37084(3000)이다. 웹사이트는 **http://127.0.0.1:3000/** 에서 계속 실행 중이다. backend `/catalog`와 frontend `/api/catalog`는 각각 200이며 아래 3개 제공처/4개 컬렉션을 반환한다. 양쪽 health도 최종 200이다.

- 제공처: `earth-search`, `copernicus`, `nasa-cmr`.
- 컬렉션: `sentinel-2-l2a`, `landsat-c2-l2`, `sentinel-1-grd`, `viirs-vnp09ga-002`.

기존 `backend/.env`는 수정하거나 값을 출력하지 않았다. 기존 런처의 서버 전용 로딩을 그대로 재사용했고 인증키 설정·새 토큰 발급·유료 호출·자동 원본 다운로드·분석 실행·Supabase·배포·push는 하지 않았다. 최종 `/request/config`에서 이번 실행의 OpenAI 요청은 **0회**였다.

## 최소 화면 수정

- `frontend/src/app/page.tsx`: 기존 폼/추천/검색 상태 재사용. 카드 선택 시 수동 컬렉션도 해당 제품으로 맞춘다. 이후 수동 모드/체크박스 변경은 카드 선택을 해제한다. 마지막 선택이 실제 요청에 반영되며 검색 직전 `최종 검색 컬렉션`을 표시한다. 같은 `activeCard/effectiveCollections` 값을 표시와 검색 요청에서 사용한다. 상단 제공처 안내도 3개 제공처로 갱신했다.
- `frontend/src/components/Results.tsx`, `frontend/src/lib/types.ts`: 기존 응답의 `collections/applied_recommendation`을 표시해 **서버 최종 적용 컬렉션·추천 조건·AOI**를 확인할 수 있게 했다. 홍수 안내의 “S1을 실제 검색합니다”를 “S1 검색 연결됨, 이번 조회는 최종 조건/제공처 상태 확인”으로 고쳐 S2만 조회한 경우에도 SAR를 검색한 것처럼 보이지 않게 했다.
- `frontend/src/components/SceneProvenance.tsx`: SAR의 짧은 관측 시작/종료 기간에 VIIRS용 일별 집계 설명을 붙이지 않는다. 일별 집계 설명은 VNP09GA에만 표시한다.
- 화면에 SAR는 검색·메타데이터·접근 안내만, VIIRS는 `VNP09GA.002` **일별 지표반사도**이며 산불/야간조명 제품이 아님, VIIRS QA/NDVI 미지원, 작은 AOI 검색 성공이 상세 분석 가능성 보장은 아님을 명시했다.
- 신규 `frontend/tests/provider-activation.spec.ts`: 현재 3000→8000 일반 프록시의 실제 검색과 선택 우선순위를 검증한다. 테스트용 AI/가짜 영상으로 실제 검색을 대체하지 않는다. 한 건의 명시적 TEST ONLY 빈 응답은 수동 선택 전환의 UI 회귀 검사에만 사용한다.

백엔드 검색 어댑터·추천 규칙·분석 엔진·실행 스크립트는 수정하지 않았다. 기존 사용자 코드는 위 화면 범위에서 확장했고 `.env`·패키지·지도/분석 구현을 변경하지 않았다.

## 현재 웹사이트의 실제 검색 결과

공통 조건: **UTC 2025-07-20~2025-07-26**, bbox **[126.7,36.4,126.71,36.41]**, 실제 폼 입력과 `좌표 적용`으로 AOI 확정. 카드 선택과 수동 선택을 각각 실행해 보낸 request와 서버 최종 응답을 대조했다. 조회 한도는 기존 UI 기본 50이며 과거 건수와 맞추지 않았다. 아래는 마지막 세 제품 전체 재검증의 실응답이다.

| 목적 / 제품 | 제공처 / 컬렉션 | 카드 / 수동 반환 | UTC 관측일 | AOI 기하 중첩 | 접근/처리 |
|---|---|---:|---|---|---|
| 침수·수역 / Sentinel-1 GRD | copernicus / sentinel-1-grd | 1 / 1 | 2025-07-24 09:31:53.023014~09:32:18.021677 | 100% | CDSE 인증 필요, 직접 다운로드 링크 없음. SAR 전처리·침수 계산 미지원 |
| 식생 / VIIRS VNP09GA.002 | nasa-cmr / viirs-vnp09ga-002 | 7 / 7 | 07-20~07-26 각각 일별 00:00:00~23:59:59 | 전부 100% | Earthdata Login 필요, 직접 링크 없음. 픽셀 QA·NDVI 미지원 |
| 식생 / Sentinel-2 L2A | earth-search / sentinel-2-l2a | 2 / 2 | 07-20 02:27:53.875000, 07-25 02:27:32.626000 | 전부 100% | 공개 HTTP 링크 있음·접근 미검증, 기존 제한된 S2 처리 조건 유지 |

모두 해당 제품 단독 검색은 HTTP 200, outcome=success, collection status=success/complete=true, reason=exhausted, truncated=false였다. 이 의미는 해당 검색 페이지 조회 완료이며 다운로드/픽셀 품질 성공이 아니다. 실제 Asset 접근 권한은 현재 메타데이터의 표시를 확인했으며 이번에 원본 파일을 받거나 로그인하지 않았다. S2 첫 장면에는 공개 직접 링크가 16개 있으나 `access_verified=false`다. 기하 중첩 100%는 맑은/유효 픽셀 비율이 아니고 이 AOI 크기를 VIIRS로 상세 분석할 수 있다는 뜻이 아니다.

실제 Item: S1 `S1A_IW_GRDH_1SDV_20250724T093153_20250724T093218_060224_077BED_9C47_COG`; S2 `S2C_52SBF_20250720_0_L2A`, `S2B_52SBF_20250725_0_L2A`; VIIRS 일별 concept ID는 `G3624111035`, `G3624294587`, `G3624513992`, `G3625652016`, `G3625057132`, `G3626199201`, `G3630603944`에 각각 `-LPCLOUD`가 붙는다.

## 실패도 포함한 실제 테스트 기록

| 명령 / 범위 | 종료 코드 | 실제 결과 |
|---|---:|---|
| root `node.exe scripts/frontend-check.mjs typecheck` | 0 | 최종 문구/테스트 수정 후 독립 검사 통과 |
| root `$env:NEXT_DIST_DIR='.next-conditions'; $env:API_BASE_URL='http://127.0.0.1:8000'; node.exe scripts/frontend-check.mjs build` | 0 | 최종 UI의 compile·TypeScript·production 정적 생성·traces 완료. 실행 중 `.next`와 분리 |
| frontend `$env:E2E_OUTPUT_DIR='test-results-workflow-activation'; npm.cmd run test:e2e -- tests/provider-activation.spec.ts tests/providers.spec.ts tests/sensor-recommendations.spec.ts tests/reliability.spec.ts` | 1 | **28 passed / 1 failed**. 신규 실검색 6개는 모두 성공. 추가 3제공처 동시 검색에서 CMR timeout으로 결과에 NASA가 없어 live 단언 실패. UI는 부분 실패·NASA 0건/미확인과 다른 제공처 결과를 구분해 표시 |
| 같은 4파일, output `test-results-workflow-activation-final` (같은 모드 checkbox 회귀 1건 추가) | 1 | **29 passed / 1 failed**. VIIRS 카드 단독 요청이 10초 제공처 상한으로 HTTP 504/outcome=failed. 같은 조건의 수동 VIIRS는 7건, 그 뒤 3제공처 동시 검색도 성공 |
| frontend `$env:E2E_OUTPUT_DIR='test-results-workflow-activation-check'; npm.cmd run test:e2e -- tests/provider-activation.spec.ts` | 0 | **8 passed (26.8초)**. catalog 1, 명시적 UI fixture 회귀 1, 세 제품×카드/수동 실검색 6. S1 1/1·VIIRS 7/7·S2 2/2. 테스트 자체의 자동 retry 없음; 위 실패 후 명시적으로 다시 실행 |
| frontend `$env:E2E_OUTPUT_DIR='test-results-workflow-activation-final-scope'; npm.cmd run test:e2e -- tests/provider-activation.spec.ts tests/providers.spec.ts --grep 'catalog\|TEST ONLY\|s1_csar\|다중 제공처 · 동일'` | 0 | **6 passed (15.0초)**. 마지막 SAR 시간 설명 수정 후 catalog·같은 모드 수동 전환·S1 카드/수동 실제 검색·데스크톱/모바일 fixture 재검사 |

모든 E2E는 `E2E_BASE_URL`·`E2E_API_BASE_URL`을 제거하여 **실제 3000→8000**에서 실행했다. 외부 API의 간헐 timeout을 테스트 실패로 남겼으며 성공/0건으로 포장하지 않았다. 제공처 시간 상한·재시도·결과를 조작하지 않았다. 전체 pytest·전체 E2E는 이번 UI/재시작 변경 후 재실행하지 않았다. 아래 이전 269 pytest/97 E2E를 이번 실행 버전 검증으로 재사용하지 않는다.

증거: `frontend/test-results/activation-{s1_csar|viirs_sr|s2_msi}-{card|manual}.json`, 후속 실행부터 같은 이름에 timestamp가 붙은 이력 JSON, `activation-viirs_sr-card-timeout-previous.json`, 각 E2E output의 오류 screenshot/context. JSON은 보낸 조건·상태·Item/날짜·중첩·접근 flag만 보존하며 원본/서명 URL을 저장하지 않는다. 현재 API 성공 결과만이 아니라 앞선 실패 결과도 남겼다. `activation-s1_csar.png`, `activation-viirs_sr.png`, `activation-s2_msi.png`는 실제 웹 검색 screenshot이며 직접 열어 상태·최종 조건·접근 제한 표시를 확인했다. fixture 모바일 screenshot은 실제 관측 성공 근거로 사용하지 않는다.

진행 중인 사용자 작업이 없다는 확인을 받은 뒤 서버만 재시작했다. 이번 테스트는 메타데이터 검색이며 품질 검사·NDVI·관측 합성·ML 작업·원본 다운로드를 실행하지 않았다. 백엔드 자동 reload를 추가하지 않았으므로 향후 Python 변경 시에도 해당 프로젝트 서버를 다시 시작해야 한다. 활성 작업 여부가 불명확하면 먼저 확인해야 한다.

이번 코드/테스트 5개(`page.tsx`, `Results.tsx`, `SceneProvenance.tsx`, `types.ts`, `provider-activation.spec.ts`의 위 실제 경로 순) SHA-256 `경로 + NUL + bytes + NUL`: `87fcf17b49c8c237e6116f006e9078f8b24945da2a21f5b9c428e4855b31de77`. 추가 문서 변경: 이 TEST_REPORT, README의 선택 우선순위/재시작 안내, VS_CODE_HANDOFF의 최신 실행 인계.

---

# 다중 제공처 실제 자료 탐색 — 이전 변경 검증 (2026-10-30)

기존 Next.js·MapLibre·FastAPI·Earth Search·단일 목적 추천 규칙·S2 A2–A4/관측 합성/국소 ML을 유지하면서 Copernicus Sentinel-1 GRD와 NASA CMR Suomi NPP VIIRS VNP09GA.002 검색을 연결했다. 새 앱/범용 분석 엔진/별도 추천 규칙을 만들지 않았다. 이번 결과는 아래 과거 pytest/E2E 통과 기록을 재사용하지 않고 최신 수정 후 다시 실행한 근거다.

## 결과와 지원 경계

- 실제 검색 연결: Earth Search `sentinel-2-l2a`, `landsat-c2-l2` (기존), CDSE 현재 STAC `sentinel-1-grd`, NASA CMR `VNP09GA.002` (`C2631841556-LPCLOUD`, 앱 ID `viirs-vnp09ga-002`). 등록된 추천은 MSI·OLI·TIRS·C-SAR·VIIRS 5개 프로필이며 실제 검색 어댑터는 3개 제공처/4개 컬렉션이다.
- 신규 두 제품은 **검색·원본 접근 안내·메타데이터 비교만** 지원한다. S1 GRD는 광학 지수·침수 결과가 아니고 VIIRS 수백 m 일별 제품은 S2 10 m 상세도 대안이 아니다. S2 품질/NDVI/합성/ML 버튼과 서버 ItemReference 제한을 새 제품에 확장하지 않았다.
- 플랫폼·탑재체·제품·제공처·컬렉션/원격 concept·실제 장면·Asset을 구분했다. Scene/지도/선택/비교는 제공처+컬렉션+ID 키를 사용한다. 원래 해상도/출력 격자, 장면 구름/기하 중첩/AOI 실제 QA, 추천/검색/원본 접근/처리 지원을 구별한다.
- `purpose_plan.py`의 기존 RULES·`sensor_catalog.py`의 검토 사양을 확장했다. 홍수는 SAR, 광학은 조건부 보완, 식생의 VIIRS는 광역 참고, 열환경은 실제 L2SP만 선택한다. 자연어 AI는 기존 구조화 경로만 유지하며 새 AI 호출을 넣지 않았다.
- `/catalog` 등록/후보와 `/catalog/discover/{provider}` 공식 컬렉션 재발견은 읽기 전용이다. 새 컬렉션의 존재만으로 사양·적합도·권한을 생성하거나 자동 검색 연결하지 않는다. 공개 컬렉션 발견 실요청: Earth Search 9개/1회/완료, CDSE 75개/3회/미조회 남음, CMR VIIRS 75개/3회/미조회 남음. 발견 응답의 한도·실패를 그대로 표시한다.
- NOAA NODD GOES-18/19 ABI, 기상청 GK2A AMI, NOAA-20/21 VIIRS, HLS·SLSTR는 **미연결 등록 후보**다. 이번에 컬렉션 메타데이터를 확인했더라도 앱 granule 검색 연결/다운로드/처리로 표시하지 않는다. 정지궤도 후보는 추천 규칙에서 제외하며 향후 실제 원반/스캔과 AOI 교차 검사 전 적합 후보로 활성화하지 않는다.

제공처별 인증 표·공식 근거·미연결 후보의 발견 ID/형식/공간 범위·후속 연결 순서·미래 서버 전용 환경변수 이름은 [MULTI_PROVIDER_SEARCH](docs/MULTI_PROVIDER_SEARCH.md)에 기록했다. 현재 메타데이터 검색에 새 키가 필요 없다. 기존 `.env`·OpenAI 설정은 읽거나 변경하지 않았고, 계정 생성·토큰 발급·의존성 설치·배포·push를 하지 않았다.

## 최신 코드 실제 실행

| 위치 | 명령 | 종료 코드 | 결과 |
|---|---|---:|---|
| backend | `$env:PYTHONUTF8='1'; ..\.venv\Scripts\python.exe -m pytest -q --disable-warnings` (`LIVE_STAC` 미설정) | 0 | **269 passed, 16 skipped**, 15.47초. 16개 opt-in 실연결 pytest는 실행하지 않음. fixture/모의 요청만으로 실제 제공처 성공을 주장하지 않음 |
| backend | `$env:PYTHONUTF8='1'; $env:LIVE_STAC='1'; ..\.venv\Scripts\python.exe -m pytest -q -s tests/test_providers_live.py --disable-warnings` | 0 | **4 passed**, 12.76초. 최신 코드의 4개 제품/3개 제공처 실제 검색·canonical Item·접근 HEAD. 아래 한계와 별도 무인증 범위 요청 참조 |
| root | `node.exe scripts/frontend-check.mjs typecheck` | 0 | 최신 코드/테스트 독립 `tsc --noEmit`; build 후에도 재실행하여 0 확인 |
| root | `$env:NEXT_DIST_DIR='.next-conditions'; $env:API_BASE_URL='http://127.0.0.1:8013'; node.exe scripts/frontend-check.mjs build` | 0 | Next.js 16.4.3 webpack compile·TypeScript·production 정적 생성·build traces 완료. 기존 사용 중인 `.next` 대신 분리 출력, 프런트 환경 필터 유지 |
| frontend | `$env:E2E_BASE_URL='http://127.0.0.1:3013'; $env:E2E_OUTPUT_DIR='test-results-workflow-providers-final'; npm.cmd run test:e2e` | 0 | **97 passed (4.2분)**. 최신 백엔드 재시작 후 전체 실행. fixture와 공개 영상 실연결 사례를 포함하며 테스트용 응답은 tests에서만 사용 |

기본 pytest의 1088 warnings에는 기존 pyproj/numpy 및 Starlette TestClient deprecation 등이 포함된다. live pytest는 TestClient 관련 warning 1개다. 경고를 처리 결과 성공이나 실패의 대체 근거로 사용하지 않는다. 전체 opt-in Python의 A3/A4/ML 등 16건을 이번에 모두 실행한 것은 아니며, 별도 위 live 4건과 아래 기존 공개 영상 E2E를 실행했다.

## 실제 제공처 증거와 접근 확인

작은 AOI `[126.7,36.4,126.71,36.41]`, UTC **2025-07-20~2025-07-26**, 추천 프로필별 `max_items=2`로 새 `/search`를 호출했다. 각 표본 canonical Item GET은 200이었다. 기간 밖 장면은 반환하지 않았고 AOI·기간·원래 목적을 유지했다.

| 검색 제품 | 반환/요청 | 실제 표본 | 파일·미리보기 읽기 전용 확인 |
|---|---|---|---|
| Earth Search S2 L2A | 2건 / 1회 | `S2B_52SBF_20250725_0_L2A` | 미리보기 HEAD 200·공개 Asset HEAD 200 |
| Earth Search Landsat L2SP | 1건 / 2회 | `LC09_L2SP_116035_20250723_02_T1` | 미리보기 미제공, 표본은 S3/요청자 비용 원본이므로 공개 HTTP 접근 성공으로 표시하지 않음 |
| CDSE Sentinel-1 GRD COG | 1건 / 1회 | `S1A_IW_GRDH_1SDV_20250724T093153_20250724T093218_060224_077BED_9C47_COG` | 편파 VV/VH·IW·ascending·L1 보존. 미리보기 301→206, 원본 ZIP HEAD 405·무인증 GET Range 401 |
| NASA CMR VNP09GA.002 | 2건 / 1회 | `G3626199201-LPCLOUD` | 일별 종료 시각·실제 granule geometry·HDF5 파일/공개 browse 보존. browse 303→206, 원본 무인증 GET 302→Earthdata Login 401 |

위 206 확인은 HTTP Range 요청이며 대용량 파일 전체를 수신하지 않았다. HEAD/redirect만으로 다운로드를 보장하지 않는다. redirect의 서명 주소/query는 기록하지 않았고 HTTP 코드·호스트·자료 유형만 확인했다. 새 제품 Asset은 인증 필요/접근 미검증, `direct_url=null`로 반환하며 공개 링크 저장 대상에서 제외한다. 공개 원본 링크도 파일 HEAD를 매번 검사한 것으로 표시하지 않는다.

앱 미연결 후보 조사: NOAA GOES-19 ABI L2 LSTF 공개 S3 LIST와 NetCDF 객체 HEAD가 각각 200, GK2A 공식 dataList는 무키 401이었다. NASA CMR에서 VJ109GA/VJ209GA·HLS 컬렉션 200, CDSE 공식 목록에서 실제 SLSTR LST NRT/NTC 컬렉션을 발견했다. 추측한 SLSTR 이름 3개는 404여서 등록하지 않았으며 실제 발견 ID를 문서에만 남겼다. 이 조사는 후보 컬렉션/권한 조사이며 앱 내 신규 검색 연결 증거로 재사용하지 않는다.

공식 인증 근거: [Copernicus STAC](https://documentation.dataspace.copernicus.eu/APIs/STAC.html) / [OData 원본 인증](https://documentation.dataspace.copernicus.eu/APIs/OData.html), [NASA CMR](https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html) / [LP DAAC Earthdata Login](https://lpdaac.usgs.gov/documents/2052/Getting_Started_with_Earthdata_Search.pdf), [NOAA NODD](https://www.noaa.gov/nodd/datasets), [기상청 위성 API](https://apihub.kma.go.kr/apiList.do?seqApi=6).

## 브라우저·경합·기존 기능 회귀

- 신규 `providers.spec.ts`: 1440px/390px의 동일 ID를 가진 다른 제공처 장면 선택·지도 강조·날짜/상세 연결, 부분 실패와 성공 결과 공존, 원본 인증/처리 미지원, 미리보기 없음, 인증 파일 직접 링크/저장 차단, 신규 제품 A2 비활성, 가로 넘침 없음. **실제 공개 API** 별도 사례는 같은 AOI/기간으로 Earth Search·CDSE·CMR를 한 응답/지도에서 확인한다.
- 신규 backend fixture: 목적·공간 규모/변수 구분, 제공처별 실패/시간 초과/0건/상한, 다음 페이지·중복, 기간 밖 제외, 전역 한도 아래 미반환 범위, CMR lat/lon 정규화·polygon, 인증/서명 URL 비노출, 처리 가드·지명/목적 문맥, 컬렉션 발견의 읽기 전용/상한을 검사한다. CMR 공개 `sort_key`는 자격증명으로 오인 차단하지 않도록 페이지 링크 회귀 단언을 추가했다.
- 전체 E2E는 기존 밴드 선택/복원·링크 `.txt` 내용·페이지 이동·센서/전후 비교·지도 레이어·자연어 카메라/AOI 분리·빠른 목적/AOI/기간/선택 변경 중 늦은 응답 폐기를 재검사했다. 기존 **공개 실제 영상 A2·A3 SCL/밴드 범위 읽기·A4 NDVI ZIP·관측 합성 ZIP·국소 ridge ML ZIP 및 지도 레이어**도 최신 서버에서 재실행하여 통과했다. 국소 ML은 OpenAI가 아닌 기존 픽셀 추정 엔진이다.
- `frontend/test-results/providers-1440.png`, `providers-390.png`를 저장하고 직접 열어 확인했다. 화면 수치는 TEST ONLY fixture이며 과학적/실관측 검증으로 사용하지 않는다. 기존 imagery layout 회귀의 16px checkbox·날짜/레이어 상태·접근성 검사도 함께 통과했다.
- 실제 OpenAI 유료 호출 **0회**: 검증 백엔드의 AI_NL_ENABLED=0, `/request/config` usage.requests=0을 읽기 전용 확인했다. AI 오류/취소 테스트는 모의 응답이며 실제 모델 성공 증거가 아니다.

중간 검증: 첫 pytest 11 failed/242 passed, 두 번째 6 failed/263 passed였다. 신규 연결로 바뀐 옛 “S1 미지원”/그룹 기대값, 테스트 작성 중 UTF-8 전달과 중복 fixture ID를 수정했고 최종 269/16으로 재실행했다. 첫 live pytest 3 passed/1 failed는 Landsat 표본에 공개 HTTP Asset이 없는데 테스트가 이를 가정한 문제였다. 제한을 우회하지 않고 S3/요청자 비용 경로를 미검증으로 기록하도록 고쳤고 최종 4건 통과했다. 첫 집중 E2E 8 passed/2 failed는 nested summary 선택자 중복이었으며 직접 자식 summary로 수정했다. 이후 전체 97건 1차 통과, 최종 backend 필드/CMR 페이지 URL 검토 후 다시 최신 서버에서 **97건 전부** 통과했다.

## 변경 파일 (실제 저장소 상대 경로)

새 백엔드 등록/어댑터/보안 경계:

```text
backend/app/provider_registry.py
backend/app/provider_search.py
backend/app/copernicus.py
backend/app/cmr.py
backend/app/catalog_discovery.py
backend/app/safe_urls.py
```

기존 백엔드의 확장·단일 규칙 재사용:

```text
backend/app/stac.py
backend/app/sensor_catalog.py
backend/app/purpose_plan.py
backend/app/recommendations.py
backend/app/metadata.py
backend/app/assets.py
backend/app/models.py
backend/app/main.py
backend/app/evaluation.py
backend/app/request_interpretation.py
```

프런트 표시/기존 상태 재사용·타입/실행 제한:

```text
frontend/src/app/page.tsx
frontend/src/app/globals.css
frontend/src/components/SceneProvenance.tsx (신규)
frontend/src/components/SensorRecommendations.tsx
frontend/src/components/Results.tsx
frontend/src/components/ImageryExplorer.tsx
frontend/src/components/AssetDownloads.tsx
frontend/src/components/NaturalWorkflow.tsx
frontend/src/components/AnalysisConditions.tsx
frontend/src/components/SceneComparison.tsx
frontend/src/lib/types.ts
frontend/src/lib/selection.ts
frontend/src/lib/workflow.ts
frontend/src/lib/externalAccess.ts
```

테스트:

```text
backend/tests/test_providers.py (신규)
backend/tests/test_providers_live.py (신규)
backend/tests/test_core.py
backend/tests/test_purpose_plan.py
backend/tests/test_sensor_recommendations.py
frontend/tests/providers.spec.ts (신규)
frontend/tests/sensor-recommendations.spec.ts
frontend/tests/external-access.spec.ts
frontend/tests/next-work.spec.ts
frontend/tests/search.spec.ts
frontend/tests/analysis-conditions.spec.ts
frontend/tests/change-analysis.spec.ts
frontend/tests/pixel-quality.spec.ts
```

문서: `README.md`, `docs/VS_CODE_HANDOFF.md`, 신규 `docs/MULTI_PROVIDER_SEARCH.md`, `TEST_REPORT.md`. 기존 `MapPanel.tsx`·분석/래스터 엔진·패키지 설정·환경 로더·실제 `.env`는 변경하지 않았다. 검증용 일회성 launcher/스크린샷·파일 목록은 기존 ignored `frontend/test-results/` 아래에 두었다. Git 저장소가 없어 diff로 기존 편집을 대조할 수는 없으며 요청 범위 파일을 직접 보존·확장했다. 코드/테스트 43파일을 `frontend/test-results/provider-changed-files.txt` 순서로 `경로 + NUL + bytes + NUL` 연결한 SHA-256: `6bf75f2d5fb4d69aa8239e0ac07e710c8e06b2bc7bc659b88c6a579ff658a2cc`.

## 실행 상태와 남은 검증

기존 사용자 서버 3000(PID 34344)/8000(PID 31584)는 유지했다. 검증은 별도 3013/8013에서 수행했고 E2E 종료 후 제가 띄운 두 서버만 종료했다. 종료 전 양쪽 health 200, 기존 사용자 양쪽 health도 200이었다. production build는 검증 dev 서버를 종료한 뒤 별도 `.next-conditions`에 생성했다. **현재 기존 8000 프로세스는 이전 코드를 메모리에 유지**하므로 새 검색을 사용하려면 사용 중인 프로젝트 실행 창에서 작업 종료 여부를 확인하고 프로젝트를 재시작해야 한다. 다른 앱/서버를 종료하지 않았다.

미실행/한계: CDSE/Earthdata 인증 원본 전체 다운로드·대용량 파일 무결성·계정별 권한/토큰 수명·SAR/VIIRS 픽셀 처리, 미연결 후보 granule/다운로드·GEO AOI 가시성 구현, 전체 opt-in Python 16건, 실제 OpenAI 응답/비용 검증, production 서버 브라우저 테스트는 이번 완료 범위가 아니다. 페이지/시간/결과 상한 너머 자료는 미조회이며 0건/부재로 확정하지 않는다. 실제 링크는 이후 제공처 변경/인증/네트워크 상태에 따라 실패할 수 있고 fixture로 대체하지 않는다. 키·토큰·서명 URL을 출력/문서/링크 목록/manifest에 저장하지 않았다.

---

# 외부 자료 접근 안내 — 이전 변경 검증 (2026-10-30)

이번 변경은 S3/요청자 비용 Asset의 기존 제한을 유지하면서, 같은 Item·밴드에 HTTP(S) 직접 링크가 있을 때 다른 형식을 안내하고, Sentinel-1 미연결 추천 카드와 제한된 Sentinel-2/Landsat Asset에 공식 포털 이동 경로를 추가한다. 포털은 검색 조건을 자동 전달하지 않으며 인증·비용 동의·다운로드를 대행하지 않는다. 테스트 fixture는 tests 전용이다.

| 명령 | 종료 코드 | 결과 |
|---|---:|---|
| `node scripts/frontend-check.mjs typecheck` | 0 | 최종 코드·테스트·임시 빌드 경로 정리 후 독립 TypeScript 검사 통과 |
| `node scripts/frontend-check.mjs build` | 1 | 기존 `.next`의 `_global-error.segments` mkdir EPERM. 코드 compile/TypeScript 단계까지 통과했지만 빌드 완료로 기록하지 않음 |
| `$env:NEXT_DIST_DIR='.next-access-check'; node scripts/frontend-check.mjs build` | 0 | 최종 코드에서 분리된 출력 폴더로 Next.js production 정적 생성까지 통과. 임시 폴더는 검증 후 제거 |
| `$env:E2E_BASE_URL='http://127.0.0.1:3012'; npm.cmd run test:e2e -- tests/external-access.spec.ts` | 0 | 최종 코드에서 새 UI 2건 통과. 별도 로컬 3012/8012 서버 사용 후 중지; 앞선 환경 격리 실패와 테스트 선택자 1건 실패를 수정한 뒤 재실행 |
| `$env:E2E_BASE_URL='http://127.0.0.1:3012'; npm.cmd run test:e2e -- tests/sensor-recommendations.spec.ts tests/reliability.spec.ts` | 0 | 기존 추천·밴드 선택·링크 목록·부분 실패·모바일 회귀 19건 통과 |

외부 포털 링크의 대상은 [Copernicus Browser 공식 설명](https://documentation.dataspace.copernicus.eu/Applications/Browser.html)과 [USGS Landsat Data Access](https://www.usgs.gov/landsat-missions/landsat-data-access)로 확인했다. 링크 클릭 후 포털의 실제 검색 결과·계정 접근·원본 다운로드 성공은 검사하지 않았다. 현재 코드에서 백엔드 변경은 없으며 pytest는 이번 변경 후 실행하지 않았다.

## 이전 변경 기록

# 날짜별 실제 영상 — 가독성·레이어 정렬 검증 (2026-10-30)

이번 변경은 기존 `ImageryExplorer`의 표현·레이아웃에 한정한다. Next.js·MapLibre·검색·분석 엔진·루트 선택/날짜/레이어 상태와 콜백을 재사용했다. 새 화면·API·서버 설정·의존성·배포·push는 없다. 아래 이전 설정/전체 E2E 기록은 이번 UI 변경의 검증으로 재사용하지 않는다.

## 실제 브라우저에서 확인한 원인

Edge/Playwright에서 테스트용 검색 fixture를 렌더링하고 CSS 계산값과 실제 스크린샷을 비교했다. fixture는 tests에만 있으며 서비스 오류 시 대체 자료로 쓰지 않는다.

- 전역 `input,select,textarea { width:100% }`가 `.imagery-layers label { display:flex; align-items:baseline }`의 checkbox에도 적용됐다. 해당 영역에 폭 제한이 없어 flex-shrink=1로 줄어든 뒤에도 입력 요소가 매우 넓었다. 1440px 뷰포트/936px 행에서 checkbox 폭 **825px·803.94px**, 390px 뷰포트/298px 행에서 **208.47px·195.48px**를 계측했다. native 체크 표시는 그 큰 입력 요소 안에 놓이고 텍스트는 남은 오른쪽 좁은 영역으로 밀렸다.
- 선택 정보의 2열 grid 안에서 각 `dl div`는 전역 `display:flex; justify-content:space-between`, `dd`는 `text-align:right`를 그대로 받았다. 예: 데스크톱 첫 항목의 dt x=430 / dd x=836.63, 모바일 x=48 / x=286.63이었다.
- 레이어의 이름·상태·설명이 하나의 익명 flex 텍스트 항목이었고, 비활성 행 전체 opacity 및 긴 공통 문구가 가독성을 낮췄다.

## 수정 내용

- 전역 input/dl 규칙을 변경하지 않았다. `.imagery-layers input[type=checkbox]`에 **16×16px, flex-shrink:0**, 각 행에 왼쪽 시작 정렬을 적용했다. 입력 옆에 이름→짧은 상태→설명을 담는 축소/줄바꿈 가능한 텍스트 영역을 배치했다.
- 상태를 `표시 중`, `사용 가능`, `미실행/자료 없음`, `미제공`으로 구별한다. disabled 동작과 실제 준비 상태를 유지한다. 원본 URL이 없는 미리보기는 미제공/비활성으로 표시하며 저장된 상위 미리보기 선택값은 바꾸지 않아 URL 있는 장면으로 돌아가면 이전 선택을 유지한다.
- 선택 영상 첫 묶음은 위성·UTC 촬영 시각·제품이다. 해상도/제공처/기하 중첩/장면 구름/실제 AOI 픽셀 품질은 값과 짧은 설명이 가까운 카드로 묶었다. null은 미확인, 실제 0은 0으로 유지한다. AOI 기하 중첩과 픽셀 품질, 장면 구름량과 AOI 구름량을 구별한다.
- 원본 Item ID·컬렉션·탑재체·추천 근거·필수 밴드는 삭제하지 않고 기본 접힌 native details로 옮겼다. 긴 ID 줄바꿈도 검사했다. 긴 레이어 의미/출처/ML 한계는 별도 접힌 details에서 확인한다.
- fieldset/legend/label을 유지하고 `useId` 기반 aria-labelledby/aria-describedby로 checkbox 이름과 상태·설명을 연결했다. 날짜/목록/지도 강조와 픽셀·ML 레이어의 출처 구분은 기존 상태에서 받는다. ML 컨트롤은 기존처럼 관련 작업의 지도 결과가 있을 때만 나타난다.

## 최신 코드의 실제 실행

| 위치 | 명령 | 종료 코드 | 결과 |
|---|---|---:|---|
| root | `node.exe scripts/frontend-check.mjs typecheck` | 0 | 최신 UI·테스트의 독립 `tsc --noEmit` 통과 |
| root | `$env:NEXT_DIST_DIR='.next-conditions'; $env:API_BASE_URL='http://127.0.0.1:8000'; node.exe scripts/frontend-check.mjs build` | 0 | Next.js 16.4.3 webpack production compile·TypeScript·정적 생성 통과. 기존 dev `.next` 보존, 서버 환경값은 프런트 체크에서 정제 |
| frontend | `$env:E2E_OUTPUT_DIR='test-results-workflow-imagery-final'; Remove-Item Env:E2E_API_BASE_URL -ErrorAction SilentlyContinue; npm.cmd run test:e2e -- tests/imagery-layout.spec.ts tests/imagery-explorer.spec.ts tests/pixel-quality.spec.ts tests/change-analysis.spec.ts tests/estimate-mode.spec.ts tests/search.spec.ts tests/reliability.spec.ts` | 0 | **43 passed (2.6분)**. 현재 실행 중인 개발 앱의 일반 3000→8000 프록시 사용 |

`imagery-layout.spec.ts` 신규 5건은 1440/390px 실측·스크린샷, checkbox/name 첫 줄 간격/높이, 16px/축소0, 메타데이터 값의 왼쪽 정렬, 폼 입력 폭 보존, 긴 ID 접기/펼치기, 미제공/접근 실패, 원본 미리보기 토글·날짜 변경 후 상태 복귀, QA/처리 결과의 실제 UI/API 연결과 지도 토글을 검사한다.

기존 38건도 함께 재실행했다. 날짜/목록/지도 선택, 기간 밖/날짜/구름 누락, 비교·밴드/원본 링크 파일 저장, 빠른 조건 변경 중 오래된 응답 폐기, 실제 공개 STAC 검색·A3 QA·A4 NDVI ZIP·기존 국소 ML ZIP/지도 레이어를 포함한다. 여기서 ML은 기존 로컬 픽셀 추정 엔진이며 OpenAI 자연어 호출이 아니다. 이번 OpenAI 요청 집계를 읽기 전용으로 확인한 결과 **0회**였다. 키·환경 파일은 읽거나 수정하지 않았다.

## 스크린샷·계측 결과

| 자료 | 위치 | 확인 |
|---|---|---|
| 변경 전 데스크톱·모바일 | `frontend/test-results/imagery-before-1440.png`, `imagery-before-390.png` | checkbox/문구 벌어짐과 메타데이터 양끝 정렬 재현 |
| 변경 후 데스크톱·모바일 | `frontend/test-results/imagery-layout-1440.png`, `imagery-layout-390.png` | 신규 회귀 테스트가 저장. checkbox와 이름이 같은 첫 줄, 문구 자연 줄바꿈, 전체 문서 가로 넘침 없음 |
| 변경 후 미실행 상태 별도 계측 | `frontend/test-results/imagery-after-1440.png`, `imagery-after-390.png` | 두 폭 모두 checkbox 16px/flex-shrink=0, dt/dd 시작 x 동일 확인 |
| QA/처리 자료가 있는 상태 | `frontend/test-results/imagery-layout-available.png` | TEST ONLY overlay로 활성·비활성·표시 상태와 지도 연결 확인 |

이미지를 직접 열어 데스크톱/모바일과 결과가 준비된 상태를 시각 확인했다. 스크린샷/1px overlay와 UI 수치는 명시적인 TEST ONLY fixture이며 과학적 품질 검증 증거가 아니다. 실제 공개 데이터 회귀는 위 기존 별도 E2E에서 검사했다. 임시 계측 스크립트는 `frontend/test-results/inspect-imagery-layout.mjs`, `inspect-imagery-after.mjs`이며 애플리케이션에서 import하지 않는다.

중간 집중 실행은 **9 passed / 1 failed (31.0초), 종료 1**이었다. 미리보기 상태 테스트의 has locator가 바깥 region 경로까지 포함해 행을 찾지 못했다. checkbox의 실제 상위 label로 선택자를 수정했고 최종 43건에서 해당 단언을 포함해 통과했다. 초기 임시 브라우저 계측 스크립트는 작업 폴더/상대 경로 오류로 진입 전 중단된 경우가 있었으며 경로 수정 후 계측은 종료 0이었다.

## 변경 파일과 검증 경계

- `frontend/src/components/ImageryExplorer.tsx`: 선택 정보/접힌 근거/접근성 있는 레이어 행.
- `frontend/src/app/globals.css`: 기존 imagery 영역에 한정한 정렬·고정 checkbox 크기·상태/카드 스타일.
- 신규 `frontend/tests/imagery-layout.spec.ts`: 위 5개 UI 회귀 사례.
- `TEST_REPORT.md`: 이번 실제 검증 기록을 기존 이력 앞에 추가.

`MapPanel.tsx`, 루트 page 상태, API/타입, 추천·검색·분석 엔진은 수정하지 않았다. 이번에는 전체 E2E·backend pytest·별도 production 서버 브라우저 검사를 실행하지 않았다. 확인한 범위의 정렬/상태 연결 문제는 해소됐으며 외부 원본 미리보기 URL은 제공처 접근 상태에 따라 실패할 수 있다. 실패 시 기존 오류 안내를 표시하고 가짜 이미지/값으로 대체하지 않는다. 서버 재시작·배포·push는 하지 않았다.

Git 저장소가 없어 검증한 3개 코드/테스트 파일을 위 순서(`ImageryExplorer.tsx`, `globals.css`, `imagery-layout.spec.ts`)로 `경로 + NUL + bytes + NUL` 연결한 SHA-256을 기록한다: `47822b91bcade059d02eb41c99892715357bcafbdba5a6613e19d4a7c3331c5c`.

---

# OpenAI 서버 설정·환경 격리 — 2026-10-30

범위: 기존 자격증명 재사용을 위한 로더/설정, 사용자 승인 후 적용·프로젝트 재시작과 모의 테스트. 기존 추천·검색·지도·분석 기능과 Responses 호출 경로를 재사용했다. 새 의존성 설치·배포·push·실제 OpenAI 호출은 하지 않았다. 아래 과거 전체 E2E 기록을 이번 변경의 재실행 결과로 재사용하지 않는다.

## 확인과 적용 상태

- 확인 당시 키 저장 위치는 `backend/.env.example`이었고 `backend/.env`는 없었다. 승인 후 기존 파일 자체를 `backend/.env`로 이름 변경하고 비밀 없는 예시를 생성했다. 존재 여부만으로 이후 확인했고 기존 사용자 모델은 비어 있었다. 첫 파일 읽기에서 키가 도구 출력에 포함되는 실수가 있었으며 사용자에게 알렸다. 해당 값은 재인용하지 않으며 보고서·문서·테스트에 넣지 않는다.
- 적용한 일반 설정: `AI_NL_ENABLED=1`, `AI_NL_PROVIDER=openai`, `AI_NL_MODEL=gpt-5.6-luna`. 사용자가 이미 지정한 모델/다른 파일 변수는 보존한다. 프로세스 값이 있으면 파일보다 우선한다.
- **사용자 승인 후 실제 적용 완료**. 사용자가 “설정 적용·프로젝트 재시작 승인”으로 기존 키의 지속 사용·파일 이름 변경·일반 설정 적용·이 프로젝트 재시작을 승인했다. `node.exe scripts/configure-server-env.mjs --apply-approved`는 종료 0이었고 키 존재 여부만 반환했다. 파일 이름 변경 뒤 일반 설정을 갱신했으며 키를 예시/다른 파일/프런트에 복사하지 않았다.
- 승인 근거는 이번 사용자 요청 6번과 위 명시 응답이다. 실제 유료 호출은 승인 범위에서 제외했고 수행하지 않았다. 승인 플래그 없는 설정 도구는 파일을 읽거나 변경하기 전에 중단한다.

## 선택 모델과 호출 경계

[GPT-5.6 Luna 공식 모델 문서](https://developers.openai.com/api/docs/models/gpt-5.6-luna)를 2026-10-30 열어 Responses/Structured Outputs/`reasoning.effort=none` 지원, 비용 지향 소형 모델 설명과 100만 토큰당 입력 $0.20 / 출력 $1.20을 확인했다. 기존 GPT-5 nano 문서는 deprecated, GPT-4.1 nano는 shut down으로 표시되어 기본 설정으로 선정하지 않았다. 선택 모델은 짧은 목적·날짜·지명 추출에 맞춰 추론을 끄고 기존 strict schema·1000 출력 토큰·12초 상한을 유지한다. 다른 사용자 모델의 요청 설정은 바꾸지 않는다.

계정의 모델 접근 가능 여부·키의 제공처 인증 성공·실제 모델 응답은 **미검증**이다. 이번 작업의 실제 OpenAI 요청은 **0회**다. `ready=true`는 값/형식의 설정 인식 성공이며 모델 응답 성공이 아니다. 모델 목록 조회도 하지 않았다.

향후 유료 검증 최소안은 선택된 모델로 `영천군의 2025년 8월 식생상태 확인` 한 문장 **1회**, 기존 strict schema/도구 없음/`store:false`/1000 출력 토큰/12초 조건에서 목적·날짜·지명 필드를 확인하는 것이다. 영상 검색·픽셀 처리·자동 재시도 없이 별도 승인 후에만 시행한다. 이번 설정 적용 승인에는 유료 검증이 포함되지 않는다.

## 로딩 위치·우선순위·키 격리

- `scripts/server-env.mjs`는 프로젝트 루트 기준 **`backend/.env` 한 파일만** 읽는다. 루트/프런트 `.env`나 `.env.example`을 추측해서 병합하지 않는다.
- 허용 목록: `AI_NL_ENABLED`, `AI_NL_PROVIDER`, `AI_NL_MODEL`, `OPENAI_API_KEY`, 선택 단가 2개. 파일의 다른 값은 보존하되 새 백엔드 프로세스 환경에 무조건 주입하지 않는다.
- **프로세스 환경에 키가 존재하면(빈 문자열 포함) > 서버 파일 > 기존 기본 동작** 순서다. 환경변수 치환/셸/코드를 실행하지 않는다.
- 백엔드는 서버 설정을 받고 Next.js·지도 worker 준비 프로세스는 `OPENAI_*`, `AI_NL_*`, `NEXT_PUBLIC_OPENAI_*`, `NEXT_PUBLIC_AI_NL_*`를 제거한 별도 환경을 받는다. `scripts/frontend-check.mjs`의 독립 typecheck/build도 정제된 환경이며 서버 파일을 읽지 않는다.
- `.gitignore`의 `.env*`와 명시 `/backend/.env`로 서버 파일을 제외한다. `.env.example`은 공유 예외여서 실제 비밀을 둘 수 없다. 현재 `.git` 저장소가 없어 인덱스/과거 추적 이력을 검증했다고 설명하지 않으며 Git에 추가/커밋하지 않았다. 가짜 파일만 둔 임시 Git 저장소에서 현재 ignore 규칙으로 `backend/.env` 제외/비밀 없는 예시 허용을 실제 검사했고 종료 0이었다.
- 승인받은 설정 도구는 키가 든 기존 파일 자체를 `.env`로 이름 변경한다. 키 값을 별도 파일/프런트/예시에 복사하지 않고 일반 변수만 갱신한다. 안전한 예시는 키 값이 비어 있다. 충돌 파일이 있으면 덮어쓰지 않고 중단한다.

## 실제 테스트 명령·종료 코드

| 위치 | 명령 | 종료 코드 | 결과 |
|---|---|---:|---|
| root | `node.exe --test scripts/server-env.test.mjs` | 0 | **12 passed**, 0 failed. 가짜 키/임시 폴더만 사용. 단일 경로·프로세스 우선·빈 값·허용 목록·따옴표/BOM/주석·보간 미실행·환경 격리·실제 자식 프로세스의 키 존재 여부·승인 가드·파일 이름 변경·사용자 모델 보존·일반 설정 갱신·Git 제외 규칙 검사 |
| backend | `$env:PYTHONUTF8='1'; Remove-Item Env:LIVE_STAC -ErrorAction SilentlyContinue; ..\.venv\Scripts\python.exe -m pytest -q --disable-warnings` | 0 | **253 passed / 12 skipped**, 15.04초, 1088 warnings. 실제 OpenAI 없음, opt-in STAC 12건 미실행 |
| root | `node.exe scripts/frontend-check.mjs typecheck` | 0 | 정제된 환경의 독립 `tsc --noEmit` 통과 |
| root | `$env:NEXT_DIST_DIR='.next-conditions'; $env:API_BASE_URL='http://127.0.0.1:8000'; node.exe scripts/frontend-check.mjs build` | 0 | 정제된 환경의 Next.js 16.4.3 production compile·TypeScript·정적 생성 통과. 기존 dev `.next` 보존 |

추가 backend 테스트는 누락 설정 이름만 반환, 상태 조회에서 호출/키 반환 없음, 선정 모델의 추론 none을 모의 응답으로 검사했다. 기존 schema·오류·취소 테스트도 재실행했다. 이번에는 전체 브라우저 E2E·실제 OpenAI·실시간 위성 처리 테스트를 실행하지 않았다. 로딩/설정 범위만 변경했으며 라이브 모델 응답 성공으로 보고하지 않는다.

초기 문서 갱신 명령 1회는 셸의 Unicode 전달 설정 때문에 대상 제목을 찾지 못해 Python ValueError로 문서 변경 전에 중단됐다. 출력 인코딩을 명시하고 문서를 갱신했다. 비밀 파일을 문서 갱신 과정에서 출력하지 않았다.

## health·작업 확인

승인 전 현재 실행 중인 앱은 프런트 `/` 200, `/api/health` 200, 백엔드 `/health` 200이었다. `/api/request/config`는 기존 실행 코드에서 ready=false/provider=null/model=null이었으며 새 `missing_settings`는 아직 제공하지 않았다. AI 실행 상태는 running이 아니었고 실제 래스터 worker 프로세스 0개를 확인했다. 기존 API에 전체 메모리 작업 목록 조회가 없어 모든 대기 작업 부재를 검증한 것으로 설명하지 않는다. 다른 앱/서버는 종료하지 않았다.

승인 직후 다시 확인한 관측 가능한 AI 실행/래스터 worker는 없었다. 프로젝트 경로·backend worker(39420)·부모(29700)·런처(41152)와 frontend 부모(42460)의 관계를 검증한 뒤 해당 backend worker만 종료했다. 기존 런처가 자기 자식들을 종료한 후 3000/8000 포트가 닫힌 것을 확인하고 같은 `scripts/start-local.mjs`로 재시작했다. 다른 앱/서버를 종료하지 않았다. 새 backend worker는 31584다. 이는 승인된 로컬 재시작이며 배포가 아니다.

적용 후 Python/httpx의 읽기 전용 GET 확인은 종료 0이었다.

| 검사 | 결과 |
|---|---|
| `http://127.0.0.1:3000` | HTTP 200 |
| `/api/health` | HTTP 200 |
| `http://127.0.0.1:8000/health` | HTTP 200 |
| `http://127.0.0.1:8000/request/config` | HTTP 200, ready=true, provider=openai, model=gpt-5.6-luna, missing_settings=[] |
| `http://127.0.0.1:3000/api/request/config` | 동일한 준비 상태, 실제 OpenAI 요청 집계 0 |
| 서버/예시 파일 키 존재 여부 | `backend/.env`: 있음 / `backend/.env.example`: 없음. 값은 출력하지 않음 |

**설정 인식 성공 / 실제 계정 접근·모델 응답 성공 미검증**이다. 실제 API 호출·모델 목록 조회·키 재발급은 하지 않았다. 실제 모델 검증은 위 최소안으로 별도 승인 후에만 진행한다.

## 변경 파일

- 신규 `scripts/server-env.mjs`, `scripts/configure-server-env.mjs`, `scripts/frontend-check.mjs`, `scripts/server-env.test.mjs`
- `scripts/start-local.mjs`
- `backend/app/ai_interpretation.py`, `backend/tests/test_ai_interpretation.py`
- `.gitignore`, `docs/AI_NATURAL_INPUT.md`, `README.md`, `TEST_REPORT.md`
- 승인 후 적용: 기존 파일을 `backend/.env`로 이름 변경(비공개·Git 제외), 안전한 `backend/.env.example` 재생성, `docs/VS_CODE_HANDOFF.md`에 결과 기록

---

# 자연어 해석·카메라/AOI 분리 — 최신 검증 보고서

기준: 2026-10-29 (Asia/Seoul). 최신 사용자 요청에 따라 기존 Next.js·MapLibre·React/TypeScript·FastAPI와 자연어 조건 훅, 추천·STAC·비교·밴드/다운로드·A3/A4·관측 합성·ML 추정 엔진을 재사용했다. 새 앱·분석 엔진·의존성 설치·배포·push는 없다. 아래 75 E2E/230 pytest와 그 이후 문구 수정은 과거 기록이며 이번 전체 코드 검증으로 재사용하지 않는다.

## 구현 결과와 계약

- `영천군의 2025년 8월 식생상태 확인`의 기간은 UTC 2025-08-01~31로 반영되고, 지도 카메라만 영천시 참고 위치로 이동한다. 좌표는 빈 상태이며 AOI/사각형을 생성하지 않는다. 영천군은 1995년 통합된 옛 지명임을 표시한다. 옛 군 경계의 복원/현재 법정경계와 동등한 데이터라고 설명하지 않는다.
- 카메라 상태(`CameraLocation`)와 분석 폼 bbox/확정 상태를 분리했다. 지도 두 꼭짓점 → `분석 AOI 확정`, 또는 좌표 → `좌표 적용`이 필요하다. 수동 좌표 변경은 재확정이 필요하다. 지명과 기존 AOI가 다를 수 있으면 좌표를 보존하고 유지/새 선택을 요청한다. 카메라만 이동할 때 검색 조건/결과를 변경하지 않는다. 지도는 추천 카드·검색 버튼보다 먼저 배치했다.
- 무료 자동 해석은 800 ms debounce/blur·IME·중복 방지·수동 날짜 보호를 유지한다. 지명 후보 선택은 화면 이동만 제안한다. 새 문장·취소·늦은 응답은 기존 버전/AbortController와 수동 수정/지도 이동 revision으로 보호한다. 영역 선택을 시작하면 카메라 이동 애니메이션을 멈추며 선택 중 자동 화면 이동을 적용하지 않는다.
- 기존 interpret 요청에 `interpretation_mode: rules | ai`(기본 rules), 제안에 `engine/extraction`, 지명에 `role=camera_only/view_bbox`를 추가했다. 옛 `region.bbox`는 적용하지 않고 서버 재시작을 안내한다. `GET /request/config`는 비밀값 없는 준비/제공처·모델/사용량·상한이다. 기존 검색/픽셀 API의 명시 bbox·기간 계약은 유지한다.
- OpenAI는 목적(enum), 명시 날짜와 원문 근거, 지명 문자열/모호성, single/change/unspecified, 불확실성만 추출한다. strict schema/extra 필드 금지, 원문 근거·달력·월말/윤년·366일·허용 목적/의도를 서버에서 검증한다. 좌표·사양·영상 존재·픽셀 품질을 생성하지 않으며 자연어 코드/셸/도구를 실행하지 않는다. 추천은 기존 카탈로그/규칙이다. 상대 날짜/모호한 사건 날짜는 확인을 요청하고 사건일을 생성하지 않는다.

## OpenAI 설정·실연결 여부

워크스페이스 `.env*`의 **변수 이름/존재 여부만** 확인했고, 현재 프로세스의 AI 관련 환경변수 이름도 확인했다. AI 제공처·모델·키 설정은 없었다. 키 값이나 무관한 개인 자격증명을 조회/출력하지 않았다. 이후 사용자가 OpenAI API라고 답변해 제공처를 확정했다.

- 구현 제공처: **OpenAI Responses API**, 공식 고정 HTTPS 원점, `store:false`, strict Structured Outputs. 기존 `httpx` 사용, 새 SDK 설치 없음.
- **실제 선택/호출한 모델: 없음**. `AI_NL_MODEL` 기본값을 추측하지 않았다. 사용자 서버에서 지원 모델 ID를 직접 지정해야 한다.
- **실제 OpenAI API 검증: 미실행**. 키·모델 미설정으로 이번 작업의 실제 OpenAI 호출은 0회다. 테스트용 AI 응답을 실제 이해/정확도/청구량 검증으로 설명하지 않는다.
- 설정: `AI_NL_ENABLED=1`, `AI_NL_PROVIDER=openai`, `AI_NL_MODEL`, 서버 전용 `OPENAI_API_KEY`. 선택 단가 변수는 `AI_NL_INPUT_USD_PER_MILLION`, `AI_NL_OUTPUT_USD_PER_MILLION`. 값은 출력하거나 저장하지 않았다. `backend/.env.example`은 빈 변수/설정 안내이며 자동 로드하지 않는다. [보안 입력·실행 방법](docs/AI_NATURAL_INPUT.md)을 따른다.
- 명시 AI 버튼만 제공처를 호출한다. 입력/blur·기존 선택 후 후속 요청은 AI를 호출하지 않는다. 최대 2000자·1000 출력 토큰·응답 64 KiB, 제공처 전체 12초/브라우저 15초, 자동 재시도 없음. 프로세스당 100회·분당 6회·동시 1개, 모델/문장 10분 서버 RAM 캐시 128건과 브라우저 10분 캐시 16건이다.
- 누락·잘못된 schema/원문 근거·타임아웃·연결 실패·취소·상한은 실패/미확인으로 표시하고 수동값을 보존한다. AI 오류를 규칙 성공으로 위장하지 않는다. 요청 중/실패/취소/로컬 캐시 상태를 구분한다. 사용량 새로고침은 집계 조회만 수행한다. 토큰/실패/캐시/미확인 청구 호출과 선택 단가 기준 비용 또는 미확인을 표시한다. 재시작 시 집계가 초기화되며 다중 서버/영속 청구 원장이 아니다. 취소가 이미 발생한 제공처 요금의 취소를 보장하지 않는다.

공식 구현 근거는 [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses), [Responses 형식과 저장 선택](https://developers.openai.com/api/docs/guides/migrate-to-responses?api-mode=responses)을 실제 열어 확인했다. API 계정의 모델 가용성과 의미 해석 정확도는 키 설정 후 별도 확인해야 한다.

## 지명 데이터 출처·이용 조건

전국/해외 실시간 지오코더는 연결하지 않았다. 로컬 출처 등록 목록은 **충남·상주시·영천시와 별칭**이다. 광주/중구 중복 후보 중 좌표 미등록 항목과 그 밖의 지명은 수동 지도를 안내한다. AI 추출 범위와 검증된 좌표 자료의 범위는 별개다.

- [영천시청 위치와기후](https://www.yc.go.kr/portal/contents.do?mId=0402010000)의 극서 128°41′41″, 극남 35°50′03″, 극동 129°08′42″, 극북 36°10′54″를 직접 HTTP 200 원문으로 확인했다(2026-10-29). 화면 참고 `[128.694722,35.834166,129.145,36.181667]`. AOI나 경계 폴리곤이 아니다.
- [영천시청 연혁](https://www.yc.go.kr/portal/contents.do?mId=0403040000)에서 1995-01-01 영천시·영천군 통합을 확인했다.
- [영천시청 저작권 정책](https://www.yc.go.kr/portal/contents.do?mId=0704000000)을 확인했다. 공공누리 표시 자료의 조건과 미표시 자료의 사전 협의 안내를 보존했다. 극점 페이지의 공공누리 표시를 확인하지 못했으므로 공공누리 데이터셋으로 표시하지 않는다. 앱에는 위치 수치 사실만 전사하며 설명문·지도 이미지·표 디자인을 복제하지 않는다.
- 충남 2015 도정백서·상주 시청 극점은 기존 출처/연도를 보존해 **카메라 참고**로 재사용한다. 상세 URL/범위/한계는 `backend/app/data/regions.json`과 [설명](docs/AI_NATURAL_INPUT.md)에 기록했다. 최신 행정경계·옛 영천군 경계의 정합을 검증하지 않았다.

## 마지막 앱 수정 후 실제 실행

| 위치 | 실제 명령 | 종료 코드 | 결과 |
|---|---|---:|---|
| backend | `$env:PYTHONUTF8='1'; Remove-Item Env:LIVE_STAC -ErrorAction SilentlyContinue; ..\.venv\Scripts\python.exe -m pytest -q --disable-warnings` | 0 | **250 passed / 12 skipped**, 18.19초, 1088 warnings. backend opt-in live 12건은 미실행 |
| frontend | `npm.cmd run typecheck` | 0 | 독립 TypeScript 검사. 마지막 MapPanel 수정 후 루트의 `npm.cmd --prefix frontend run typecheck`로도 재실행, 종료 0 |
| frontend | `$env:NEXT_DIST_DIR='.next-conditions'; $env:API_BASE_URL='http://127.0.0.1:8011'; npm.cmd run build` | 0 | Next.js 16.4.3 webpack production compile·TypeScript·정적 생성 통과. dev `.next` 보존 |
| frontend | `$env:E2E_API_BASE_URL='http://127.0.0.1:8011'; $env:E2E_OUTPUT_DIR='test-results-nl-camera-final4'; npm.cmd run test:e2e` | 0 | **87 passed (4.1분)**. 최종 앱 수정 이후 전체 파일 재실행 |

새 AI pytest 19건은 TEST ONLY transport로 schema/원문/기간 오류·timeout·refusal·미설정·rate/busy·cache·취소/사용량·민감값 비노출을 검사한다. 기존 달력/지명 pytest의 구 AOI 기대를 카메라 전용 계약으로 갱신하고 영천군 1건을 추가했다. 브라우저 `automatic-conditions.spec.ts` 15건은 실제 규칙 API와 명시 fixture 오류를 사용하며 달력/지명·카메라 실제 중심·사각형 없음·확정 전 차단·수동값/새 응답 경합·지도 그리기·모바일 순서를 검사한다. 새 `ai-camera.spec.ts` 7건은 TEST ONLY AI 응답으로 명시 호출·캐시·토큰/비용 표시·오류/취소/수동 수정·새 문장 보호를 검사한다.

## 실데이터와 미검증 경계

- E2E의 공개 영상 사례는 실제 STAC/추천, 수동 AOI 확정, A2 원본 Item/Asset HEAD, A3 SCL·필수 밴드 범위 읽기, A4 NDVI ZIP, 관측 합성 계획→확인→실행→ZIP, 실험적 ML 검증→확인→ZIP·관측/추정 지도 레이어를 재검사한다. 이는 OpenAI 자연어 API 실연결 검증이 아니다.
- 전체 E2E는 개발 프런트엔드와 최신 FastAPI 8011에 대한 기존 테스트 전용 실제 HTTP 전달을 사용한다. 개별 tests fixture는 TEST ONLY로 구별한다. 실제 합성/ML 다운로드는 앱의 작업 경로를 검증한 뒤 동일 작업의 8011 직접 링크로 브라우저 저장하는 기존 helper를 유지한다. production 프록시 전체 다운로드 경로를 이 환경에서 검증했다고 표현하지 않는다.
- 별도 production 서버 브라우저 검사, QGIS 앱 직접 열기, backend 전체 opt-in live 12건, 실제 OpenAI 의미 정확도/모델 가용성/청구량, 전국/해외 지오코딩, 구름 아래 목표일 참값은 미검증이다. 기존 25 km²/픽셀·전송/시간 상한과 SAR/HLS 미연결을 유지한다.
- `frontend/test-results/automatic-camera-mobile.png`를 직접 열어 제안·미확정 AOI·출처·명시 AI 버튼·비용 상태의 모바일 배치를 확인했다. Map의 실제 카메라 중심과 AOI 없음은 브라우저에서 별도로 단언했다.

## 수정 중 실패·재검증 기록

- 초기 pytest는 구 AOI 라벨 기대 1건이 실패(41 passed / 1 failed, 종료 1)했다. 새 카메라 전용 계약으로 단언을 변경했다. 이후 AI/조건 집중은 51 passed였다.
- 초기 집중 E2E는 **19 passed / 2 failed**, 종료 1이었다. 취소 테스트의 지연 fixture가 테스트 종료 뒤 route.fetch를 호출했고, 오류 선택자가 Next 빈 route-announcer를 가리켰다. 지연 전 실제 규칙 응답 준비/예상 취소 처리와 앱 오류의 정확한 선택자로 수정했다. 새 지도 확정 테스트를 포함한 집중은 **22 passed (41.2초)**, 종료 0이었다.
- 중간 전체 `test-results-nl-camera-final2`는 **85 passed / 2 failed (4.1분)**, 종료 1이었다. 기존 AOI 경합 테스트가 새 좌표 확정을 빠뜨린 경우와 지도 이동 애니메이션 중 두 꼭짓점 선택이 겹치는 경우였다. 테스트의 명시 좌표 적용과 실제 MapPanel의 이동 정지/그리기 보호로 수정했다. 이후 검색/경합/자동조건 집중 **32 passed (1.1분)**, 종료 0이었다.
- `test-results-nl-camera-final` 및 `final3` 시도는 요청 중 상태 표시·지도 순서·그리기 보호 보완을 위해 중단(종료 1)했으며 전체 통과로 세지 않는다. 위 `final4`가 최종 코드 판정이다.
- 최초 루트 `npm.cmd run typecheck`는 package.json 위치 오류(ENOENT, 종료 1)로 검사를 실행하지 못했다. frontend 디렉터리/명시 prefix로 수정해 위 독립 검사와 build를 실행했다. 기존 deprecation 경고를 의존성 교체로 숨기지 않았다.

## 실제 변경 파일

| 범위 | 경로 |
|---|---|
| 서버 AI 추출/설정/검증 | 신규 `backend/app/ai_interpretation.py`, `backend/app/main.py`, `backend/app/models.py`, `backend/app/request_interpretation.py`, 신규 `backend/.env.example` |
| 카메라용 지명 제안/출처 | `backend/app/condition_proposals.py`, `backend/app/data/regions.json` |
| 폼·지도·AI 상태/타입 | `frontend/src/lib/useConditionInput.ts`, `frontend/src/lib/types.ts`, `frontend/src/components/AutomaticConditions.tsx`, `frontend/src/components/MapPanel.tsx`, `frontend/src/app/page.tsx`, `frontend/src/app/globals.css` |
| backend 테스트 | 신규 `backend/tests/test_ai_interpretation.py`, `backend/tests/test_condition_proposals.py` |
| E2E | 신규 `frontend/tests/ai-camera.spec.ts`, `frontend/tests/automatic-conditions.spec.ts`, `frontend/tests/runtime.ts`, `frontend/tests/reliability.spec.ts` |
| 문서·산출물 제외 | 신규 `docs/AI_NATURAL_INPUT.md`, `docs/AUTOMATIC_CONDITIONS.md`, `docs/VS_CODE_HANDOFF.md`, `README.md`, `AGENTS.md`, `TEST_REPORT.md`, `.gitignore` |

기존 NaturalWorkflow/EstimatedImage/QA/분석 엔진·카탈로그를 교체하지 않았다. 기존 후속 사용자 문구 개선과 수동 입력을 보존했고, 영천군을 미등록으로 보던 테스트는 새 검증 자료/카메라 계약으로 갱신했다. Git 저장소가 없어 앱/핵심 설정 50개(`backend/app` Python/JSON, `frontend/src` TS/TSX/CSS, next.config.ts, playwright.config.ts)를 경로순 `경로 + NUL + bytes + NUL`로 연결한 SHA-256: `a3b9ae933bca44f29c9b456599cad36e2dd924bb0b9c091c0cae670a2195cd02`.

최종 전체 검증 뒤 실행 중인 프로젝트의 backend worker·부모·런처 명령/경로를 확인하고, 이 프로젝트 로컬 런처만 재시작했다. 일반 3000→8000 프록시에서 `.3`, 2025-08-01~31, `yeongcheon/camera_only`, `region.bbox` 없음과 OpenAI 준비 false/모델 null/실제 호출 0회를 확인했다. 일반 프록시 브라우저 예시도 `Remove-Item Env:E2E_API_BASE_URL -ErrorAction SilentlyContinue; $env:E2E_OUTPUT_DIR='test-results-nl-camera-normal-proxy'; npm.cmd run test:e2e -- tests/automatic-conditions.spec.ts -g '영천군 2025년 8월'`로 **1 passed (3.7초), 종료 0**이었다. 이어 `npm.cmd run typecheck`도 종료 0이었다.

현재 로컬 앱은 http://127.0.0.1:3000 에서 최신 코드로 실행 중이다. 검증용 8011만 종료했다. 기존 브라우저는 새로고침하면 된다. OpenAI 실사용에는 사용자가 서버 실행 환경에서 키·모델을 준비하고 재시작해야 하며 키 값을 대화/코드/브라우저에 입력하지 않는다.

---

# 선택 영상에 따른 다음 작업 흐름 — 최신 검증 보고서

## 2026-10-29 자연어 조건 형식 오류 후속 확인

사용자가 `영천군의 2025년 8월 식생상태 확인할거야` 입력에서 본 `조건 해석 응답 형식이 올바르지 않습니다`의 원인은 **실행 중인 3000/8000 서버의 이전 백엔드**였다. 로컬 `/api/request/interpret` 응답은 `workflow-intent-2026-10-29.1`로 `condition_proposals`가 없었고, 파일의 현재 구현은 `.2`다. 기존 로컬 런처를 중지하고 `node scripts/start-local.mjs`로 다시 시작한 뒤 같은 요청은 `.2`와 `condition_proposals.status=partial`을 반환했다. 기간은 `2025-08-01`~`2025-08-31`로 해석했고, **영천군은 현재 등록된 지명 범위 밖**이라 AOI는 임의로 만들지 않았다.

`frontend/src/lib/useConditionInput.ts`에서 이전 서버 응답을 받으면 버전 불일치와 재시작을 안내하도록 오류 문구를 수정했다. `frontend/tests/automatic-conditions.spec.ts`에 위 문장의 부분 성공 및 이전 서버 응답 두 사례를 추가했다. 수정 후 `npm run test:e2e -- tests/automatic-conditions.spec.ts -g "영천군 입력|이전 백엔드 응답"`는 **2 passed, 종료 0**, `npm run typecheck`는 **종료 0**이었다. 이 후속 확인에서는 전체 pytest/build/E2E를 재실행하지 않았다. 아래 75건 전체 E2E 등은 **이 문구·테스트 추가 전**의 실행 이력이다. 3000/8000 로컬 앱은 최신 코드로 다시 실행 중이다.

기준: 2026-10-29 (Asia/Seoul). 기존 Satellite Insight AI 폴더에서 화면 흐름과 제한된 후속 의도 연결만 개선했다. Next.js·React/TypeScript·MapLibre·FastAPI, 자연어 날짜/AOI 자동입력, 검색·추천·비교·밴드 선택·원본 링크·A3/A4·관측 합성·ML 엔진을 재사용했다. 새 앱/엔진·유료 API·키 설정·의존성 설치·Supabase·배포·push는 없다. 아래 보고서는 과거 기록이며 이번 성공 근거로 재사용하지 않는다.

## 구현과 상태 흐름

1. 목적·확정 AOI·UTC 기간 → 근거 있는 추천 → 제품 선택 → 추천 아래 하나의 검색 버튼. 제품 선택은 검색하지 않는다. 기존 자동/직접 컬렉션 검색도 유지한다.
2. 검색 결과의 선택 장면 → `다음 작업`. 미선택이면 선택 안내만, 한 장면이면 원본/지원되는 단일 QA, 여러 장면이면 비교를 열 수 있다. 비교 쌍은 page.tsx의 기존 루트 상태로 관리한다. 비교를 열면 단일 QA 버튼을 감춰 같은 작업 버튼을 여러 곳에 놓지 않는다.
3. 장면 구름량은 메타데이터로만 표시한다. 사용자 구름 요청 또는 실제 AOI 검사 저하 때 품질 해결을 표시한다. 검사 실패는 미확인으로 전파하고 오래된 품질/분석 레이어를 지운다.
4. 같은 허용 기간의 검색된 대체 관측 확인 → 사용자 확인 체크 → 기존 원본 픽셀 기반 관측 합성 계획. 실제 계획에서 잔여 결측이 확인되고 지원 조건이면 접힌 선택형 실험적 ML을 표시한다. 합성 실행을 먼저 완료할 의무는 없지만 원본 픽셀 검사 근거가 필요하다. ML 자체의 학습/검증·확인·실행 게이트는 유지한다.
5. `다른 작업 요청`은 장면 선택 이후 접힌 영역에 있다. 검색/비교/확정 AOI 이동/구름 안내만 기존 상태/API로 실행한다. 미지원 요청은 실행하지 않으며 목적을 조용히 바꾸지 않는다.
6. 목적·AOI·기간·선택·비교 쌍 변경은 계획·확인·작업 상태·지도 레이어를 폐기한다. 진행 작업을 취소하며, 늦은 작업 시작 응답의 작업도 취소한다. 후보/확인 변경도 이전 계획을 폐기하지만 동일 자연어 해석 때문에 작업 버튼이 사라지지 않게 했다.

| 목적 | 다음 작업의 실제 지원 범위 |
|---|---|
| 식생 | 원본/밴드·메타데이터 비교, 지원되는 S2 L2A QA, 같은 플랫폼 두 날짜 A4 NDVI. 한 시점의 제한된 S2 조건에서만 관측 합성·실험적 ML |
| 홍수/수역 | 광학 원본/밴드·비교와 지원되는 S2 쌍 QA. SAR 검색 미연결, 침수 면적/원인 확정·합성·ML 미지원 |
| 열환경 | Landsat L2SP 원본/다운로드·메타데이터 비교. 앱 내 온도 계산·픽셀 QA·합성·ML 미지원. Sentinel-2를 열적외선 지표온도 대안으로 제시하지 않음 |
| 도시 | 원본/밴드·비교와 지원되는 S2 쌍 QA. 도시 변화 계산·합성·ML 미지원 |

## 마지막 앱 코드 수정 후 실제 실행

| 위치 | 명령 | 종료 코드 | 실제 결과 |
|---|---|---:|---|
| backend | `Remove-Item Env:LIVE_STAC -ErrorAction SilentlyContinue; ..\.venv\Scripts\python.exe -m pytest -q --disable-warnings` | 0 | **230 passed / 12 skipped**, 15.37초, 1088 warnings. 전체 backend opt-in live 12건은 미실행 |
| frontend | `npm.cmd run typecheck` | 0 | production build와 별개로 `tsc --noEmit` 실행, 통과 |
| frontend | `$env:NEXT_DIST_DIR='.next-conditions'; $env:API_BASE_URL='http://127.0.0.1:8011'; npm.cmd run build` | 0 | Next.js 16.4.3 webpack production compile·TypeScript·정적 생성 통과 |
| frontend | `$env:E2E_API_BASE_URL='http://127.0.0.1:8011'; $env:E2E_OUTPUT_DIR='test-results-workflow-final2'; npm.cmd run test:e2e` | 0 | **75 passed (3.9분)**. 신규 12건과 기존 63건 모두 이번 최종 코드로 재실행 |

기존 날짜/AOI 자동입력 10건을 포함한 전체 E2E를 재실행했다. 신규 `next-work.spec.ts` 12건은 미선택/한 장면/여러 장면, 메타데이터 구름량과 실제 QA 구분, 양호/저하/HTTP 실패, 원본 작업의 선택 장면 상세 열기, 목적·제품별 제한, 결측 0/양수의 ML 노출, 미지원 후속 의도, 늦은 작업 시작 취소, 모바일 순서/중복 QA/가로 넘침을 검사한다. 신규 pytest 2건은 미지원 의도의 원래 목적 보존과 검색 의도의 현재 조건 재사용을 검사한다. 집중 parser/자동조건 pytest는 별도 **42 passed**, 종료 0이었다.

## Fixture와 공개 영상 검증 경계

- 신규 상태별 12건과 기존 오류/취소/경합 테스트는 **tests 안의 TEST ONLY fixture**다. API 장애를 서비스 코드에서 fixture로 대체하지 않는다.
- 전체 E2E의 별도 실제 사례는 실제 추천/STAC, A2 canonical Item·공개 Asset HEAD, A3 SCL/필수 밴드 범위 읽기, A4 NDVI ZIP, 관측 합성 계획→명시 확인→실행→실제 ZIP 저장, 관측 합성 계획의 잔여 결측 확인→ML 검증→확인→실제 추정 ZIP 저장·관측/추정 지도 레이어 구분을 검사한다. 실제 합성/ML 사례는 `S2B_52SBF_20210716_0_L2A`, `S2B_52SBF_20210726_0_L2A`, AOI `[126.70,36.40,126.71,36.41]`를 사용한다.
- 이번 실제 브라우저 저장 파일 `frontend/test-results/cloud-live.zip`(33,047바이트), `estimate-live.zip`(61,608바이트)을 루트 `.venv` Python의 `zipfile`/JSON/`rasterio.io.MemoryFile`로 추가 읽기 검사했다(종료 0). 두 ZIP CRC 정상, manifest JSON 파싱, 합성 TIFF 4개와 ML TIFF 6개 모두 46×56·CRS 존재를 확인했다. 합성은 밴드/유효마스크/출처 인덱스/날짜, ML은 원관측/추정 전용/혼합/픽셀 상태/참조 인덱스/날짜를 별도 보존한다. 이는 로컬 파일 헤더 재열기이며 QGIS 수동 검증은 아니다.
- 기존 사용자의 3000/8000 서버를 종료하지 않았다. 테스트는 기존 개발 프런트엔드와 최신 코드의 별도 FastAPI 8011을 사용한다. `runtime.ts`의 로컬 전달은 실제 HTTP이며 각 테스트의 명시 fixture와 구별한다. 기존 다운로드 helper는 앱 경로를 검사한 뒤 같은 실제 작업의 8011 직접 링크로 브라우저 저장한다. 앱의 기본 프록시를 거친 production 브라우저 다운로드를 검증한 것으로 설명하지 않는다.
- build 산출물은 dev `.next`를 보존하는 `.next-conditions`다. 별도 production 서버에서의 E2E, QGIS 앱 직접 열기, 백엔드 전체 opt-in live 12건, 여러 지역/계절의 과학적 정확도 및 구름 아래 목표일 참값은 미검증이다. ML의 맑은 보류 픽셀 검증을 구름 아래 정확도로 일반화하지 않는다.
- 래스터 25 km²/100,000셀/64 MiB/60초/동시 1작업, 합성 최대 4장면·31일과 ML 참조일 14일 등 기존 제한을 유지한다. 검색 한도 밖 후보는 조사하지 않는다. SAR/HLS/GIBS·범용 분석·Supabase 영속 작업 관리는 추가하지 않았다.

## 수정 중 발견한 실패와 처리

- 초기 전체 73건 실행의 실패 7건을 확인했다. 기존 추천 카드 테스트가 제품 선택만으로 검색한다고 가정했고, 일부 비교 테스트가 새 접힌 비교를 열지 않았다. 새 명시 UI 단계로 테스트를 수정했다. 빈 검색 fixture에 추천 메타데이터가 없을 때 발생한 렌더링 오류는 optional 처리로 수정했다. 실제 합성 테스트에는 대체 관측 검토 전 실행 차단과 검토 후 활성화 단언을 유지했다.
- 지연 작업 시작 응답을 새 선택 후 취소하지 못하던 실제 경합을 cleanup 버전 증가로 수정했다. 실제 단일 QA 저하 안내가 후보 확인 후 사라지던 문제도 보존 상태로 수정했다.
- 중간 집중 34건은 **31 passed / 3 failed**, 종료 1이었다. 수정 전 테스트 모듈을 이미 읽은 실행에서 남은 카드 단계 3건이 실패했다. 수정 파일을 새로 읽은 센서 5건 재실행은 **5 passed (14.9초)**, 종료 0이었다. 앞선 새 흐름/합성/ML 집중 17건 재실행도 **17 passed (34.6초)**였다.
- `test-results-workflow-final` 전체 시도는 후보 확인 변경 시 해석 상태가 작업 버튼을 일시 제거하는 문제를 확인해 25건 통과 후 중단(종료 1)했다. 문장/핵심 조건 변경의 해석 초기화와 후보/확인 변경의 계획 폐기를 분리했다. 완료된 전체 실행으로 세지 않으며 위 `final2`가 최종 판정이다.
- 경고는 기존 FastAPI TestClient/httpx·Rasterio/NumPy deprecation 및 Node 색상 환경 경고 등을 포함한다. 새 의존성 설치로 숨기지 않았다.

## 실제 변경 파일

| 범위 | 실제 경로 |
|---|---|
| 루트 상태·순서·모바일 UI | `frontend/src/app/page.tsx`, `frontend/src/app/globals.css` |
| 다음 작업·합성/ML 진입·문맥 보호 | `frontend/src/components/NaturalWorkflow.tsx`, `frontend/src/components/EstimatedImage.tsx`, 신규 `frontend/src/lib/workflow.ts`, `frontend/src/lib/types.ts` |
| 추천·비교·결과·지도 레이어 UI | `frontend/src/components/SensorRecommendations.tsx`, `frontend/src/components/SceneComparison.tsx`, `frontend/src/components/ImageryExplorer.tsx`, `frontend/src/components/Results.tsx` |
| 실제 QA/분석 버튼 지원 범위·요청 실패 전파 | `frontend/src/components/PixelQuality.tsx`, `frontend/src/components/ChangeAnalysis.tsx` |
| 제한된 기존 자연어 의도 확장 | `backend/app/request_interpretation.py`, `backend/tests/test_request_interpretation.py` |
| 새 상태별 E2E·공통 조작 | 신규 `frontend/tests/next-work.spec.ts`, `frontend/tests/runtime.ts` |
| 기존 회귀 E2E의 새 화면 진입·단언 | `frontend/tests/analysis-conditions.spec.ts`, `automatic-conditions.spec.ts`, `change-analysis.spec.ts`, `cloud-workflow.spec.ts`, `estimate-mode.spec.ts`, `imagery-explorer.spec.ts`, `pixel-quality.spec.ts`, `reliability.spec.ts`, `search.spec.ts`, `sensor-recommendations.spec.ts` (이 행의 나머지도 모두 `frontend/tests/` 아래) |
| 문서·검증 산출물 제외 | `README.md`, `AGENTS.md`, `docs/VS_CODE_HANDOFF.md`, `TEST_REPORT.md`, `.gitignore` |

분석 엔진 `cloud_composite.py`, `cloud_estimate.py`, `pixel_raster.py`, `change_analysis.py`와 밴드/추천 공통 규칙은 다시 구현하지 않았다. 기존 날짜/AOI 제안·단일 폼 훅과 테스트 전용 로컬 전송/독립 build 설정도 재사용했다. 생성된 스크린샷/ZIP은 `frontend/test-results/`에 있으며 테스트 산출물이다. `next-work-mobile.png`를 직접 열어 다음 작업·비교·QA·접힌 후속 요청의 모바일 배치도 확인했다.

Git 저장소가 없어 앱 소스/핵심 설정 49개를 경로순 `경로 + NUL + 파일 bytes + NUL`로 연결한 SHA-256을 남긴다: `f1980ad9f00081e143f733670121499cf049e01408e1c0d4d7852b4b5e147a69`. 대상은 `backend/app` Python/JSON, `frontend/src` TS/TSX/CSS, `frontend/next.config.ts`, `frontend/playwright.config.ts`다. 이 스냅샷은 마지막 앱 수정 후 검사한 코드다.

검증용 8011 프로세스만 종료하고 포트가 닫힌 것을 확인했다. 사용자의 3000/8000 서버는 그대로 유지했다. 기존 8000 서버는 이전 코드가 메모리에 있으므로 기존 실행 창을 종료하고 루트 `start.cmd`로 다시 시작해야 새 해석 응답을 사용한다. 계정/비밀키/추가 설치는 필요 없다.

---

# 자연어 날짜·관심지역 자동입력 — 최신 검증 보고서

기준: 2026-10-29 (Asia/Seoul). 기존 프로젝트 `C:\Users\aicam\Documents\ChatGPT\바이브코딩`에서 요청한 날짜·관심지역 자동입력만 구현했다. 아래 ML·지도·A4 보고서는 과거 실행 이력으로 보존한다. 이번 수치는 실제 새 실행 결과이며 과거 195/53 또는 173/39를 재사용하지 않았다. 기존 FastAPI·React/TypeScript·Next.js·MapLibre와 검색/QA/합성/추정 엔진을 재사용했다. 새 유료 API·인증키·의존성 설치·계정·Supabase·배포·push는 없다.

## 결과와 검증 경계

- 예시 `2026년 7월 충남의 집중호우 전후 침수범위를 분석하고 싶어.`는 2026-07-01~31, 충청남도 포함 사각 영역 `[125.539166,35.975,127.641945,37.062223]`으로 자동 반영된다. 도청 2015 도정백서 원문 PDF 47쪽(인쇄 9쪽)을 내려받아 렌더링하고 극점표를 직접 대조했다. 자료 연도와 최신 법정경계가 아니라는 한계는 UI/자료 파일/방법 문서에 보존한다.
- 기존 `/request/interpret`에 선택형 `resolve_conditions`를 추가했다. 날짜·지명 제안만 반환하며 STAC 검색이나 래스터 작업을 호출하지 않는다. 명시 UTC 달력 날짜·월말·윤년, 미언급 유지, 모호 지명·미지원 하위 지역·자료 실패·검색 상한 처리, 사건 날짜 미생성을 검사했다.
- 550 ms debounce/blur, 한글 조합 보호, 동일 자동 요청 합치기/성공 캐시, 문장 버전/AbortController, 수동 필드 보호와 명시 재적용, 단일 폼에서 파생한 지도 bbox/검색 요청, 오래된 결과 표시를 구현했다. 처리 상한을 넘는 충남 전체를 임의로 축소하지 않는다.
- 신규 브라우저 10건은 America/Los_Angeles 시간대에서도 날짜가 바뀌지 않는지 확인한다. API 지연 중 수동 수정과 빠른 새 문장, IME, 중복 요청, 검색/처리 자동 호출 없음, 지도/좌표/요청 일치를 포함한다. 신규 실제 STAC 테스트 1건은 응답 `source=live-stac`와 예시 기간/bbox를 확인한다. 검색 결과 개수가 반드시 양수라고 가정하지 않는다.

## 마지막 앱 코드 변경 후 실제 실행

| 위치 | 명령 | 종료 코드 | 실제 결과 |
|---|---|---:|---|
| backend | `Remove-Item Env:LIVE_STAC -ErrorAction SilentlyContinue; ..\.venv\Scripts\python.exe -m pytest -q --disable-warnings` | 0 | **228 passed / 12 skipped**, 23.47초. 1088 경고는 표시만 생략. 백엔드 전체 opt-in live 12건은 미실행 |
| frontend | `npm.cmd run typecheck` | 0 | 독립 TypeScript 검사 통과. 최종 테스트 런타임/다운로드 보완도 검사 |
| frontend | `$env:NEXT_DIST_DIR='.next-conditions'; $env:API_BASE_URL='http://127.0.0.1:8011'; npm.cmd run build` | 0 | Next.js 16.4.3 production build·TypeScript·정적 생성 통과. 기존 dev `.next`와 별도 산출물 |
| frontend | `$env:E2E_API_BASE_URL='http://127.0.0.1:8011'; $env:E2E_OUTPUT_DIR='test-results-conditions'; npm.cmd run test:e2e` | 0 | **63 passed (3.8분)**. 신규 10건과 기존 53건을 모두 실제 재실행 |

신규 `test_condition_proposals.py`는 매개변수 포함 33건이다. 기존 자연어 7건과 함께 최종 집중 실행은 **40 passed**였다. 이 검사는 실제 공개 자료에서 고정한 지명 목록·달력 로직/API 검사이며 실시간 지오코딩 테스트가 아니다. 자료 실패/상한은 tests 전용 조작으로 별도 검사한다. Fixture를 서비스 실패 시 대체 자료로 사용하지 않는다.

전체 E2E에는 실제 STAC 검색/추천·A2 원본 HEAD·A3/A4 범위 읽기·NDVI ZIP·관측 합성 ZIP·ML 추정 ZIP과 fixture UI/오류/모바일/경합 검사가 함께 있다. 백엔드 LIVE_STAC 미설정이 이 브라우저 실연결을 차단하지 않는다. QGIS 앱 직접 열기, 전체 백엔드 live suite 12건, 별도 production 서버에서의 브라우저 검사는 이번에 수행하지 않았다.

## 검증 환경·실패 이력

기존 3000/8000 서버를 임의 종료하지 않았다. 별도 테스트 프런트엔드 실행 명령은 자동 실행 정책에 차단되어, 실행 중인 개발 프런트엔드와 최신 코드의 검증용 FastAPI 8011을 사용했다. 테스트 런타임은 실제 HTTP 요청을 이 로컬 백엔드로 전달한다. 앱의 기본 `/api` 프록시/다운로드 코드는 변경하지 않았다. 검증용 8011 프로세스만 최종 확인 후 종료한다. 기존 8000 프로세스가 옛 코드를 메모리에 유지하면 사용자가 기존 실행 창을 종료하고 `start.cmd`로 다시 시작해야 신규 응답을 읽는다.

- 새 자동입력 E2E 첫 실행은 **8 passed / 2 failed**였다. 지연 테스트의 `route.fetch()`가 최신 8011이 아닌 기존 8000으로 향해 신규 응답 필드가 없었다. 테스트의 실제 HTTP 전달을 바로잡은 재실행은 **10 passed**였다. UI의 수동 보호 단언을 약화하지 않았다.
- 전체 E2E 첫 실행은 **61 passed / 2 failed**였다. 실제 합성·추정 완료 후 `download.saveAs: canceled`였다. 전달용 fulfill/URL 교체/redirect를 통한 첨부 탐색도 취소되었다. 같은 실제 작업 ZIP을 백엔드 직접 링크로 저장하면 성공함을 별도 브라우저로 확인했다.
- 테스트에서만 앱의 `/api/(cloud|estimate)/jobs/{id}/download` 경로 형식을 검증하고 동일 작업의 실제 백엔드 링크로 기준 서버를 바꾸었다. 2개 실제 다운로드 단독 재실행은 **2 passed**, 이후 최종 전체는 **63 passed**였다. 파일 저장·바이트 검사와 앱의 작업 경로 검사 모두 유지한다. 정상 앱 프록시를 거친 production 브라우저 다운로드를 이번 환경에서 재검증한 것으로 설명하지 않는다.
- 경고는 기존 FastAPI TestClient/httpx와 Rasterio/NumPy deprecation이 주를 이룬다. 새 의존성을 설치해서 경고를 숨기지 않았다.

## 실제 변경 파일

| 범위 | 경로 |
|---|---|
| 백엔드 | `backend/app/models.py`, `backend/app/request_interpretation.py`, 신규 `backend/app/condition_proposals.py`, 신규 `backend/app/data/regions.json` |
| 단일 조건 상태·UI | 신규 `frontend/src/lib/useConditionInput.ts`, 신규 `frontend/src/components/AutomaticConditions.tsx`, `frontend/src/app/page.tsx`, `frontend/src/lib/types.ts`, `frontend/src/app/globals.css` |
| 기존 화면 연결 | `frontend/src/components/NaturalWorkflow.tsx`(조합 중 문맥 요청 보류), `frontend/src/components/MapPanel.tsx`(검증 가능한 AOI 속성) |
| 테스트 | 신규 `backend/tests/test_condition_proposals.py`, 신규 `frontend/tests/automatic-conditions.spec.ts`, 신규 `frontend/tests/runtime.ts`; 기존 `analysis-conditions.spec.ts`, `change-analysis.spec.ts`, `cloud-workflow.spec.ts`, `estimate-mode.spec.ts`, `imagery-explorer.spec.ts`, `pixel-quality.spec.ts`, `reliability.spec.ts`, `search.spec.ts`, `sensor-recommendations.spec.ts`의 공통 런타임 import 연결. 실제 ZIP 2개는 위 테스트 전용 전송 helper 사용 |
| 검증 설정 | `frontend/next.config.ts`, `frontend/playwright.config.ts`, `.gitignore`; Next build가 `frontend/tsconfig.json`의 별도 산출물 타입 include와 `frontend/next-env.d.ts`의 생성 타입 경로도 갱신. 기존 compiler 옵션 유지 |
| 문서 | `README.md`, `AGENTS.md`, `docs/VS_CODE_HANDOFF.md`, 신규 `docs/AUTOMATIC_CONDITIONS.md`, `TEST_REPORT.md` |

새 계정/키/패키지 설정은 필요 없다. 상세 형식·범위·출처·옵션은 [자동입력 안내](docs/AUTOMATIC_CONDITIONS.md)를 따른다. 현재 지역 자동입력 목록은 충남/충청남도와 등록된 상주시 별칭이다. 광주·중구 후보 중 좌표 미등록 지역과 그 밖의 지역은 직접 지정한다. 전국/해외 범용 지오코딩 또는 최신 법정경계 정합을 검증했다고 표현하지 않는다.

앱 소스 및 핵심 설정 48개(backend/app의 Python·자료 JSON, frontend/src의 TS/TSX/CSS, next.config.ts, playwright.config.ts)를 경로순으로 `경로 + NUL + 파일 bytes + NUL` 연결한 SHA-256: `9749fe6d03969b273652fe355a57d88fcba8ff7773e92f7608958083b575687a`. Git 저장소가 없어 이 스냅샷과 이번 명령/종료코드를 실행 근거로 남긴다.

---

# Satellite Insight AI — 선택형 ML 추정영상 현재 검증 기록

기준일: 2026-10-29 (Asia/Seoul). 기존 지도 탐색·관측 픽셀 선택 합성과 별도로, **가려진 목표일 픽셀을 모델로 추정하는 선택형 모드**를 추가했다. 이 모드의 결과를 실측 영상, 구름 제거 완료, 구름 아래 참값의 복원으로 표현하지 않는다. 상세 방법·운영 게이트·출력은 [추정영상 방법 문서](docs/ESTIMATED_IMAGE_METHOD.md)에 기록했다. 아래 지도 탐색 보고와 A4 기록은 이전 단계의 실행 이력이며 이번 ML 기능의 검증 근거로 재사용하지 않는다.

## 현재 구현·제한

- `backend/app/cloud_estimate.py`가 같은 플랫폼·기준선 Sentinel-2 L2A 목표일/참조일의 적색·근적외선·녹색 실제 범위 읽기와 SCL/NoData를 재사용한다. AOI 내 맑은 짝픽셀로 표준화된 국소 다중 출력 ridge(`α=1`)를 학습하고 2×2 공간 사분면 4-fold 보류 검증을 한다. 세 밴드 평균 MAE가 단순 참조일 복사보다 최소 5% 개선되어야 하며 밴드별/NDVI 기준도 통과해야 한다. 최소 학습 쌍 400, 사분면 보류 40, fold 학습 200, 참조일 최대 14일 차이 등은 **운영 게이트**다.
- 학습에 필요한 맑은 짝픽셀 부족, 기준선 개선 실패, 다른 목적/제품/기간, 범위 밖 예측값, 원본 검증 오류는 차단하거나 결측을 유지한다. 계획 확인 후 실행할 때 원본 Item·ETag와 모델/검증/면적 지문을 다시 확인한다. 기존 작업 상태/취소를 재사용한다.
- `target_observed.tif`, `estimated_only.tif`, `estimate_with_observed.tif`, `pixel_status.tif`(0 결측·1 실측·2 추정), `donor_index.tif`, `donor_date.tif`, `manifest.json`을 ZIP으로 생성하고 GeoTIFF를 재열기 검사한다. 지도 실측/추정 거짓색 미리보기는 별도 레이어다. 파일/manifest에 목표·참조 날짜, 모델 계수·검증 지표, 픽셀 출처를 보존하며 인증/서명 URL을 기록하지 않는다.
- 이 검증은 **맑은 목표일 보류 픽셀**에서 이루어진다. 두꺼운 구름 아래 목표일의 정답은 관측하지 못했으므로 화면의 MAE/RMSE/90백분위로 구름 아래 정확도를 보장할 수 없다. 토지피복·생육·사건 변화와 SCL 오분류는 추가 오차를 만들 수 있다. 홍수·산불·전후 변화·열환경·SAR에는 적용하지 않는다. 실제 관측 픽셀만 고르는 별도 합성과 수치·출처를 섞지 않는다.

## 이번 ML 기능의 실제 테스트 상태

| 실행 시각 (KST) | 실행 명령 | 종료 코드 | 결과·경계 |
|---|---|---:|---|
| 2026-10-29 약 14:41 KST | `cd backend; ..\.venv\Scripts\python.exe -m pytest -q --disable-warnings --basetemp .pytest-estimate-final` | 0 | **195 passed, 12 skipped**. 12건은 `LIVE_STAC=1` opt-in 실시간 테스트로 이 명령에서 미실행 |
| 2026-10-29 약 14:41 KST | `cd frontend; npm run typecheck` | 0 | 독립 TypeScript 검사 통과 |
| 2026-10-29 약 14:42 KST | `cd frontend; npm run build` | 0 | Next.js production build 통과 |
| 2026-10-29 약 14:31 KST | `cd frontend; npm run test:e2e -- tests/estimate-mode.spec.ts` | 0 | **3 passed**. 이 3건은 TEST ONLY 계획/실행/상태/지도 UI fixture 중심 |
| 2026-10-29 약 14:46–14:49 KST | `cd frontend; npm run test:e2e` | 0 | **53 passed (2.8분)**. 새 추정 브라우저 실제 검색→계획→확인→작업→ZIP·지도 레이어와 기존 검색/합성/A2–A4/모바일/응답 경합 포함 |
| 2026-10-29 약 14:39 KST | `cd backend; $env:LIVE_STAC='1'; ..\.venv\Scripts\python.exe -m pytest -q -s tests/test_cloud_estimate_live.py --basetemp .pytest-estimate-live` | 0 | **1 passed**. 공개 Sentinel-2 실제 원본 2장, `/estimate/plan`→확인→실행→ZIP 저장·6개 GeoTIFF 재열기 |

[`backend/tests/test_cloud_estimate.py`](backend/tests/test_cloud_estimate.py)의 **테스트 전용 32×32 고정 TIFF**는 계획→실행, 6개 TIFF 재열기/CRS·NoData·transform, 목표일 원관측 불변, 추정/결측/출처 날짜, 맑은 짝픽셀 부족, 단순 복사 기준선 개선 실패, 잘못된 날짜·목적·기준선, 서명 URL 비노출을 검사한다. 직접 실행 `cd backend; ..\.venv\Scripts\python.exe -m pytest -q --disable-warnings --basetemp .pytest-cloud-estimate-20261029 tests/test_cloud_estimate.py`는 **10 passed, 종료 0, 1.97초**였다. 첫 기본 pytest 시도는 제한 샌드박스 Temp에 디렉터리를 만들지 못해 테스트 본문 전 `10 errors`, 종료 1이었고, 작업공간의 확인한 임시 경로로 재실행해 통과했다. 임시 경로는 결과 확인 후 삭제했다. Fixture는 서비스 실패 시 가짜 결과로 쓰지 않는다.

실제 사례: 공개 `S2B_52SBF_20210716_0_L2A` 목표일과 `S2B_52SBF_20210726_0_L2A` 참조일, AOI `[126.70,36.40,126.71,36.41]`, UTC 2021-07-16~26을 사용했다. AOI 995,374 m² 중 목표일 실제 유효 604,154 m²(60.7%), 모델 추정 237,514 m²(23.9%), 남은 결측 153,706 m²(15.4%)다. 2×2 공간 보류 1,131 픽셀에서 반사도 MAE는 적색 0.0112·근적외선 0.0658·녹색 0.0116이었다. 이는 **맑은 영역** 오차이며 구름 아래 정확도가 아니다. 결과 예시는 [`examples/sentinel-2-local-estimate-2021-07-16.zip`](examples/sentinel-2-local-estimate-2021-07-16.zip), 화면 기록은 [`examples/sentinel-2-local-estimate-ui.png`](examples/sentinel-2-local-estimate-ui.png)에 보존했다. 실제 GIS 프로그램 QGIS에서의 수동 열기는 미실행이고 Rasterio 재열기는 통과했다.

Windows 제한 샌드박스의 FastAPI TestClient 스레드 정체, Next.js `.next` EPERM, Edge 임시 프로필 시작 실패 때문에 허용된 로컬 환경에서 전체 회귀를 재실행했다. production build가 실행 중인 dev 서버의 `.next` 산출물을 바꾼 직후 새 실시간 E2E 첫 시도는 추천 카드가 뜨지 않아 180초 타임아웃/종료 1이었다. 로컬 서버를 재시작한 같은 테스트는 1건 통과/종료 0, 이후 전체 53건 통과/종료 0이었다. 한 실제 사례의 통과로 다른 지역·날짜·구름 아래 정확도/성능을 일반화하지 않는다.

## ML 변경 파일

`backend/app/cloud_estimate.py`(신규), `backend/app/cloud_jobs.py`, `cloud_composite.py`(GeoTIFF 기록 함수의 버전/해석 인수), `pixel_worker.py`, `main.py`, `frontend/src/components/EstimatedImage.tsx`(신규), `NaturalWorkflow.tsx`, `ImageryExplorer.tsx`, `MapPanel.tsx`, `frontend/src/app/page.tsx`, `frontend/src/lib/types.ts`, `frontend/src/app/globals.css`, `backend/tests/test_cloud_estimate.py`(신규), `test_cloud_estimate_live.py`(신규), `frontend/tests/estimate-mode.spec.ts`(신규), `examples/sentinel-2-local-estimate-2021-07-16.zip`·`sentinel-2-local-estimate-ui.png`(공개 사례), 이 문서와 README·AGENTS·`docs/ESTIMATED_IMAGE_METHOD.md`. 기존 검색·비교·다운로드·A3/A4·관측 선택 합성의 기능은 유지한다. HLS/GIBS·SAR 검색이나 배포·push는 진행하지 않았다.

---

# 과거 기록: 지도 중심 영상 탐색 검증

기준일: 2026-10-29 (Asia/Seoul). 작업 폴더: `C:\Users\aicam\Documents\ChatGPT\바이브코딩`. 이 폴더는 Git 저장소가 아니다. 이전 [A4 검사 보고서](docs/TEST_REPORT_A4_2026-10-29.md)는 당시의 별도 기록으로 보존한다. 아래 **지도 탐색 1차 범위**에 대한 결과를 최신 근거로 사용하며, 아래쪽 A4 절은 과거 시점의 기록이다.

## 이번 범위와 외부 참고

`AGENTS.md`, `frontend/AGENTS.md`, 최신 README/당시 TEST_REPORT, 패키지·pytest·Playwright 설정과 기존 검색·추천·비교·다운로드·A3/A4 코드를 읽었다. Next.js 16·MapLibre·FastAPI와 실제 STAC 검색 결과를 재사용했다. NASA HLS/GIBS, Cesium 3D, 새 구름 복원 엔진, 배포·push는 진행하지 않았다.

참고 저장소 [`bilawalsidhu/gods-eye-view`](https://github.com/bilawalsidhu/gods-eye-view)의 확인한 `main` 커밋은 `f2c6ff082d8c53e3ef4089879616b4a96fe23a7d`이다. `src/layers/recentImagery/catalog.js`, `model.js`, `source.js`의 검색 소스·선택 모델·미리보기 소스 분리 구조를 참고했다. 코드 라이선스는 [MIT](https://github.com/bilawalsidhu/gods-eye-view/blob/f2c6ff082d8c53e3ef4089879616b4a96fe23a7d/LICENSE)이며 코드/자산은 복사하지 않았다. 영상·지도·GIBS 타일의 이용 조건은 코드 라이선스와 별개다. HLS는 [후속 어댑터 설계](docs/HLS_ADAPTER_DESIGN.md)에만 기록했다.

## 실제 구현과 근거 구분

- 기존 실제 STAC 결과를 확정 UTC 기간 안의 날짜로 묶는다. 날짜 선택은 목록·지도 강조·장면 상세를 함께 바꾸되 재검색이나 기간 확대를 하지 않는다. 기간 밖/촬영일 누락 Item은 별도 건수로 알리고 날짜 탐색·지도·비교에서 제외한다. 장면 구름량 `null`은 0%로 만들지 않는다.
- 지도에서 AOI·실제 Item 촬영 범위·선택 장면을 표시하고, 비교 영상 1/2를 동일 AOI 지도에서 다른 선으로 강조한다. 카드 선택과 지도 촬영 범위 클릭은 같은 선택 상태를 갱신한다. AOI 확정 시 그 영역으로 확대한다.
- 제공처 thumbnail은 별도 패널에 두며 정합된 정량 원본 밴드가 아니다. 미리보기가 없거나 접근에 실패해도 검색 Item·링크를 유지한다. A3/A4에서 실제 읽은 픽셀 배열이 반환될 때만 품질 마스크와 NDVI 차이의 작은 PNG 지도 레이어를 활성화한다. 미실행 장면에는 가짜 레이어를 제공하지 않는다. PNG는 화면 표시용 WGS84 네 꼭짓점 근사이며 정량 값·정확한 격자/NoData는 GeoTIFF 및 처리 근거를 사용한다.
- 기존 제한적 자연어 API에 `선택한 두 날짜를 비교해`와 `이 지역으로 이동해`를 추가했다. 각각 기존 전후 비교와 확정 AOI 지도 이동을 호출하며 AOI·기간을 자동 변경하지 않는다. 범용 자유문/지명 지오코딩은 지원하지 않는다.
- 현재 식생 Sentinel-2 한 시점/기간의 실제 관측 픽셀 선택 합성 코드도 기존 작업 폴더에 있다. 이번 지도 단계에서 새 엔진으로 확장하지 않았다. 이는 한 날짜 촬영 또는 ML 복원이 아니다. HLS S30/L30 검색, GIBS 미리보기, SAR 직접 처리, 다중 센서 조화는 미구현이다.

장면 전체 메타데이터 구름량, AOI와 footprint의 기하 중첩, SCL/NoData 실제 픽셀 진단, NDVI 변화는 각각 다른 근거다. 지도 품질 레이어는 실제 진단 범위의 유효/제외 픽셀 시각화이지 분석 가능 확정이 아니다. NDVI 양수/음수 레이어는 변화 원인이나 식생 증감을 확정하지 않는다. QGIS 프로그램 자체의 시각 검증은 수행하지 않았다.

## 실행 기록 — 중간 근거와 재실행 이력

| 실행 시각 (KST) | 위치·명령 | 종료 코드 | 실제 결과 |
|---|---|---:|---|
| 2026-10-29 12시대 KST | `backend`: `..\.venv\Scripts\python.exe -m pytest -q` | 0 | **185 passed, 11 skipped**. 고정 소형 래스터 PNG/QA/NDVI 테스트 포함. `LIVE_STAC=1` opt-in 11건은 이 명령에서 미실행 |
| 2026-10-29 12시대 KST | `frontend`: `npm run typecheck` | 0 | `tsc --noEmit` 독립 통과. 빌드와 겹치지 않게 순차 실행 |
| 2026-10-29 12시대 KST | `frontend`: `npm run build` | 0 | Webpack production compile·내장 TypeScript·정적 생성 통과 |
| 2026-10-29 12시대 KST | `frontend`: `npm run test:e2e` | 0 | **48 passed (2.2분)**. 이 시점 이후 지도 클릭 테스트를 추가했고 최종 전체 결과는 아래에 기록 |
| 2026-10-29 12시대 KST | `frontend`: `npm run test:e2e -- tests/imagery-explorer.spec.ts -g "지도 촬영 범위 클릭"` | 0 | **1 passed**. 지도 클릭→날짜·목록·상세 상태 확인 |
| 2026-10-29 12시대 KST | `frontend`: `npm run test:e2e -- tests/change-analysis.spec.ts -g "A4 실제"` | 0 | **1 passed**. 실제 NDVI·ZIP과 지도 품질/변화 레이어 활성화·토글. 화면을 육안 확인했다 |

위 48건은 이후 AOI 자동 확대와 지도 클릭 테스트 추가 **이전** 실행이다. 최종 전체 재실행은 아래에 따로 기록했다. 테스트 fixture는 `backend/tests`와 `frontend/tests` 전용이고 서비스 실패 시 결과로 대체하지 않는다. 백엔드 기본 pytest의 live 11건은 미실행이지만 브라우저의 실제 STAC/래스터 사례는 외부 연결로 실행됐다.

### 실패·환경 이력

- 제한된 샌드박스에서 `.next/static/chunks` 생성이 `EPERM`으로 빌드 종료 1. 허용된 로컬 환경의 같은 소스로 재실행하면 종료 0. 빌드와 동시에 돌린 독립 typecheck는 생성 중 `.next/types`를 찾지 못해 종료 1; 빌드 후 순차 실행은 종료 0.
- 제한된 샌드박스의 Edge 임시 프로필 쓰기 오류로 신규 E2E 4건은 브라우저 시작 전 종료 1. 허용된 환경에서 같은 4건은 모두 통과했다.
- 신규 지도 클릭 테스트는 지도 캔버스가 화면 밖에 부분 배치된 상태를 클릭해 1회 실패(종료 1). 테스트가 지도를 화면 안으로 스크롤한 뒤 재실행해 통과했다. 서비스 실패로 분류하지 않는다.
- 첫 49건 전체 E2E는 지도 범례 문구가 바뀐 뒤 예전 문자열을 단언해 **48 passed / 1 failed**, 종료 1이었다. 단언을 실제 새 문구로 고치고 실영상 단독·전체를 다시 실행해 통과했다. 변경된 문구의 지도 표시 자체는 당시 스크린샷과 DOM에서 확인됐다.
- 제한된 샌드박스에서 기본 pytest가 출력 없이 장시간 정체되어 중단(종료 1). 허용된 로컬 환경에서 전체 pytest 185/11 종료 0 확인.
- HTTP/콘솔 404는 원인 확인 없이 해결됐다고 판단하지 않는다. 실시간 검색 E2E가 기록한 해당 실행의 HTTP 오류 목록은 비어 있었지만 모든 제공처 상태를 보장하지 않는다.

## 최종 실행 — 마지막 코드 수정 후

| KST 실행 창 | 위치·명령 | 종료 코드 | 통과·미실행 |
|---|---|---:|---|
| 2026-10-29 약 12:30 | `backend`: `..\.venv\Scripts\python.exe -m pytest -q` | 0 | **185 passed, 11 skipped**. Opt-in 백엔드 실시간 테스트 11건 미실행 |
| 2026-10-29 약 12:44 | `frontend`: `npm run typecheck` | 0 | 독립 TypeScript 검사 통과 |
| 2026-10-29 약 12:44 | `frontend`: `npm run build` | 0 | Next.js production build 통과 |
| 2026-10-29 약 12:49–12:51 | `frontend`: `npm run test:e2e` | 0 | **49 passed (2.3분)**. 실제 STAC 검색, A2/A3/A4 공개 영상, 실제 구름 계획→확인→합성 ZIP, 지도 클릭, 날짜·목록·비교·레이어, 부분 실패·모바일·응답 경합 포함 |

최종 E2E에서 실제 A4 지도 PNG 화면 `frontend/test-results/a4-live-map.png`를 생성하고 육안 확인했다. 외부 타일·영상 서비스의 장기 가용성은 현재 한 차례 실행으로 보장하지 않는다. 유료 API·새 인증·배포·push는 수행하지 않았다.

## 이번 지도 단계 변경 파일·재현

`frontend/src/lib/imageryExplorer.ts`(신규), `frontend/src/components/ImageryExplorer.tsx`(신규), `MapPanel.tsx`, `SceneComparison.tsx`, `Results.tsx`, `NaturalWorkflow.tsx`, `frontend/src/app/page.tsx`, `globals.css`, `frontend/src/lib/types.ts`, `backend/app/pixel_raster.py`, `pixel_worker.py`, `change_analysis.py`, `request_interpretation.py`, `backend/tests/test_map_previews.py`(신규), `frontend/tests/imagery-explorer.spec.ts`(신규), `frontend/tests/change-analysis.spec.ts`. README, AGENTS, NEXT_STEPS, HLS_ADAPTER_DESIGN과 이 보고서를 갱신했다. 기존 사용자 변경 및 이전 진행 중 구름 코드·기능을 보존했다.

실시간 재현: 루트에서 `node scripts/start-local.mjs`, `http://127.0.0.1:3000/`. 식생 목적·UTC 2021-07-01~31·작은 AOI `[126.70, 36.40, 126.71, 36.41]`로 Sentinel-2 검색. 날짜 버튼/카드/지도에서 선택하고 전후 모드에서 `S2B_52SBF_20210716_0_L2A` → `S2B_52SBF_20210726_0_L2A`를 선택한다. `두 날짜 NDVI 계산` 후 품질/변화 지도 레이어를 토글하고 ZIP을 저장한다. 실제 제공처 연결이 필요하다.

---

# 과거 기록: A4 식생 NDVI 변화 분석

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

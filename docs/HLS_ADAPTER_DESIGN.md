# HLS L30/S30 연결 계약 (2026-11-02)

## HTTP 400 후속 진단 — 2026-11-02 17:45~17:55 KST

**정상화 미완료.** 현재 CMR의 동일 장면 browse URL을 최소 무인증 GET과 앱 전송으로 비교했다. L30/S30 모두 `data.lpdaac.earthdatacloud.nasa.gov`의 최초 응답(hop=0)이 HTTP400, application/json, 본문0바이트였다. 리다이렉트가 없으므로 최종 호스트도 같았다. 기존 암호화 저장소의 NASA 자격을 사용하는 B04 Range도 동일400이었다. Content-Range/TIFF 바이트/전체 크기는 확인되지 않았다. 인증 성공·토큰 만료·제공처 내부 원인을 확정할 근거가 없다. URL 선택 오류도 확인되지 않아 hls.py/cmr.py는 변경하지 않았다.

`provider_transfer.diagnostics(records)`는 명시적으로 켠 로컬 실행 문맥에서만 단계·hop·허용 호스트·공개 HLS 제품 경로·상태·Content-Type·선언/수신 크기·숫자 Content-Range·Range/Authorization 존재 여부를 수집한다. 요청별 문맥 분리·64행 상한, query/userinfo/원문 본문/Location/토큰 미보관, 알 수 없는 경로 삭제를 적용했다. 평상시 HTTP 응답이나 로그로 전달하지 않는다. 206 Range의 시작/종료/전체 크기·길이를 검증하고, 오류 JSON/HTML·부분 수신을 전체 원본 성공으로 처리하지 않는다. 화면에는400과 인증 원인 미확정을 설명한다.

`scripts/diagnose-hls-local.py`는 기존 env 로더로 실행하는 명시적 실검증 도구다. 기존 active grant만 사용하고 신규 채택·갱신·회전은 거부한다. 원본은 probe 성공·크기 확인 후 제품별 최대1개/10MiB만 허용한다. 429·로그인·동의·차단 redirect·크기 상한은 중단한다. 이번에는 B04 probe에서 실패해 전체 파일을 받지 않았다. 증거는 비밀 없는 `test-results/hls-diagnostic/report.json`, 현재 사이트 화면 결과는 `browser-live.json`이다. 상세 명령/성공·실패·미실행 구분은 최신 TEST_REPORT를 따른다.

공식 [HLS 접근 안내](https://hls.gsfc.nasa.gov/data-access-and-tools/)와 [Earthdata User Token 문서](https://urs.earthdata.nasa.gov/documentation/for_users/user_token)를 다시 확인했다. 재제공 설정·자격증명·허용 호스트를 변경하지 않았다. 다른 제공처 HLS 대체 연결·신규 분석·디자인 변경은 이번 범위에 포함하지 않았다. 다음 확인은 LP DAAC에 아래 표본의 UTC 시각·공개 경로·첫 응답400/빈 본문을 제시해 해당 요청의 처리 원인을 확인하는 것이다. 토큰을 전달할 필요는 없다.

---

사용자가 HLS 전용8개 설정 적용·인증 실검증과 작업 부재 확인 후 프로젝트 재시작을 승인했다. 실제 토큰·만료값과 다른 설정은 보존했다. CMR 검색은 L30 1건/S30 2건 성공했으나 공개 browse/인증 B04는 HTTP400으로 실패했다. 로컬 DPAPI 저장 active는 실제 NASA 인증 성공이 아니며 원본 전체 수신은 미실행이다. 공개 S3 browse의 실제 객체도 무인증403이었다.

이번 후속 요청으로 아래 과거 설계의 **검색·실제 browse·원본 다운로드**를 기존 NASA CMR/미디어/운영자 인증에 구현한다. 아래의 GIBS 타일 설계는 이번에 구현하지 않는다. 인증 설정과 실제 파일 성공은 별도이며 최신 실행 결과는 TEST_REPORT.md를 따른다.

## 등록과 자료 근거

| 앱 컬렉션 | 공식 ShortName/Version | CMR Concept ID | 원본 경로의 제품 폴더 | DOI |
|---|---|---|---|---|
| hls-l30-002 | HLSL30 / 2.0 | C2021957657-LPCLOUD | HLSL30.020 | 10.5067/HLS/HLSL30.002 |
| hls-s30-002 | HLSS30 / 2.0 | C2021957295-LPCLOUD | HLSS30.020 | 10.5067/HLS/HLSS30.002 |

2026-11-02 실제 CMR UMM 조회: L30 revision98, S30의 현재 UMM·Version·DOI·30m 격자·시작일을 확인했다. 등록 ID는 검증된 release snapshot이며 임의 제품 발견을 자동 활성화하지 않는다. 검색은 기존 CMR bbox/UTC 기간·page_num/page_size25·제공처 최대4요청·45초·전체 결과 상한/중복/부분 실패를 재사용한다. 각 결과는 제공처+컬렉션+granule ID로 구분한다.

공식 근거:
- [L30 CMR UMM](https://cmr.earthdata.nasa.gov/search/collections.umm_json?concept_id=C2021957657-LPCLOUD), [S30 CMR UMM](https://cmr.earthdata.nasa.gov/search/collections.umm_json?concept_id=C2021957295-LPCLOUD).
- [NASA HLS L30 제품·레이어·scale](https://hls.gsfc.nasa.gov/products-description/l30/), [S30 제품·밴드 대응·resampling·scale](https://hls.gsfc.nasa.gov/products-description/s30/), [HLS 접근 안내](https://hls.gsfc.nasa.gov/data-access-and-tools/), [공식 인용 안내](https://hls.gsfc.nasa.gov/documents/).
- [NASA 공개 HLSL30 메타데이터/라이선스](https://data.nasa.gov/dataset/hls-landsat-operational-land-imager-surface-reflectance-and-toa-brightness-daily-global-30-b4633), [HLSS30 메타데이터/라이선스](https://data.nasa.gov/dataset/hls-sentinel-2-multi-spectral-instrument-surface-reflectance-daily-global-30m-v2-0-bee8f): accessLevel public, 정부 저작물 이용 안내 링크. CMR UseConstraints도 NASA data-use-policy를 가리킨다. 인증 성공은 재제공 검토 완료의 대체 근거가 아니다. Earthdata 정책 본문 일부 주소는 이 환경에서403/접근 실패였음을 남기며, 모든 NASA 제품의 무제한 재제공 허가로 넓히지 않는다.
- [EDL User Token](https://urs.earthdata.nasa.gov/documentation/for_users/user_token): 호환 앱 승인·60일 만료·renew_token의 이전 토큰 무효화. 방문자별 OAuth와 별개다.

HLS는 Landsat OLI/OLI-2 및 Sentinel-2 MSI 관측에서 만든 조화 NBAR 광학 시계열이며 UTM/MGRS30m 제품이다. L30 반사도는 B04적색/B05NIR/B06SWIR1/B07SWIR2, S30은 B04/B8A/B11/B12를 동일 역할로 선택한다. S30 B08과 B8A를 동일 파일로 합치지 않고 목적 기본 NIR은 B8A를 우선한다. 실제 CMR이 제공한 개별 GeoTIFF만 선택한다. 원문에 없는 밴드/플랫폼/구름량/파일 크기를 생성하지 않는다. CMR JSON에 개별 입력 플랫폼이 없으면 null이다. 제품 계열 사양과 그 사실을 함께 표시한다.

반사도scale0.0001과 Fmask 비트 QA는 S2 L2A scale/offset·SCL 엔진과 호환 판정을 하지 않았다. **A2~A4·합성·ML 미지원**. L30 B10/B11은 TOA 밝기온도이며 지표면온도로 추천/처리하지 않는다. HLS는 열환경 추천 목록에 추가하지 않는다. 실제 타일 geometry 중첩은 유효 픽셀 비율이 아니다. 파일명 시각을 타일 내 모든 픽셀 촬영시각으로 간주하지 않는다.

## 미리보기·원본·보안

CMR canonical granule의 실제 /browse# JPG와 /data# 개별 TIFF만 사용한다. 호스트·제품 버전 폴더·동일 granule title·파일명을 검증하고 서명 URL을 제외한다. 공개 browse 우선, 없으면 missing_asset, 접근 실패면 실제 HTTP·실패 상태다. 다른 장면/가짜 미리보기/GIBS로 대체하지 않는다.

원본은 기존 `/media/session`→`/media/inspect`→명시 `/media/downloads/<receipt>`를 재사용한다. inspect의 GET Range/헤더 형식 확인과 전체 다운로드 완료를 구분하고, 확인 가능한 전체 파일 크기를 표시한다. 전체 수신·형식 magic 확인 전 파일 응답으로 내보내지 않는다. HTML·401·403·404·timeout·미완료·크기 제한은 별도다. 보호된 HLS 파일은 NASA 인증으로 요청하며 공개 browse에는 우선 인증을 붙이지 않는다. 토큰은 허용 LP DAAC 인증 호스트에만 보내고 교차 호스트 리다이렉트 이후 영구 제거한다. 호스트/제품 경로·DNS·파일명·동시2·35초/파일·원본256MiB·preview8MiB/16MP·receipt120초·사용량 상한은 기존 경로를 유지한다.

운영자 자격은 Windows DPAPI/SQLite 최신 회전값을 재사용한다. 사용자별 Earthdata OAuth도 그대로 남긴다. 미검토 HLS 제품에 과거 VIIRS용 확인값을 자동 승계하지 않는다. **실제 .env 값/자격은 승인 전 변경하지 않는다.**

## 필요한 서버 설정과 정확한 활성화안

현재 토큰과 만료 설정은 존재하나 공통/NASA enable·정책 확인값은 미설정으로 확인했다(값 출력 없음). 최초로 HLS만 활성화할 경우:

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

마지막 두 값은 제공처/대상 HLS 이용·재제공 검토의 명시 확인이며 코드를 실행하기 위해 임의로 켜는 우회값이 아니다. 설명한 출처와 제한을 확인하고 운영자의 승인을 받은 뒤에만 적용한다. OPERATOR_NASA_USER_TOKEN/OPERATOR_NASA_TOKEN_EXPIRES_AT 기존 값은 유지한다. 새 COLLECTIONS 기본은 과거 VIIRS뿐이므로 기존 운영자의 허용 제품이 조용히 확대되지 않는다. 위 활성화안은 HLS만 허용하고 VIIRS는 운영자 인증 대상으로 추가하지 않는다. 다른 운영자 제공처는 켜지 않는다.

실제 검증안: 한국 작은 bbox126.7/36.4/126.71/36.41, UTC2025-07-20~26. 두 제품 각1장면, 실제browse/인증원본 접근을 분리한다. 먼저 원본 크기 확인, 작은 단일 광학 밴드 각1개만 선택(파일당 최대16MiB/합계32MiB), 전체 수신 후 GTiff/격자/자료형/작은 픽셀 범위 디코딩 확인. 작지 않으면 중단/작은 품질 밴드 별도 표기, 일괄 다운로드 없음. 401 발생시 기존 공식 경로의 최대1회 갱신은 토큰을 교체·이전 토큰을 무효화할 수 있으므로 승인 내용에 포함한다. 실패는 실제 상태로 기록한다.

서버 재시작은 진행 중 분석/다운로드 부재를 확인한 뒤 해당 프로젝트만 수행한다. 공개 배포·새 키 발급·비용 동의·AI 호출은 포함하지 않는다.

---

# HLS 검색·미리보기 후속 설계 (미구현)

작성일: 2026-10-29. 이번 지도 탐색 1차 범위에는 HLS 검색이나 GIBS 타일 연결을 넣지 않았다.

## 검토 근거

- 참고 저장소 `bilawalsidhu/gods-eye-view`, 확인한 `main` 커밋 `f2c6ff082d8c53e3ef4089879616b4a96fe23a7d`.
- 검토 경로: [`catalog.js`](https://github.com/bilawalsidhu/gods-eye-view/blob/f2c6ff082d8c53e3ef4089879616b4a96fe23a7d/src/layers/recentImagery/catalog.js), [`model.js`](https://github.com/bilawalsidhu/gods-eye-view/blob/f2c6ff082d8c53e3ef4089879616b4a96fe23a7d/src/layers/recentImagery/model.js), [`source.js`](https://github.com/bilawalsidhu/gods-eye-view/blob/f2c6ff082d8c53e3ef4089879616b4a96fe23a7d/src/layers/recentImagery/source.js).
- 저장소 코드 라이선스: [MIT](https://github.com/bilawalsidhu/gods-eye-view/blob/f2c6ff082d8c53e3ef4089879616b4a96fe23a7d/LICENSE). 이번 구현은 소스나 자산을 복사하지 않고, 검색 소스와 화면 표시 모델을 분리한다는 구조만 참고했다. 향후 코드를 직접 재사용하면 원 저작권·라이선스 고지를 보존해야 한다.
- 지도 OpenStreetMap 타일, NASA GIBS 타일, CMR 메타데이터, HLS 원본 파일의 이용·표시·다운로드 조건은 코드 MIT 라이선스와 별도로 확인한다.

## 분리된 어댑터

1. 백엔드 `HlsCmrAdapter`(신규 설계)는 NASA CMR에서 HLS S30과 L30을 현재 STAC 제공처와 별도 조회한다. 호출자는 확정 AOI·UTC 기간·상한을 그대로 전달한다. 제품 ID와 센서 계보를 유지하며, S30/L30을 기존 `sentinel-2-l2a`/`landsat-c2-l2`와 혼합 식별하지 않는다.
2. CMR 페이지 커서/Search-After, 최대 요청 수·시간·전체 결과 상한을 둔다. `(collection, granule_id)`로 중복 제거한다. 제공처별 성공·빈 결과·부분 성공·실패·조회 제한을 반환한다. HLS 실패가 기존 STAC 검색 성공 결과를 지우지 않도록 결과 병합은 상위 검색 서비스에서 수행한다.
3. 프론트엔드 날짜 모델은 현재 `src/lib/imageryExplorer.ts`를 재사용하고 소스 종류를 구분한다. 30일 기본 기간이나 20% 장면 구름 필터를 참고 저장소에서 복사하지 않는다. 사용자 기간과 목적별 조건이 우선한다.
4. 미리보기 어댑터는 GIBS의 **표시용** 타일과 촬영일·레이어 ID를 지도 레이어로 제공한다. GIBS 타일을 정량 반사도 밴드, QA 마스크, 구름 보정 또는 분석 산출물로 표시하지 않는다. HLS 30 m 출력 격자를 Sentinel-2 원본 10 m 해상도나 지표온도 제품으로 표시하지 않는다.
5. 원본 Asset 접근은 미리보기와 별도의 검증 경로로 확인한다. 공식 API의 현재 인증·토큰·다운로드 이용 조건, 실제 COG/파일 Header 및 밴드/QA 접근을 확인한 뒤에만 처리와 다운로드 지원 상태를 변경한다. 서명 URL·자격증명은 로그/manifest에서 제거한다.

## 채택 전 검증

- 공식 NASA CMR/HLS/GIBS 현재 문서와 실제 API 응답으로 컬렉션·제품·페이지네이션·링크 접근·이용 조건을 재확인한다.
- 같은 AOI·기간의 S30/L30 실제 결과, 중복, 페이지 경계, 0건, HLS 타임아웃과 기존 STAC 부분 성공 보존, 미리보기 없음, 잘못된 날짜를 테스트한다.
- GIBS 표시와 HLS 분석 밴드가 서로 다른 자료임을 UI와 API에서 확인한다. 새 인증·비용·지속 접근이 필요하면 그 단계에서 중단한다.

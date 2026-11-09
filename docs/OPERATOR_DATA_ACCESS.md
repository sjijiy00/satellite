## 2026-11-05 USGS 승인 후 실검증

기존 서버 자격으로 승인 이후 동일 제품·QA_PIXEL의 앱 내 다운로드를 검증했습니다. 동일 entityId+productId가 여러 목록에 반복되는 응답은 중복 제거하며, 다른 식별자나 checksum/filesize 상충은 거절합니다. 밴드별 바로 다운로드는 접근 확인과 수신을 명시 클릭으로 연결합니다. 구미7월11일 QA_PIXEL 3,968,136bytes의 API·브라우저 수신과 GeoTIFF·해시 일치를 확인했습니다. 아래 과거 미검증 기록 이후의 최신 근거와 제한은 [TEST_REPORT](../TEST_REPORT.md)의 USGS 절을 참고하세요.

# 운영자 자료 접근 구현 계약 (2026-11-02)

## 2026-11-04 운영자 계정 연결 점검

- NASA 운영자 User Token은 현재 `backend/.env`에 설정돼 있다. 기존 HLS 파일의 제한적 Range 요청은 206이었지만 전체 파일 다운로드·GIS 재열기의 증거가 아니다. 동일 revision의 암호화 grant를 명시적으로 재개하는 `OPERATOR_NASA_RESUME_STORED_GRANT=1` 설정은 env token이 없을 때만 적용한다. 만료 전 자동 갱신은 **실제 요청 시** 수행하며 무기한 세션 유지를 보장하지 않는다.
- USGS ERS Application Token으로 M2M `login-token`과 정확한 Landsat 8 L2SP `scene-metadata` 조회가 성공했다. M2M `download-options`는 HTTP 403이었다. 사용자가 `MACHINE` 역할을 신청했으며 ERS 목록에서 **Pending**을 확인했다. 최신 서버에서 실제 Item의 개별 파일 검사는 `operator_permission_denied`였다. 승인·파일별 재검사 전에는 원본 접근 성공이라 표시하지 않는다. `scene-metadata`는 공식 단수 `entityId`와 `idType=displayId`를 사용하고 정확한 제품 ID를 재확인한다. HTTP 403은 응답 본문이 HTML이어도 권한 오류로 분류한다.
- CDSE 기존 password grant는 `invalid_grant`였다. `OPERATOR_CDSE_REFRESH_TOKEN`의 공백만 있는 값을 빈 값으로 고쳐 revision 파싱 오류를 정리했다. 운영자가 `backend/.env`를 revision 3으로 갱신한 후에도 실제 Sentinel-1 Asset 검사는 `operator_reconnection_required`였고 파일 전송에 도달하지 않았다. 사용자는 [Copernicus Marine 연동 웹 로그인](https://dataspace.copernicus.eu/news/2026-10-12-copernicus-data-space-ecosystem-and-copernicus-marine-service-logins-mutually)을 사용한다. 현재 CDSE 화면은 계정 생성 성공 후 이메일 확인을 요구한다. 웹 로그인 권한 상호 인정과 [OData 직접 password grant](https://documentation.dataspace.copernicus.eu/APIs/OData.html)의 Marine 자격 허용은 별개이며 후자는 공식 안내에서 확인되지 않았다. `cdse-public` 기기 인증 시험은 HTTP 400 `unauthorized_client`였다. 브라우저 쿠키/코드를 추출하거나 Marine 비밀번호로 반복 로그인하지 않는다. 이메일 확인 및 계정의 공식 API 자격 경로가 확인되면 **새 revision**으로 작은 Range 검사와 명시 다운로드를 각각 재검증한다. 로그인 정보나 토큰을 채팅에 보내지 않는다.
- 이번 인증/제품 매핑 코드의 집중 검증은 `TEST_REPORT.md`의 63 pytest 및 19 Node 테스트다. 전체 파일 수신, 재열기, 모든 제공처 실접근은 아직 통과로 기록하지 않는다.

## 2026-11-03 CDSE Sentinel-1 대용량 원본 후속 점검

- 화면의 실제 Item `S1A_IW_GRDH_1SDV_20250817T093217_20250817T093243_060574_0788C1_8F3F_COG`의 공개 STAC 크기는 Product ZIP 1,177,053,605 bytes, VV 627,835,581 bytes, VH 541,730,379 bytes다. 기존 파일당 256 MiB, 사용자 시간당 512 MiB, 운영자 시간당 1 GiB 상한을 모두 넘거나 쉽게 소진한다. 이 제품의 접근 범위 확인을 전체 수신 완료로 표현하지 않는다.
- CDSE `sentinel-1-grd`만 파일당 2 GiB, 사용자·제공처 시간당 3 GiB, 외부 수신 최대 20분·브라우저 전달 최대 5분으로 분리했다. 원본은 서버 임시 spool에 전체 수신한 뒤 브라우저의 파일 저장 스트림에 기록한다. 저장 위치를 직접 고르는 Chrome/Edge가 필요하며 임시 디스크 여유와 제공처 속도·쿼터에 따라 실패할 수 있다. 다른 제품의 256 MiB/35초/512 MiB 제한은 유지한다. 동시에 진행하는 자동 미리보기 두 건 때문에 명시 원본 확인이 즉시 `busy`가 되는 문제는 최대 12초 대기로 완화했다. 무제한 재시도·무제한 전송은 없다.
- [공식 Sentinel 데이터 고지](https://cds.climate.copernicus.eu/licences/ec-sentinel)는 Sentinel 데이터 배포와 공중 전달을 허용하며 `Copernicus Sentinel data [Year]` 출처 고지를 요구한다. [CDSE 포털 약관](https://dataspace.copernicus.eu/terms-and-conditions)은 Sentinel 데이터와 그 외 포털 콘텐츠의 권리를 구분한다. 이 검토는 이 앱의 Sentinel-1 원본 제품 범위에 한정한다. 로컬 `backend/.env`의 `OPERATOR_CDSE_ENABLED` 및 `OPERATOR_CDSE_REDISTRIBUTION_REVIEWED`만 활성화했고 자격 값은 변경하지 않았다. 공개 배포 승인은 아니다.
- **현재 실연결 실패:** 설정된 CDSE 사용자명·비밀번호를 공식 `cdse-public` password grant에 보냈을 때 HTTP 400 `invalid_grant`였다. 앱의 1 KiB 원본 검사도 `operator_reconnection_required`이며 실제 ZIP/측정 TIFF 수신은 실행하지 않았다. 계정 정보 오류와 2FA 필요 여부는 이 응답만으로 구분할 수 없다. [공식 토큰 절차](https://documentation.dataspace.copernicus.eu/APIs/Token.html)에 따라 운영자가 계정을 확인하고 `OPERATOR_CDSE_PASSWORD`를 바로잡거나 공식 2FA 절차의 refresh token을 `OPERATOR_CDSE_REFRESH_TOKEN`에 설정한다. 이후 `OPERATOR_CDSE_REVISION`을 현재 값보다 높여 저장소의 실패 세대를 재초기화하고 서버를 재시작한다. 토큰·비밀번호·2FA 코드를 채팅에 보내지 않는다. 다시 1 KiB 검사 → 버튼 활성화 → 명시 전체 수신·ZIP/TIFF 재열기를 확인해야 완료다.
- 아래 2026-11-02의 자격 미설정·256 MiB 문장은 당시 구현 기록이다. 현재 상태와 상한은 이 절 및 최신 TEST_REPORT를 우선한다.

> HLS 후속 연결: HLSL30/HLSS30 v2.0 검색·browse·서버 원본 경로와 제품별 허용/정책 게이트를 추가했습니다. 사용자 승인 후 현재 HLS 두 제품만 운영자 인증 대상으로 설정했습니다. 토큰/만료값을 보존했습니다. 실제 CMR 검색 성공과 LP DAAC browse/인증 파일 HTTP400 실패를 구분하며, 암호화 저장만으로 실제 인증 성공이라 하지 않습니다. [HLS 계약](HLS_ADAPTER_DESIGN.md)과 최신 TEST_REPORT를 따릅니다. 아래의 자격증명 미설정 문구는 초기 구현 당시 기록입니다.

> 후속 공개 경로: Planetary Computer의 익명 SAS와 NOAA NDVI CDR는 운영자 로그인과 별개로 연결했습니다. 공개 Asset을 먼저 쓰고 requester-pays는 계속 비활성입니다. 정확한 제품·범위·출처는 [PUBLIC_DATA_ACCESS](PUBLIC_DATA_ACCESS.md), 최신 테스트는 TEST_REPORT를 따릅니다.

이 절은 아래의 초기 설계를 확장한 **이번 실제 코드 계약**이다. 자격증명이 없는 상태의 구현/fixture 검증과 실제 제공처 인증·다운로드 성공을 구분한다. 최신 실행 증거는 [TEST_REPORT](../TEST_REPORT.md)를 따른다. 현재 `.env`에는 제공처/운영자 변수 이름이 없음을 값 없이 확인했다. 실제 키·계정·비용 동의·설정 활성화·공개 배포는 대신 수행하지 않았다.

## 실제 연결과 허용 범위

| 제품/경로 | 코드 | 실제 운영자 접속 |
|---|---|---|
| Earth Search S2 L2A 공개 Asset | 기존 canonical/전송/QA 유지, 기존 밴드 패널의 명시 원본 접근 도구 연결 | 공개 경로 별도 실검증. 운영자 인증 불필요 |
| Landsat 8/9 C2 L2SP/L2SR | 기존 USGS 동일 제품·촬영일·플랫폼·컬렉션/파일 대응 유지. 운영자 M2M login-token → display ID 목록 → download-options의 정확한 secondary file → download-request, scene-metadata가 실제 제공한 동일 제품 browse | 자격 없음, fixture만 검증. 실제 M2M 문서 상세·계정별 응답/파일 옵션 대응은 계정 준비 후 재확인 필요 |
| Sentinel-1 GRD/COG | canonical Product OData UUID만 사용. Product ZIP 또는 canonical S3 measurement 파일의 동일 SAFE/노드 경로. CDSE-public password/공식 refresh grant, 공식 Nodes 목록으로 확인한 preview/quick-look.png만 대체 미리보기 후보 | 자격 없음, fixture만 검증. 실제 STAC Product/measurement/thumbnail 형식은 읽기 전용 확인 |
| NASA VNP09GA.002 | 공개 browse 우선. protected LP DAAC 파일에만 운영자 User Token, EDL renew_token 사용 | 공개 browse와 인증 원본은 별도. 인증 자격 없음, 갱신/인증 원본은 fixture만 |
| AWS Landsat requester-pays | 비활성. USGS는 별도 공식 파일 경로만 사용 | AWS 자격·비용 동의를 요청/실행하지 않음 |

전국/모든 위성/모든 Asset을 지원하지 않는다. 센서/QA/NDVI/관측 합성/ML 엔진은 확장하지 않았다. S1·VIIRS·Landsat 운영자 다운로드가 픽셀 분석 지원을 의미하지 않는다.

## 공식 인증·재제공 근거 (2026-11-02 확인)

- [USGS Application Token](https://www.usgs.gov/media/files/m2m-application-token-documentation): 비밀번호 login 대신 login-token. M2M 세션의 X-Auth-Token은 M2M API에만 사용하고 파일 호스트에 Bearer로 붙이지 않는다. [M2M 공식 안내](https://m2m.cr.usgs.gov/)는 공식 API의 검색/다운로드 URL 발급 역할을 설명한다. 상세 예제/JSON 문서는 비로그인 요청이 ERS 로그인 화면으로 이동하여 파일 옵션 스키마의 **실계정 검증은 남아 있다**. 알 수 없는 파일/응답/준비 중 자료는 임의 파일로 대체하지 않는다. M2M scene-metadata가 동일 Product ID의 실제 browse URL을 반환한 경우에만 후보로 사용하고 미수록/허용 호스트 밖/파일 접근 실패는 미제공으로 유지한다.
- [USGS Landsat public domain](https://www.usgs.gov/faqs/are-landsat-data-cloud-still-considered-be-within-public-domain), [공식 Cloud Guide](https://d9-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/s3fs-public/atoms/files/LSDS-2032-Landsat-Commercial-Cloud-Direct-Access-Users-Guide-v2.pdf.pdf): Landsat 자료 이용·재배포와 AWS 저장소 요청자 비용은 별개다. 출처/제품 ID를 유지한다. M2M 계정 권한·요청 한도도 별도다.
- [CDSE Token](https://documentation.dataspace.copernicus.eu/APIs/Token.html), [OData Nodes/Download/Refresh](https://documentation.dataspace.copernicus.eu/APIs/OData.html): cdse-public와 공식 password/refresh grant를 사용한다. Sentinel Hub client credentials를 OData 인증으로 전용하지 않는다. 2FA 요구는 우회하지 않으며 운영자가 공식 인증에서 얻은 refresh token을 서버에 설정할 수 있다. [Sentinel 데이터 라이선스](https://cds.climate.copernicus.eu/licences/ec-sentinel)는 적법한 배포·공중 전달을 허용하고 출처 표시를 요구한다. [CDSE 이용 조건](https://dataspace.copernicus.eu/terms-and-conditions)은 Sentinel 데이터와 다른 포털 콘텐츠를 구분한다. 다른 포털 이미지/상용 제품을 재제공 허용 데이터로 넓히지 않는다. [계정 쿼터](https://documentation.dataspace.copernicus.eu/Quotas.html)를 계정 여러 개로 회피하지 않는다.
- [EDL User Token 공식 문서](https://urs.earthdata.nasa.gov/documentation/for_users/user_token): User Token은 최대60일, renew_token은 기존 토큰을 무효화하고 새 토큰/expiration_date를 반환한다. 기존 방문자 OAuth refresh와 다른 어댑터다. [VNP09GA.002 공식 CMR](https://cmr.earthdata.nasa.gov/search/concepts/C2631841556-LPCLOUD/71), [UMM](https://cmr.earthdata.nasa.gov/search/collections.umm_json?concept_id=C2631841556-LPCLOUD) 실제 읽기에서 ShortName/Version과 AccessConstraints=None를 확인했다. 이는 모든 NASA 자료의 재제공 허가나 계정 승인 완료를 의미하지 않는다. 대상 DOI 10.5067/VIIRS/VNP09GA.002·출처를 유지하고, 대상 DAAC 승인/EULA/공개 제공 조건을 운영자가 검토해야 한다. 403을 포괄 재배포 권한으로 해석하지 않는다.

모든 인증 경로는 별도의 `REDISTRIBUTION_REVIEWED=1`이 있어야 동작한다. 코드 allowlist는 위 제품뿐이며 이 값은 검토 사실의 명시 설정이다. 개발 중 대신 동의하거나 권한을 만들어 주지 않는다. 실제 기관/서비스 이용 조건의 변경·개별 제한을 다시 확인하고 제한 자료는 등록하지 않아야 한다.

## 서버 설정 이름과 준비

공통: `OPERATOR_ACCESS_ENABLED=1`, `OPERATOR_PUBLIC_ORIGIN`(정확한 사이트 origin), `OPERATOR_WORKERS=1`. 선택형 `OPERATOR_STORE_PATH` 기본값은 `backend/.private/operator/access.sqlite3`이다. 실제 `.env`는 변경하지 않았다. 예시 파일은 비활성/빈 값만 추가했다.

각 제공처에는 `OPERATOR_USGS_ENABLED`, `OPERATOR_CDSE_ENABLED`, `OPERATOR_NASA_ENABLED`와 각각의 `_REVISION`(초기1), `_REDISTRIBUTION_REVIEWED`가 있다.

- USGS: `OPERATOR_USGS_USERNAME`, `OPERATOR_USGS_APPLICATION_TOKEN`. 운영자가 ERS 계정/M2M 권한과 Application Token을 직접 준비한다.
- CDSE: `OPERATOR_CDSE_USERNAME`, `OPERATOR_CDSE_PASSWORD` **또는** `OPERATOR_CDSE_REFRESH_TOKEN`. 2FA 계정은 공식 2FA 인증에서 발급받은 refresh token 방식으로 준비한다. 앱이 2FA 코드를 생성/우회하거나 자동 재시도를 반복하지 않는다.
- NASA: `OPERATOR_NASA_USER_TOKEN`, `OPERATOR_NASA_TOKEN_EXPIRES_AT`(제공처가 발급한 만료 시각, Unix UTC 초). 호환되는 LP DAAC 서비스에 승인된 운영 계정의 공식 토큰만 사용한다. 미래61일 초과/비정상/무기한 만료값을 거부한다. 개인 방문자 토큰을 공용 모드로 자동 승격하지 않는다.

`backend/.env` 한 파일을 기존 `scripts/server-env.mjs`로 읽는다. 기존 프로세스 환경이 우선한다. OPERATOR/USGS/CDSE/COPERNICUS/AWS 및 NEXT_PUBLIC 변형은 프런트·worker·빌드에서 제거한다. 브라우저 설정 입력창/토큰 발급 API를 추가하지 않았다. `.env`/`.private`는 기존 버전 관리 제외 규칙을 따른다.

## 토큰·폐기·관리자 조치

운영자 저장소는 **Windows 사용자 범위 DPAPI + 해당 사용자/SYSTEM 디렉터리 ACL + SQLite FULL 동기화**다. 토큰/refresh만 암호화 저장하고 비밀번호/Application Token은 서버 설정에서만 읽는다. 설정 fingerprint·revision·세대·상태·사용량·사용한 seed hash를 기록한다. 평문 key 파일이나 브라우저 토큰을 만들지 않는다.

유효 토큰은 재사용하고 만료5분 전 또는 인증 실패시1회만 갱신한다(USGS 세션은 보수적으로15분 재발급). 갱신 요청 전에 renewing을 커밋하고 성공 후 새 grant를 원자적으로 교체한다. 갱신 경합은 asyncio lock과 DB 세대 비교로 막는다. 프로세스가 중단되거나 저장 실패로 결과가 불명확하면 재연결 필요로 차단한다. **자동으로 환경의 초기 토큰을 다시 쓰지 않는다.** 폐기·만료·권한 거부·2FA·provider/timeout/준비 중 상태는 분리된다.

새 회전 토큰을 도입할 때 `_REVISION`을 올리고 실제로 새 토큰을 설정해야 한다. 이미 사용/폐기한 token seed는 revision만 올려 재사용할 수 없고, 이전 revision으로의 롤백도 거부한다. User Token 만료값만 바꿔 수명을 연장할 수 없다. USGS Application Token/비밀번호처럼 세션 갱신으로 폐기되지 않는 정적 자격은 **로컬 폐기 전 상태에 한해** 관리자가 높은 revision으로 명시 재시도할 수 있다. 로컬 폐기 후에는 새 자격이 필요하다. 저장소/seed 이력을 삭제하면 이 보장은 유지되지 않으므로 보관·백업·복구도 함께 보호해야 한다.

관리자 전용 서버 콘솔: `node scripts/operator-admin.mjs status nasa` 또는 `usgs`/`cdse`. 같은 안전한 서버 env 로더를 쓰고 누락 이름·상태만 출력한다. `node scripts/operator-admin.mjs revoke-local nasa`는 **초기화된 로컬 grant를 차단**하며 제공처 전체 토큰 철회가 아니다. 미초기화 상태를 폐기 성공으로 표시하지 않는다. 원격 폐기는 해당 공식 계정에서 운영자가 별도로 수행한다. HTTP 관리자 설정/비밀 조회/토큰 반납 API는 없다. 방문자는 일반화된 접근 상태만 보고, 운영자 모드에서는 NASA 개인 연결/갱신 버튼이 사라진다. 개인 OAuth와 저장소는 그대로 분리·보존한다.

## 전송·캐시·배포 제한

- canonical 제공처/컬렉션/Item/Asset key만 입력한다. 임의 URL은 스키마에서 거부한다. 파일 호스트/경로·DNS 공인 주소·리다이렉트·파일명을 확인하고 제공처 호스트 집합도 분리한다. 인증 헤더는 최초 허용 인증 호스트에만 붙이고 교차 호스트 이동 시 영구 제거한다. 서명 URL은 내부에서만 사용한다.
- 미리보기8MiB·16MP·이미지 전체 디코딩, 원본256MiB·형식 magic/전체 수신 확인. 원본 전체는 명시 다운로드에서만 받으며 접근 확인의 Range1024바이트를 다운로드 완료로 표시하지 않는다. 다운로드 receipt는 방문자·Asset·운영자 세대에 묶이고120초, 회전/폐기 후 재확인한다.
- 앱 전체 전송 동시2, 제공처 인증 전송 동시2, 같은 원본 동시 요청은 busy로 거부한다. 운영자 미리보기는 동시 작업2/16MiB/60초 메모리 캐시와 요청 합치기. 원본은 영속 캐시하지 않고 제한된 임시 spool을 닫으면 삭제한다. 개별 검사60초, 외부 파일35초, 클라이언트 스트림120초. 사용자별512MiB/시간, 운영자 공개 경로는 제공처별 추가512MiB/시간(프로세스), 인증 경로는 공유 DB 기준 제공처별1GiB/시간·120회/시간 상한(인증/M2M 요청과 파일 작업을 보수적으로 합산).
- upstream httpx/httpcore 로그는 URL/헤더를 출력하지 않도록 필터링한다. uvicorn receipt/OAuth code 로그 마스킹도 유지한다. 브라우저·링크 목록·manifest에는 운영자 토큰이나 서명 URL을 반환하지 않는다.
- **현재 지원 실행은 Windows 단일 worker다.** WEB_CONCURRENCY/OPERATOR_WORKERS가1이 아니거나 uvicorn multiprocessing worker이면 운영자 인증을 거부한다. 서로 다른 프로세스의 DB 갱신 claim/CAS·한도는 검사하지만 미디어 세션/receipt/캐시는 아직 프로세스 메모리이므로 다중 worker 웹 운영 완료가 아니다. Linux/다중 서버/공개 규모용 secret manager·공유 receipt/캐시·분산 admission·관리자 인증 운영은 후속 작업이며 배포 승인도 아니다.

---

# 운영자 계정으로 제공하는 자료 접근 — 요청 및 설계

2026-11-02 사용자 요청: 운영자가 제공처마다 인증 정보를 한 번 서버에 등록하고, 방문자는 제공처 로그인 없이 미리보기·원본 다운로드를 이용한다. **아래는 구현할 계약이며 현재 코드에서 지원되는 설정/API라고 표현하지 않는다.** 기존 사용자별 NASA OAuth 저장 기능만으로 이 모드가 구현된 것은 아니다.

## 원하는 사용자 흐름

방문자 → 우리 웹사이트의 자료 API → 서버의 제공처별 인증·캐시 → 공식 제공처 → 서버의 이미지/파일 응답.

방문자는 검색과 장면 선택을 하고 미리보기를 바로 본다. 원본은 다운로드를 누르면 받는다. 제공처 계정 연결·로그인 유지·토큰 발급은 운영자가 처리한다. 서버 인증 실패는 방문자에게 로그인 버튼을 요구하는 대신 자료 접근 불가/운영자 확인 필요 상태로 표시한다. 사이트 접속만으로 대용량 원본을 자동 다운로드하지 않는다.

## 제공처별 준비와 근거

| 경로 | 운영자가 준비할 것 | 자동화 범위와 조건 |
|---|---|---|
| Earth Search 공개 카탈로그/공개 S2 Asset | 공개 경로에는 별도 로그인 불필요 | STAC 검색과 실제 Asset 접근 조건을 구분 |
| Landsat/USGS | USGS 계정명, ERS에서 발급한 M2M Application Token, M2M 이용 권한 | 공식 login-token으로 API 세션을 발급하고 정확한 제품/개별 파일 다운로드를 연결. M2M API 키를 LandsatLook 로그인 cookie나 일반 Bearer로 사용하지 않음 |
| AWS Landsat requester-pays | 별도 AWS 권한과 운영자의 비용 선택 | USGS 로그인만으로 접근되지 않음. 비용 동의 없이 활성화하지 않고 무료 대체 경로와 구분 |
| Copernicus Data Space | 다운로드 API에 적합한 운영 계정의 공식 인증 | 실제 access/refresh 응답을 사용. 2FA·철회·재인증은 제공처 정책 준수. Sentinel Hub용 client credentials가 모든 CDSE 다운로드에 통한다고 가정하지 않음 |
| NASA Earthdata/LP DAAC | 운영 계정의 User Token 또는 승인된 공식 서버 인증, 대상 DAAC 앱 승인/권한 | 실제 User Token 발급·만료·renew 응답으로 관리. 기존 방문자별 OAuth refresh와 별개의 어댑터. 운영자 계정으로 자료를 수집할 권한과 방문자에게 재제공할 권한을 각각 확인 |

사용자 브라우저의 로그인 cookie나 저장된 비밀번호를 추출하지 않는다. 개발자가 이미 웹사이트에 로그인한 사실만으로 서버에 API 인증이 생기지 않는다. 현재 확인 시 `backend/.env`에는 EARTHDATA_/USGS_/CDSE_/COPERNICUS_/AWS_/OPERATOR_ 설정 이름이 없었다. 값은 출력하지 않았다. 실제 자격증명은 채팅이나 예시 파일에 넣지 않는다.

공식 근거(2026-11-02 조회):

- [Earth Search README](https://github.com/Element84/earth-search/blob/main/README.md): 공개 카탈로그와 제품별 원본 저장 위치.
- [USGS Application Token](https://www.usgs.gov/media/files/m2m-application-token-documentation): ERS Application Token과 M2M login-token. 실제 파일 매핑·계정 권한은 별도 검증 필요.
- [USGS Landsat 공개 이용](https://www.usgs.gov/faqs/are-landsat-data-cloud-still-considered-be-within-public-domain), [AWS Registry](https://registry.opendata.aws/usgs-landsat/): Landsat 공개 이용/재배포와 requester-pays 저장소 구분.
- [CDSE Token](https://documentation.dataspace.copernicus.eu/APIs/Token.html): access/refresh, 재발급과 2FA. [CDSE 이용 조건](https://dataspace.copernicus.eu/terms-and-conditions): Sentinel 데이터의 공개 이용과 웹포털의 다른 콘텐츠를 구분하고 계정·사용 한도를 준수.
- [NASA 자동 자료 접근](https://wiki.earthdata.nasa.gov/spaces/EL/pages/65801191/Earthdata+Login+Home), [User Token](https://urs.earthdata.nasa.gov/documentation/for_users/user_token): 자동 스크립트용 사용자 접근과 토큰 발급·갱신. 이 문서는 개인 계정 권한을 모든 익명 방문자에게 위임해도 된다는 포괄 허가로 해석하지 않는다. 대상 데이터의 공개 재제공 조건이 확인되지 않으면 활성화하지 않음.

## 서버 계약

- 방문자 인증과 독립된 운영자 credential manager를 두고 제공처마다 토큰 수명·회전·오류·정지를 관리한다. 웹사이트 방문마다 새 로그인하지 않고 유효 토큰을 재사용하고 필요할 때만 갱신한다.
- 최초 설정은 서버 전용 환경 설정/secret manager로 입력한다. 회전한 토큰은 암호화 저장소가 권위 있는 최신값으로 보관한다. 재시작 때 최초의 이미 폐기된 seed token으로 되돌아가지 않도록 설정 fingerprint와 버전을 검증한다. 비밀번호·토큰을 프런트·URL·로그·manifest에 반환하지 않는다.
- 기존 로컬 Windows DPAPI 저장은 개인 브라우저 세션용이다. 공개 운영용 자격 저장·다중 worker 잠금·회전·폐기는 별도 설계/검증한다. 기존 public callback 차단을 조용히 제거하지 않는다.
- 제공처·컬렉션·제품·권한·재제공 조건을 검토한 allowlist를 사용한다. 현재 연결된 3개 제공처·4개 컬렉션 밖의 모든 위성을 자동 활성화하지 않는다. 제한/비공개 데이터는 공용 운영자 계정으로 익명 공개하지 않는다.
- 이미지는 가시성 기반 자동 처리, 원본은 명시 요청만 처리한다. 같은 제품/파일의 제한된 캐시, 중복 요청 합치기, 제공처 전체/방문자별 동시성·전송 상한을 둔다. 방문자가 임의 URL로 운영자 권한을 사용하게 하지 않는다. 인증 헤더는 해당 제공처의 허용된 호스트에만 보낸다.
- 원본 제품·버전·촬영일·Asset 식별을 유지하고 다른 처리 버전이나 비슷한 장면을 같은 파일로 대체하지 않는다. 미리보기·분석 원본·픽셀 QA를 구분한다.
- 제공처 장애·quota·만료/철회·2FA 요구 시 운영자에게 필요한 조치를 알린다. 모든 방문자의 사용량은 운영 계정·서버의 전체 한도로 집계한다. 무기한 인증이나 무제한 무료 사용을 보장하지 않는다.

## 다음 구현 단계와 검증

1. 제공처별 운영 자격/대상 제품의 공개 재제공 조건을 확인하고 운영자 모드 설정 계약을 확정한다. 비용이 있는 AWS 경로는 별도 명시 선택.
2. 운영자 인증 manager, USGS/CDSE/NASA 어댑터, 암호화 회전·폐기와 캐시/전송 상한을 구현한다. 실제 값 없이도 설정 누락·권한 거부·갱신 race 등을 테스트할 수 있지만 실제 연결 성공으로 표현하지 않는다.
3. 기존 미디어 API에 운영자 모드를 연결하고 방문자용 제공처 로그인 UI를 제거하거나 운영자 모드에서 숨긴다. 관리자에게만 설정·재연결 조치를 제공한다.
4. 방문자별 제공처 로그인 cookie가 전혀 없는 새 브라우저에서 공개 허용 제품별 자동 미리보기·명시 다운로드를 확인한다. 실제 토큰 갱신·서버 재시작·다중 worker·한도·철회와 비밀 유출도 검증한다.

현재 코드 변경·새 계정 발급·자격증명 저장·공개 접근 권한 확장·유료 요청은 수행하지 않았다. 이 설계를 구현 완료나 공개 배포 승인으로 취급하지 않는다.

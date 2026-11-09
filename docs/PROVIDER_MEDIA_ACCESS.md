# 제공처별 미리보기·원본 접근 (2026-10-30)

기존 검색·추천·장면/밴드 선택·비교 상태를 재사용한다. 미리보기 이미지, 분석용 원본 파일, 실제 AOI 픽셀 QA는 별개다. 계정 연결이나 HTTP HEAD 200을 다운로드 완료로 표시하지 않는다.

## 실제 장면 추적

| 구분 | Landsat 9 L2SP | Suomi NPP VIIRS VNP09GA.002 |
|---|---|---|
| canonical Item | Earth Search `LC09_L2SP_116035_20250723_02_T1` | CMR `G3626199201-LPCLOUD` |
| 메타데이터 | HTTP 200 | HTTP 200 |
| 미리보기 | `thumbnail`·`reduced_resolution_browse` 존재. S3 requester-pays여서 기존 HTTP 이미지 필터에서 제외됨 | 공개 browse 존재. LP DAAC → 허용된 CloudFront 경로 |
| 별도 공식 대응 | 전체 제품 `LC09_L2SP_116035_20250723_20250726_02_T1`의 USGS SR/ST Item 200. 플랫폼·촬영 UTC 시각·L2SP·Collection 02·scene ID·전체 제품 ID·파일명을 대조 | 원래 CMR granule의 browse/data 링크만 사용 |
| 실제 이미지 접근 | 정확히 대응한 USGS 썸네일/큰 browse는 GET에 **302 USGS 로그인 이동**. 익명 미리보기 성공 아님 | 전체 JPEG **70,963바이트** GET 200, rasterio/GDAL 디코딩 및 브라우저 표시 성공 |
| 원본 | 대응한 USGS `lwir11`도 GET 302 로그인. 원래 S3 비용 조건은 별도로 유지 | 익명 원본 요청은 Earthdata 로그인으로 이동. 앱에서 원본 확인 시 **earthdata_not_configured**. 사용자 인증 원본 전송 미실행 |

Landsat의 촬영일은 2025-07-23T02:11:18.464892Z이고 처리일은 제품 ID의 20250726이다. 축약된 Earth Search ID만으로 다른 처리 버전 파일을 같은 파일로 연결하지 않는다. USGS 대응은 같은 파일명이며 양쪽에 checksum이 있으면 불일치도 거부한다. ST/SR 하위 Item은 동일 L2SP 제품의 서로 다른 Asset 묶음이며 서로 다른 밴드를 같은 파일로 간주하지 않는다.

현재 표본은 익명 접근 가능한 원본 RGB 밴드가 없어 RGB 재생성하지 않았다. Earthdata 토큰은 Earth Search requester-pays S3나 USGS 로그인을 해결하지 않는다. 해당 파일을 받을 수 없을 때 EarthExplorer의 Data Sets → Landsat Collection 2 Level-2 → Landsat 8-9 OLI/TIRS → Additional Criteria의 Landsat Product Identifier에 **전체 제품 ID**를 넣는 경로를 표시한다. 가짜 장면 전용 링크는 만들지 않는다.

[USGS Full Resolution Browse 안내](https://www.usgs.gov/landsat-missions/landsat-collection-2-full-resolution-browse-images)의 FRB는 Level-1 제품에서 생성된다. 이를 같은 촬영이라는 이유만으로 선택한 L2SP의 동일 제품/파일로 대체하지 않는다.

공식 Item:

- [Earth Search Landsat Item](https://earth-search.aws.element84.com/v1/collections/landsat-c2-l2/items/LC09_L2SP_116035_20250723_02_T1)
- [USGS ST Item](https://landsatlook.usgs.gov/stac-server/collections/landsat-c2l2-st/items/LC09_L2SP_116035_20250723_20250726_02_T1_ST)
- [USGS SR Item](https://landsatlook.usgs.gov/stac-server/collections/landsat-c2l2-sr/items/LC09_L2SP_116035_20250723_20250726_02_T1_SR)
- [CMR granule 조회](https://cmr.earthdata.nasa.gov/search/granules.json?concept_id=G3626199201-LPCLOUD&page_size=1)

## 화면과 API

현재 제공처 장면의 이미지는 외부 링크를 브라우저가 따라가게 하지 않는다. 화면에 보이는 미리보기의 공유 큐 → canonical Item 재조회 → 제공처 이미지 전체 수신·형식 확인 → 세션에 귀속된 같은 출처 이미지 응답 순서다. 최초 접근 확인 버튼은 필요 없고 실패 시 명시 재시도를 제공한다. 이미지 숨기기/보기와 별도 미리보기 이미지 저장을 지원한다. 자동 로드는 미리보기에만 적용하고 원본 전체 다운로드는 사용자 동작으로 유지한다. 세션·receipt 만료 복구와 한도는 [자동 미리보기](AUTOMATIC_PREVIEWS.md)를 따른다.

기존 밴드 선택에서 선택한 Asset key로 `선택 원본 접근 확인`을 한다. 실제 GET Range와 파일 헤더를 확인한 뒤에만 `원본 다운로드`가 활성화된다. 이 단계는 전체 다운로드 성공이 아니다. 다운로드 시 canonical Item·Asset을 다시 조회하고 전체 파일을 제한된 임시 파일로 수신한 뒤 브라우저로 보낸다. UI는 전체 바이트 수신과 브라우저 저장 결과 확인을 구분한다. 원본 헤더 검사는 TIFF/HDF/JP2/NetCDF/ZIP 식별 수준이며 checksum 검증·과학적 픽셀 QA가 아니다.

| 같은 출처 웹 API | 역할 |
|---|---|
| `GET /api/media/session` | HttpOnly 미디어 세션 준비 |
| `POST /api/media/inspect` | provider/collection/Item ID, Asset key(최대 8개), preview 여부만 받음. URL 입력 금지 |
| `GET /api/media/previews/{receipt}` | 검증한 이미지 바이트. `?download=1`은 browse 저장 |
| `GET /api/media/downloads/{receipt}` | canonical 재검증 후 원본 전체 전송 |
| `GET /api/media/downloads/{receipt}/status` | 서버 응답 스트림 완료 여부. 브라우저 디스크 저장 보증 아님 |
| `GET /api/auth/earthdata/status` | 설정/연결/재연결/갱신 가능 상태만 반환 |
| `POST /api/auth/earthdata/refresh` | 현재 사용자 세션의 만료 임박 상태 확인·필요한 OAuth 갱신 |

Asset 누락, 형식 미지원, 404/410 자료 없음, requester-pays, USGS 로그인, NASA 앱 설정 없음/사용자 연결 없음/재연결 필요, 401, 일반 403, 명시된 EULA·앱 승인 요구, 잘못된 HTML·파일, 네트워크/시간/크기 상한을 분리한다. 일반 403만으로 EULA가 원인이라고 단정하지 않는다. 알려진 로그인 호스트로 이동하면 **실제 리다이렉트 상태 코드**를 기록하고 따라가지 않는다.

## OAuth와 운영 제한

기존 authorization-code 연결을 재사용한다. `.env`는 서버 애플리케이션의 `EARTHDATA_CLIENT_ID`, `EARTHDATA_CLIENT_SECRET`, `EARTHDATA_REDIRECT_URI`만 설정한다. 사용자 이름/비밀번호·개인 User Token은 받거나 저장하지 않는다. 기존 OpenAI 설정과 무관하다.

공식 SSO 개요에는 access/refresh token이 언급되지만 **이 프로젝트 계정의 실제 발급 응답은 아직 없다**. 구현은 실제 token 응답에 `refresh_token`이 있을 때만 `/oauth/token`의 OAuth refresh grant를 사용한다. `expires_in` 누락/오류는 추정하지 않고 거부한다. 만료 전 여유는 최대 60초(짧은 lifetime의 1/10)다. 사용자 세션별 잠금으로 중복 갱신을 막고 새 access/refresh grant를 원자적으로 교체한다. 회전 응답에 새 refresh token이 없으면 기존 것을 유지한다. 거부/잘못된 응답은 비밀을 비우고 재연결 필요로 전환한다. 파일 401은 최대 한 번만 갱신/재시도한다. 동시 401은 이미 갱신된 grant를 재사용한다. 로그아웃 중 도착한 갱신은 세션을 되살리지 않는다.

이는 사용자 화면에서 만든 User Token의 `/api/users/renew_token`과 다른 방식이며 그 API를 호출하지 않는다. 실제 OAuth 발급·갱신 허용 여부·앱 승인/EULA·원본 접근 권한은 등록된 앱과 사용자의 실제 응답으로 추가 검증해야 한다. 현재 앱 ID/secret/callback 모두 미설정이며 실제 로그인·갱신·인증 원본 다운로드는 미실행이다.

기본 세션은 **로컬 단일 프로세스 메모리, 최대 8시간**이며 재시작/로그아웃 시 소멸한다. `EARTHDATA_PERSIST_SESSIONS=1`을 명시하면 Windows 사용자 범위 DPAPI 암호화 저장과 최대30일 연결 복원을 지원한다. access token 자체 유효기간을 늘리는 것은 아니다. 폐기 실패·이전 저장소·실제 검증 한계는 [자동 미리보기와 로그인 유지](AUTOMATIC_PREVIEWS.md)를 확인한다. 공개 callback은 코드에서 차단한다. 공개 다중 사용자/다중 worker 운영은 **공유 암호화 세션 저장소, 암호키 관리·회전, 분산 잠금·폐기** 구현 전 지원하지 않는다. 무기한 연결이나 Earthdata 전체 SSO 로그아웃을 보장하지 않는다.

## 보안과 상한

- HTTPS 제공처 호스트·경로를 정확히 허용하고 매 리다이렉트에서 DNS/IP·파일명·목적지를 검사한다. 사설 IP, URL 자격증명, 임의 URL, 다른 파일 리다이렉트를 차단한다. LP DAAC CloudFront는 실제 확인한 단일 호스트와 VNP09GA.002 버킷 경로만 허용한다.
- Bearer는 원래 LP DAAC 호스트에서만 사용하며 호스트가 바뀌면 제거한다. 최종 서명 URL·인증 헤더·토큰을 JSON, 프런트, 링크 저장, manifest에 반환하지 않는다. Uvicorn access 로그의 OAuth callback query와 receipt 경로를 가린다.
- 원본 최대 **256 MiB**, 미리보기 **8 MiB / 1,600만 픽셀**, 메타데이터 **2 MiB**, 전역 동시 전송 **2개**, 미디어 세션별 **512 MiB/시간**, HTTP 전체 **35초**, 한 inspect/다운로드 준비 **60초**, 브라우저 응답 **120초**, 리다이렉트 **4회**. 자동 원본 다운로드·재시도 반복 없음.
- receipt는 **120초**, 사용자 미디어 세션에 귀속. 비공개 자료는 추가로 Earthdata 세션과 연결되어 다른 사용자·로그아웃 후 사용할 수 없다. 이미지 캐시는 합계 **32 MiB/100건** 한도. 원본 임시 spool은 완료/오류/취소 시 닫는다. 파일을 영구 저장하지 않는다.
- 같은 장면·Asset 선택이 바뀌거나 계정이 해제되면 프런트 요청을 취소하고 늦은 응답을 폐기한다. AOI·기간·추천·분석 엔진은 바꾸지 않는다.

## 공식 근거와 미검증

- [Element 84 Earth Search README](https://github.com/Element84/earth-search/blob/main/README.md): 검색과 Asset 저장·접근은 별개.
- [USGS Landsat STAC](https://www.usgs.gov/landsat-missions/spatiotemporal-asset-catalog-stac): 공식 카탈로그와 제품 확인. 실제 위 Item/Asset HTTP 응답도 별도로 확인했다.
- [Earthdata SSO 개요](https://urs.earthdata.nasa.gov/documentation/for_users/sso_process_overview), [OAuth2](https://urs.earthdata.nasa.gov/documentation/for_users/oauth2), [앱 승인](https://urs.earthdata.nasa.gov/documentation/for_users/what_is_app_auth), [User Token](https://urs.earthdata.nasa.gov/documentation/for_users/user_token): OAuth와 별도 User Token·앱 승인을 구분한다.

가짜 자격증명·모의 응답 테스트는 실제 사용자 권한/원본 수신/refresh 발급의 근거가 아니다. 최신 명령·종료 코드·실행 주소는 [TEST_REPORT](../TEST_REPORT.md)를 따른다. USGS 인증 연동, requester-pays 비용 동의/인증, 공개 운영용 저장소, VIIRS 픽셀 QA/NDVI는 구현하지 않았다.

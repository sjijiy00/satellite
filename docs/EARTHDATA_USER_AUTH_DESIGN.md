# Earthdata 사용자별 인증·VIIRS 원본 접근 설계

> **2026-10-30 최신 구현:** 아래의 초기 단계 기록 중 “갱신/원본 전송 미구현”, “최대 1시간”, 예정 API 이름은 이전 상태다. 현재는 기존 OAuth 연결에 세션별 잠금·조건부 refresh·최대 8시간 로컬 세션, canonical Asset 검사·제한된 원본 전송을 추가했다. 실제 사용자 토큰 발급·갱신·인증 원본 접근은 앱 설정이 없어 미검증이다. 현재 API·상한·실제 제공처 응답은 [PROVIDER_MEDIA_ACCESS.md](PROVIDER_MEDIA_ACCESS.md)를 우선한다. 공개 callback은 공유 암호화 저장소 구현 전 차단한다. 기존 초기 설계와 작업 기록은 아래에 보존한다.

## 초기 설계·당시 구현 기록

상태: **로컬 단일 프로세스용 사용자별 계정 연결 구현, NASA 실연결·인증 다운로드 미검증/미구현** (2026-10-30). OAuth 앱 등록 정보는 아직 설정하지 않았다. 사용자가 Earthdata에서 발급한 개인 User Token을 운영자 공용 `backend/.env`에 넣지 않는다.

현재 `backend/app/earthdata_auth.py`와 `main.py`에 OAuth 시작·콜백·상태·사이트 연결 해제 API가 있다. 브라우저에는 `Earthdata 계정 연결` 한 버튼만 보이며, 앱 등록 정보가 없으면 `연결 준비 중`으로 표시된다. `scripts/server-env.mjs`는 **앱의** `EARTHDATA_CLIENT_ID`, `EARTHDATA_CLIENT_SECRET`, `EARTHDATA_REDIRECT_URI`만 백엔드로 전달한다. 개인 User Token 변수는 추가하지 않았다. 지금의 임시 토큰 저장은 서버 메모리·단일 프로세스 전용이며 재시작 시 사라진다. 공개 서비스의 다중 사용자 운영에는 아래의 공유 암호화 세션 저장소와 추가 검증이 필요하다.

## 현재 코드와 목표

- 현재 `backend/app/cmr.py`는 공개 CMR에서 `VNP09GA.002` granule을 검색한다. `backend/app/metadata.py`와 `assets.py`는 인증 필요 파일의 `direct_url`을 비우고 접근 미검증으로 표시한다. `frontend/src/components/AssetDownloads.tsx`는 로그인 또는 다운로드 프록시가 없다.
- `frontend/next.config.ts`는 같은 출처 `/api/*`를 FastAPI에 전달한다. `scripts/server-env.mjs`는 AI와 Earthdata **앱 등록 변수만** `backend/.env`에서 읽으며, OAuth 사용자 세션은 현재 서버 메모리에만 둔다. 기존 검색·추천·S2 처리 동작은 그대로 둔다.
- 목표는 **각 사용자가 자신의 Earthdata 계정으로 승인한 범위 안에서** NASA 원본을 받는 것이다. Earthdata 로그인 상태와 파일별 접근 성공은 별개로 표시한다. 이 설계의 첫 대상은 현재 연결된 NASA CMR `viirs-vnp09ga-002`의 실제 HDF5 granule 한 종류다. 모든 NASA 제품, VIIRS 픽셀 분석, 다른 제공처의 인증까지 자동 지원한다는 뜻이 아니다.

## 인증 흐름

1. 운영자는 Earthdata Login에 **Satellite Insight AI 애플리케이션**을 등록하고, 배포 도메인의 정확한 callback URL, client ID/secret 및 대상 다운로드 서비스의 연동·이용약관 조건을 확인한다. 공식 자료에 따르면 redirect URL은 정확히 등록되어야 한다. 앱 등록 자격·승인 여부를 확인하기 전에는 연결 완료라고 표시하지 않는다.
2. 사용자가 `Earthdata 계정 연결`을 누른다. 백엔드가 짧게 유효한 무작위 `state`를 서버 세션에 저장하고 Earthdata의 authorization-code 로그인으로 이동시킨다. PKCE 사용은 해당 앱 유형에서 Earthdata가 지원하는지 등록 과정에서 확인한 후 적용한다.
3. 사용자는 **Earthdata 도메인에서** 로그인하고 앱 권한 및 필요한 EULA에 직접 동의한다. 사이트는 Earthdata 비밀번호나 화면에서 생성한 User Token을 입력받지 않는다.
4. 등록한 callback에서 `state`·만료·1회 사용을 검사한 뒤 서버가 HTTPS로 authorization code를 교환한다. 실패/거부/취소는 구분하고 브라우저에 코드·토큰을 돌려주지 않는다.
5. **현재 로컬 구현:** 서버는 임의의 세션 ID를 발급하고 `HttpOnly`, `SameSite=Lax` 쿠키를 둔다. HTTPS callback이면 `Secure` 쿠키, 로컬 HTTP 테스트 주소면 비보안 쿠키다. 접근 토큰은 브라우저에 보내지 않고 서버 메모리에서 세션별로 최대 1시간 보관하며 만료/로그아웃 때 제거한다. refresh token 저장·자동 갱신, Earthdata 전체 SSO 로그아웃은 아직 구현하지 않았다.
6. **공개 서비스 구현 조건:** 비밀을 담는 저장소는 다중 프로세스가 공유하는 암호화 저장소와 키 관리, 세션 만료·갱신·폐기가 필요하다. 현재 단일 프로세스 메모리 구현을 그대로 공개 배포하지 않는다. 실제 Earthdata 응답과 등록 조건을 확인해 수명을 확정한다.

## 원본 파일 흐름

1. 기존 공개 `/search`는 로그인 없이 유지한다. 인증 필요 Asset에는 `로그인 필요 / 연결됨 / 권한 또는 이용약관 필요 / 접근 실패 / 다운로드 가능 확인`을 구분한다. 로그인됨만으로 다운로드 성공을 표시하지 않는다.
2. 사용자가 현재 검색 결과의 VIIRS 파일을 선택하면 백엔드에 **provider + collection + Item ID + Asset key**만 보낸다. 임의 URL을 받지 않는다. 서버는 CMR canonical granule을 다시 조회하고 등록된 data link와 사용자 세션 권한을 확인한다. 선택 결과가 바뀌면 이전 접근 결과를 새 결과로 재사용하지 않는다.
3. 실제 파일 요청은 해당 사용자의 OAuth 자격으로 서버에서 수행한다. 대상 HTTPS 호스트와 모든 리다이렉트 대상의 허용 목록·DNS/IP를 확인해 내부망/로컬 접근과 인증 헤더의 다른 호스트 유출을 막는다. 크기·시간·동시 전송·총 전송량 상한을 둔다. 인증 실패, EULA 미승인, 파일 부재, 서버 시간 초과를 각각 반환한다.
4. 다운로드는 인증 헤더를 브라우저에 전달하지 않는 제한된 서버 스트림으로 제공한다. 파일 전체 전송과 형식·크기 확인이 성공하기 전에는 `다운로드 완료`라고 표시하지 않는다. 파일이 상한을 넘으면 공식 제공처에서 해당 사용자로 직접 받는 경로를 안내한다. HDF5 원본을 GeoTIFF나 AOI 추출본으로 오표기하지 않는다.
5. 로그·분석 manifest·링크 목록에는 access/refresh token, 쿠키, authorization code, 인증 query, 최종 서명 URL을 저장하지 않는다. 파일 메타데이터에 로그인 사용자 식별자가 꼭 필요하지 않다면 기록하지 않는다.

## 코드 변경 지점 (구현 단계)

| 위치 | 작업 |
|---|---|
| `backend/app/earthdata_auth.py` (구현) | OAuth 시작/callback, 1회용 state, 코드 교환, 단일 프로세스 세션·만료·사이트 연결 해제. 갱신은 후속 |
| `backend/app/session_store.py` (후속) | 공개 배포용 공유 암호화 세션, 다중 프로세스·동시 접근 |
| `backend/app/earthdata_download.py` (신규) | CMR Item 재조회, Asset 식별, 도메인/redirect 검증, 제한된 파일 스트림 |
| `backend/app/main.py` (연결 구현) | `/auth/earthdata/start`, `/auth/earthdata/callback`, `/auth/earthdata/status`, `/auth/earthdata/logout`. 다운로드 ticket API는 후속 |
| `scripts/server-env.mjs`, `backend/.env.example` (구현) | 서버에만 client ID/secret, 정확한 callback URL 전달. 사용자별 token 변수 없음 |
| `frontend/src/components/EarthdataConnection.tsx` (구현) | 한 버튼의 연결·상태·사이트 연결 해제. 파일 다운로드 UI는 후속 |
| `frontend/src/components/AssetDownloads.tsx`, `frontend/src/lib/types.ts` (후속) | NASA 장면에 파일별 권한 오류·확인 버튼과 실제 다운로드 제공. 기존 밴드 선택/링크 저장 유지 |
| `backend/tests/test_earthdata_auth.py`, `frontend/tests/earthdata-auth.spec.ts` (구현), `backend/tests/test_earthdata_download.py` (후속) | 현재 로그인 fixture 테스트와 후속 파일 접근 테스트 구분 |

`GET /auth/earthdata/status`는 `configured`, `connected`, `reauthorization_required` 같은 상태만 반환하며 토큰·이메일·프로필을 반환하지 않는다. `POST /downloads/earthdata/prepare`는 실제 선택된 파일의 사용 가능 여부를 확인하되 `download_verified`는 파일 전송 성공과 구별한다. 여러 사용자에게 같은 작업/파일 ticket이 공유되지 않도록 세션과 연결한다. 외부 파일을 브라우저 URL로 받아 내려주는 일반 프록시를 만들지 않는다.

## 구현·검증 순서와 완료 조건

1. **등록 가능성 확인:** Earthdata My Applications 또는 Earthdata 지원팀에서 앱 등록·redirect·client 자격, LP DAAC 파일에 OAuth 사용자 토큰을 쓰는 조건, EULA 및 앱 승인 요건 확인. 이 단계에서 막히면 로그인 버튼을 활성화하지 않는다. 이미 만든 개인 User Token은 이 OAuth 흐름의 앱 자격증명이 아니다.
2. **인증/세션:** 테스트용 가짜 토큰 fixture로 state 불일치·재사용, callback 취소, 만료/갱신/로그아웃, A 사용자 쿠키로 B 사용자 파일 접근 차단, CSRF·쿠키 정책 검사. 실제 사용자 비밀로 fixture를 만들지 않는다.
3. **원본 접근:** 실제 등록 앱·테스트 계정으로 `VNP09GA.002`의 작은 표본 1건을 검색→동의→권한 확인→제한된 전송→파일 형식/크기 확인까지 검증한다. redirect/401/403/404/시간 초과/초과 용량/연결 중단을 별도 검사한다. HEAD 200이나 CMR 결과만으로 다운로드 성공으로 기록하지 않는다.
4. **기존 기능 회귀:** `backend` pytest, `node.exe scripts/frontend-check.mjs typecheck`, production build, 기존 E2E와 신규 브라우저 연결→선택→다운로드/로그아웃 테스트를 **최신 변경 뒤** 실행한다. 실제 NASA 계정·앱 등록이 없으면 실연결은 `미실행`으로 적는다.

## 공식 근거와 확인할 사항

- [Earthdata OAuth2 개요](https://urs.earthdata.nasa.gov/documentation/for_users/oauth2), [SSO 절차](https://urs.earthdata.nasa.gov/documentation/for_users/sso_process_overview): 브라우저 redirect, 서버의 authorization code 교환, access/refresh token 및 애플리케이션 세션.
- [애플리케이션 승인과 EULA](https://urs.earthdata.nasa.gov/documentation/for_users/what_is_app_auth), [Earthdata FAQ](https://urs.earthdata.nasa.gov/documentation/faq): 최초 승인, 등록한 정확한 redirect URL.
- [User Token 관리](https://urs.earthdata.nasa.gov/documentation/for_users/user_token): 사용자가 화면에서 생성하는 User Token은 별도 방식이며 만료가 있다. **이 설계의 공용 서버 비밀이나 사용자 로그인 입력값이 아니다.**

OAuth 앱의 등록 가능 여부, PKCE 지원/요구, 승인된 앱 토큰의 LP DAAC 파일 접근 방식, callback 도메인·HTTPS, EULA는 실제 등록과 테스트로 최종 확인한다. 확인되지 않은 항목을 구현 완료 또는 다운로드 보장으로 표시하지 않는다.

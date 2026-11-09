# 자동 미리보기와 로컬 로그인 연결 유지

현재 연결된 Earth Search(Sentinel-2 L2A/Landsat C2 L2), Copernicus(Sentinel-1 GRD), NASA CMR(VNP09GA.002)의 검색 결과를 기존 단일 화면에서 사용한다. 검색 지원, 미리보기 제공 여부, 원본 접근 권한, 픽셀 처리 지원은 서로 다르다. 모든 사이트의 모든 위성이 연결된 상태라는 뜻은 아니다.

## 자동 표시

화면에 보이는 제공처 미리보기는 별도 접근 확인 버튼 없이 불러온다. 목록·선택 상세·비교의 동일 장면 요청을 합치고, 동시에 최대 두 개를 처리한다. 화면 밖 대기 요청과 구독자가 사라진 요청을 취소한다. 실패한 이미지는 상태와 재시도 동작을 표시한다. 이미지 숨기기를 유지하며 자동 로그인 화면 이동은 하지 않는다.

자동 확인은 미리보기 이미지에만 적용한다. 원본 밴드 검사와 전체 파일 다운로드는 사용자가 선택한 경우에만 실행한다. 제공처 browse는 분석 원본이나 실제 AOI 품질 검사 결과가 아니다.

미디어 세션 준비는 유효시간이 있는 단일 요청으로 합친다. 서버 재시작·세션 만료로 `MEDIA_SESSION_REQUIRED`가 오면 세션을 다시 준비하고 한 번 재시도한다. 미리보기 receipt 접근 실패도 가시 상태에서 한 번만 복구한다. 반복 실패·권한 거부·제공처 상한을 무한 재시도하지 않는다. 장면과 계정이 바뀌면 이전 요청·캐시를 무효화한다.

## 한 번 연결한 NASA 로그인

`backend/.env`에는 서버 애플리케이션 등록 설정을 둔다. 기존 사용자 키나 모델 설정을 바꾸지 않는다.

```dotenv
EARTHDATA_CLIENT_ID=
EARTHDATA_CLIENT_SECRET=
EARTHDATA_REDIRECT_URI=http://127.0.0.1:3000/api/auth/earthdata/callback
EARTHDATA_PERSIST_SESSIONS=1
```

빈 값은 변수 이름 안내다. NASA Earthdata에서 등록한 앱과 정확히 일치하는 callback이 필요하다. 개인 로그인은 제공처의 공식 OAuth 화면에서 한 번 진행한다. 앱이 사용자의 NASA 비밀번호·브라우저 로그인 cookie를 `.env`로 복사하지 않는다. 공식적으로 발급받은 access/refresh token을 사용자별로 서버에 보관한다.

`EARTHDATA_PERSIST_SESSIONS=1`을 명시한 Windows 로컬 단일 프로세스에서 현재 OS 사용자의 DPAPI로 grant를 암호화하고, 제한된 디렉터리의 SQLite에 저장한다. 브라우저 세션 ID는 해시로 저장한다. 같은 Windows 사용자와 동일 앱 설정으로 서버를 다시 시작하면 남은 유효기간 안의 연결을 복원한다. 암호화·복호화·저장 실패는 평문 저장이나 연결 성공으로 대체하지 않는다. 미설정 또는 `EARTHDATA_PERSIST_SESSIONS=0`은 기본 메모리 모드이며 서버 재시작 후 연결이 사라진다. 비 Windows 환경의 영속 모드는 지원하지 않는다.

영속 연결의 최대 보관 기간은 30일이고, access token의 수명은 제공처가 실제 발급한 값이다. 실제 refresh token이 있을 때만 필요한 시점에 갱신한다. 제공처 철회·만료·권한 변경이나 앱 설정 변경, cookie 삭제, 저장소 손상 때는 다시 연결해야 한다. 연결을 무기한 보장하지 않는다. 사이트 연결 해제는 이 사이트에 저장된 grant 폐기이며 NASA 전체 계정 로그아웃이나 모든 제공처 토큰 폐기와 같지 않다.

디스크 폐기가 확인되지 않으면 성공으로 표시하지 않고 다시 시도하도록 알린다. 폐기 기록이 실제로 저장·검증된 경우에만 재시작 뒤 해당 연결 복원을 차단할 수 있다. 모든 지속 저장 쓰기와 제공처 철회가 함께 불가능한 상태에서는 영구 폐기를 보장할 수 없으며, 운영자가 제공처에서 권한을 철회하고 저장소를 격리·복구해야 한다. 이전 형식 저장소를 자동으로 새 연결로 복원하지 않는다. 실제 사용자의 기존 저장소는 서버를 종료하고 제공처 철회를 확인한 뒤 `backend/.private/earthdata/`를 접근 제한된 별도 위치에 격리하고 새 저장소로 다시 연결한다. 기존 파일을 단순히 삭제했다고 제공처 토큰까지 철회됐다고 판단하지 않는다.

공개 웹서비스·다중 worker·서로 다른 OS 사용자의 공유 운영은 지원하지 않는다. 공개 callback은 계속 차단한다. 공개 운영에는 서비스용 암호화 저장소·사용자별 권한·공유 폐기와 분산 잠금이 별도로 필요하다. 로컬 DPAPI 저장소 파일이나 `.env`를 프런트 정적 파일/외부 사이트에 올리지 않는다.

## 제공처마다 다른 접근 조건

| 제공처 | 현재 연결 | 추가 조건 |
|---|---|---|
| Earth Search Sentinel-2 | 공개 검색·허용된 공개 browse/Asset | 해당 Item의 실제 파일 상태·전송 상한 확인 |
| Earth Search/USGS Landsat | 검색·정확한 USGS 제품/파일 대응·접근 진단 | USGS 로그인과 AWS requester-pays는 NASA 로그인과 별개. USGS 인증 다운로드는 아직 미연결 |
| Copernicus Sentinel-1 | 공개 검색·허용된 미리보기 진단 | CDSE 원본 인증·다운로드는 아직 미연결 |
| NASA CMR/LP DAAC | 공개 검색/browse·Earthdata OAuth·제한된 원본 전송 | 등록 앱, 사용자 연결, 제공처 승인/EULA, 대상 파일 권한과 실제 발급·갱신 검증 필요 |

`GET /api/auth/providers/status`는 현재 제공처별 연결 범위를 비밀 없이 알려준다. 공개 이미지가 있으면 로그인 없이 표시하고, 보호된 이미지에는 실제 필요한 연결 상태를 표시한다. 하나의 비밀번호나 토큰으로 모든 제공처의 로그인을 대체하지 않는다. 새 제공처는 공식 카탈로그·정확한 제품 식별·browse/Asset 경로·허용 목적지·인증 어댑터·권한·전송 상한을 각각 검증한 뒤 등록해야 한다.

USGS M2M의 application token은 공식 API용 자격이며 LandsatLook의 로그인 cookie와 같다고 가정하지 않는다. CDSE는 자체 access/refresh 흐름을 사용한다. 계정/권한이 준비되지 않은 경로를 인증 완료나 다운로드 성공으로 표시하지 않는다.

## Kakao 설정

Kakao 키는 지명 검색 전용이며 위성 제공처 로그인과 별개다. `GEOCODER_ENABLED=1`과 `KAKAO_LOCAL_REST_API_KEY`는 고정된 서버 `backend/.env`에서 읽는다. 설정을 바꾼 뒤에는 해당 프로젝트 서버 재시작이 필요하다. `/api/places/config`의 `ready=true`는 설정 인식이고, 실제 인증된 지명 조회 성공은 `/api/places/search`의 별도 결과로 확인한다. 중심점은 지도 이동만 하며 AOI를 자동 생성하지 않는다.

## 검증과 공식 근거

최신 실행 명령·종료 코드·실연결/fixture 구분과 미검증 사항은 [TEST_REPORT](../TEST_REPORT.md)를 따른다. 실제 제공처 계정이 없는 테스트의 OAuth 성공·refresh·원본 전송은 합성 검증이며 사용자 권한이나 구름 아래 픽셀 정확도의 근거가 아니다.

- [NASA 공식 SSO 흐름](https://urs.earthdata.nasa.gov/documentation/for_users/sso_process_overview): 사용자 공식 로그인과 서버 token 교환·refresh 구분.
- [USGS 공식 application token 안내](https://www.usgs.gov/media/files/m2m-application-token-documentation): ERS/M2M `login-token` 조건.
- [CDSE 공식 토큰 안내](https://documentation.dataspace.copernicus.eu/APIs/Token.html): 제공처 고유 access token과 재인증.
- [기존 제공처 실제 접근 기록](PROVIDER_MEDIA_ACCESS.md): canonical Item·파일 대응과 실검증 한계.

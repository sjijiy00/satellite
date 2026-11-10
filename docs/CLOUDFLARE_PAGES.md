# Cloudflare Pages GitHub 배포

2026-11-10: `frontend`에서 `npm run build`를 실행하면 `out` 정적 파일과 Pages API 전달 Worker를 생성합니다. Next.js 서버는 Pages에서 실행하지 않습니다. 기존 `npm run dev`와 `start.cmd`는 그대로 사용합니다. Node 서버용 배포는 `npm run build:server` 이후 `npm start`를 사용하세요.

## Pages 입력값

| 항목 | 값 |
|---|---|
| Framework preset | Next.js (Static HTML Export) |
| Root directory | `frontend` |
| Build command | `npm run build` |
| Build output directory | `out` |
| Production branch | `main` |

프리셋의 기본 명령어 대신 반드시 `npm run build`를 입력하세요. 지도 worker 준비, 정적 내보내기, Pages Worker 포함까지 수행합니다. `out`을 Git에 올리지 않고 변경된 소스를 커밋·푸시합니다. 배포 로그에서 새 커밋인지 확인하세요. 이전 `acf09cd` 커밋은 이 변경을 포함하지 않습니다.

## 연결 설정

| 위치 | 환경변수 | 용도 |
|---|---|---|
| Cloudflare Pages Production의 런타임 변수 | `API_BASE_URL` | Lightsail 백엔드의 공개 HTTPS 기본 주소. `/health`, `/docs`는 제외. 백엔드가 루트 경로로 서비스된다면 `/api`도 붙이지 않음 |
| Lightsail 백엔드 프로세스 환경 | `PUBLIC_APP_ORIGIN` | 배포한 사이트의 정확한 HTTPS origin. 예: `https://your-project.pages.dev` (끝 `/`, 경로 제외) |

Pages의 환경변수 변경 후 재배포하세요. Preview 배포도 사용하려면 별도 환경 설정이 필요하며, Production 백엔드는 등록한 정확한 사이트만 허용합니다. `backend/.env`를 사용하는 서버 시작 방식이라면 여기에 `PUBLIC_APP_ORIGIN`을 추가하고 재시작하세요. systemd를 사용한다면 해당 서비스의 EnvironmentFile 등 실제 프로세스에 환경변수를 전달하는 위치에 설정합니다. 이 작업에서는 실제 `.env`, 서버 주소, 도메인을 변경하지 않았습니다.

Lightsail 공개 IP만 있으면 아직 HTTPS 주소가 아닐 수 있습니다. 실제 접속 포트, TLS 인증서와 도메인, 방화벽 상태를 확인해야 합니다. 이 프록시는 HTTPS 백엔드만 허용합니다. 주소가 없거나 잘못되면 API는 `503 API_NOT_CONFIGURED`, 연결에 실패하면 `502 API_UNREACHABLE`을 반환하며 가짜 결과로 대체하지 않습니다. 주소 없이도 정적 화면 빌드는 가능합니다.

브라우저 → 같은 Pages 사이트의 `/api/*` → Pages Function → Lightsail 순서로 요청합니다. `/api` 접두사는 제거하고 전달합니다. 쿠키, 요청 본문, 쿼리, 다운로드 스트림과 오류 상태를 보존하고 API는 캐시하지 않습니다. 브라우저가 백엔드로 직접 호출하지 않아 CORS 추가는 필요하지 않습니다. `PUBLIC_APP_ORIGIN`은 CORS가 아니라 기존 미디어/작업 요청의 사이트 확인을 위한 설정입니다. 해당 Python 코드도 Lightsail에 반영해야 합니다.

OpenAI/Kakao/제공처 비밀 키는 Lightsail에만 둡니다. Pages 또는 `NEXT_PUBLIC_*`에 복사하지 않습니다. `API_BASE_URL`은 Pages Worker 런타임에서 읽으며 프론트엔드 번들에 삽입하지 않습니다. `out/_worker.js`는 Pages advanced mode로 배포되고 `_routes.json`은 `/api`와 `/api/*`만 Function으로 보냅니다.

## 기존 제한 유지

- 공개 Earthdata 사용자 OAuth는 기존 코드에서 비활성입니다. 이번 변경으로 활성화하지 않습니다.
- 운영자 자격증명 저장은 기존 Windows 단일 worker 제한을 유지합니다. Linux Lightsail에서 운영자 인증 자료 기능까지 검증·활성화한 것이 아닙니다. 운영자 모드를 별도로 사용하는 경우 기존 `OPERATOR_PUBLIC_ORIGIN` 정책을 따릅니다.
- 장시간 처리, 실제 원본 전송, 제공처 접근은 Lightsail/Cloudflare 제한과 기존 엔진 상태에 따릅니다. 로컬 fixture 테스트가 운영 환경에서의 실제 자료 성공을 뜻하지 않습니다.

## 배포 후 확인

1. 새 커밋 빌드가 완료되고 `out`을 찾는지 확인합니다.
2. 사이트의 `/` 및 `/processing`을 직접 열어 확인합니다.
3. `https://사이트주소/api/health`가 백엔드 JSON을 반환하는지 확인합니다.
4. 직접 조건 입력 검색 → 지도 촬영 범위 → 장면 선택 → 분석 화면 이동을 확인합니다.
5. 미디어 403이 나면 Lightsail 코드 반영과 `PUBLIC_APP_ORIGIN` 설정·서버 재시작을 확인합니다.

공식 자료: [Pages advanced mode](https://developers.cloudflare.com/pages/functions/advanced-mode/), [정적 Next.js 배포](https://developers.cloudflare.com/pages/framework-guides/nextjs/deploy-a-static-nextjs-site/).

# MyUNi

화면 아래를 돌아다니는 우리 학교 친구를 키우고, 대학별로 육성 점수를 겨루는 Windows/Mac 데스크톱 게임.

설계와 결정 사항은 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) 에 있습니다.

## 구성

| 경로 | 내용 |
| --- | --- |
| `apps/desktop` | Electron 앱 (투명 펫 창, 로그인 창, 게임 루프) |
| `apps/server` | Fastify API 서버 + PostgreSQL 마이그레이션 |
| `packages/shared` | 경험치 규칙, 시즌 키, API 스키마 (클라/서버 공용) |

## 개발 환경

필요한 것: Node.js 22 이상, PostgreSQL 16

```bash
npm install
```

### 서버

```bash
cp apps/server/.env.example apps/server/.env
```

`.env` 의 값을 채운 뒤:

```bash
cd apps/server && set -a && . ./.env && set +a && npm run migrate && npm run dev
```

### 데스크톱 앱

서버가 `http://localhost:3000` 에서 돌고 있어야 합니다. 다른 주소면 `MYUNI_API_URL` 로 지정합니다.

```bash
npm run dev:desktop
```

캐릭터 위에 마우스를 올리면 이름과 레벨이 보이고, 오른쪽 클릭으로 메뉴(먹이 주기, 놀아 주기, 종료)를 엽니다.

### 검사와 테스트

```bash
npm run typecheck
```

서버 통합 테스트는 비어 있는 테스트용 DB 가 필요합니다 (테스트가 스키마를 지우고 다시 만듭니다).

```bash
TEST_DATABASE_URL=postgres://user:pass@localhost:5432/myuni_test npm test
```

### 배포판 빌드

```bash
MAIN_VITE_API_URL=https://api.example.com npm run dist:win -w @myuni/desktop
```

macOS 는 `dist:mac`. 각 OS 에서 빌드해야 합니다.

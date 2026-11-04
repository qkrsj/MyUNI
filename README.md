# MyUNi

화면 아래를 돌아다니는 우리 학교 친구를 키우고, 대학별로 육성 점수를 겨루는 Windows/Mac 데스크톱 게임.

설계와 결정 사항은 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) 에 있습니다.

## 구성

| 폴더 | 내용 |
| --- | --- |
| `client/` | 데스크톱 앱 (Python + tkinter). `run.pyw` 로 실행 |
| `server/` | API 서버 (FastAPI + SQLite) |
| `common/` | 클라이언트와 서버가 같이 쓰는 규칙 · 시즌 계산 · 버전 |
| `deploy/` | AWS Lightsail 배포 (docker compose + Caddy HTTPS), 백업 |
| `tools/` | 배포판 빌드 (PyInstaller) |

## 개발

Python 3.12 를 씁니다.

### 서버

도커로 띄우기 (http://127.0.0.1:8787):

```bash
docker compose up -d --build
```

도커 없이 띄우기:

```bash
pip install -r server/requirements.txt
```

```bash
cd server && uvicorn app.main:app --port 8787 --reload
```

### 클라이언트

```bash
pip install -r client/requirements.txt
```

```bash
python client/run.pyw
```

기본으로 `http://127.0.0.1:8787` 서버에 붙습니다. 다른 서버는 `MYUNI_SERVER=https://... python client/run.pyw`.

캐릭터를 누르면 반응하고, 오른쪽 클릭(맥은 Control+클릭)으로 메뉴(먹이 주기 · 놀아 주기 · 랭킹 · 종료)를 엽니다.
트레이(윈도우) · 메뉴 막대(맥) 아이콘에서도 같은 메뉴를 쓸 수 있습니다.

### 검사

```bash
pip install pytest httpx
```

```bash
python -m pytest common client
```

```bash
cd server && python -m pytest
```

## 배포

- **서버**: Lightsail 인스턴스에서 `bash deploy/setup-aws.sh` (자세한 순서는 스크립트 맨 위 주석).
  올린 뒤에는 `bash deploy/backup.sh --install` 로 매일 백업을 켭니다.
- **클라이언트**: `common/version.py` 의 버전을 올리고 같은 이름의 태그를 밀면
  GitHub Actions 가 윈도우 · 맥 배포판을 만들어 릴리스에 올립니다.

```bash
git tag v0.1.0 && git push origin v0.1.0
```

배포판이 붙을 서버 주소는 저장소 Settings > Secrets and variables > Actions > Variables 의 `MYUNI_SERVER_URL` 입니다.

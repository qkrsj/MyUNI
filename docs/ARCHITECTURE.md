# MyUNi 설계 문서

화면 아래를 돌아다니는 오리지널 캐릭터를 키우고, 대학별로 육성 점수를 겨루는 Windows/Mac 데스크톱 게임.

## 확정된 결정

| 항목 | 결정 |
| --- | --- |
| 컨셉 | 학교 상징 동물 + 상징색 기반의 **오리지널** 캐릭터 키우기 (학교 공식 마스코트 이미지는 쓰지 않음) |
| 표시 방식 | 1차: 화면 아래를 걸어 다니는 투명 창. 나중에 위젯/트레이 등으로 교체 가능 |
| 경쟁 단위 | 대학별. 학과별은 2차에 학교 내부 랭킹으로 추가 |
| 가입 | 닉네임 + 비밀번호. 대학 인증 없음. 학교는 목록에서 선택 (선택 안 함도 가능) |
| 플랫폼 | Windows + macOS |
| 시즌 | 주간. 월요일 00:00 (KST) 초기화 |
| 개인 랭킹 | 닉네임 옆에 학교 표시 |
| 대결 | 초기에는 제외 |
| 인프라 | AWS Lightsail (서버 + DB 한 대) |

## 기술 스택

구조와 운영 방식은 [poketdesktop](https://github.com/rudtjr1106/poketdesktop) 을 참고했다 (코드 · 그림 · 데이터는 가져오지 않음).

| 영역 | 선택 |
| --- | --- |
| 데스크톱 | Python 3.12 + tkinter, Pillow(도트), pystray(윈도우 트레이), pyobjc(맥 투명 창 · 메뉴 막대) |
| 서버 | FastAPI + uvicorn |
| DB | SQLite 파일 하나 (서버와 같은 인스턴스, 도커 볼륨) |
| 공용 | `common/` - 경험치 규칙, 날짜/시즌 키, 버전 |
| 배포 | Lightsail + docker compose + Caddy(HTTPS 자동) |
| 배포판 | PyInstaller, GitHub Actions 가 태그마다 윈도우 · 맥에서 빌드 |

## 폴더

```
client/
  run.pyw              실행 파일 (pythonw 로 콘솔 없이)
  myuni/
    app.py             시작점. 표시 층 · 게임 로직 · 서버 통신을 잇는다
    overlay.py         [표시 층] 화면 아래를 걷는 캐릭터
    sprites.py         [표시 층] 캐릭터 도트 (지금은 도형으로 찍는 임시 도트)
    game.py            [게임 로직] 활동 시간, 자리 비움, 상호작용 횟수 - 창 없이 검사 가능
    api.py             [서버 통신]
    device.py          기기 식별값 (해시)
    ui_login.py        로그인 · 가입 창
    ui_ranking.py      랭킹 창
    ui_common.py       말풍선, 메뉴, 백그라운드 작업(Worker)
    tray.py            트레이 (윈도우) / tray_mac.py 메뉴 막대 (맥)
    platform_os.py     이 OS 에 맞는 구현을 고른다
    platform_base.py   플랫폼 계약 + 기본 구현
    platform_win.py    윈도우 (투명색, 뮤텍스, MachineGuid, GetLastInputInfo)
    platform_mac.py    맥 (CALayer, flock, IOPlatformUUID, CGEventSource)
  test_game.py
server/
  app/main.py          계정 · 학교 경로
  app/progress.py      경험치 동기화 (서버 판정)
  app/rankings.py      주간 랭킹
  app/auth.py          비밀번호, 토큰, 기기 해시, 로그인 시도 제한
  app/db.py            SQLite 스키마와 헬퍼
  data/schools.json    학교 목록 (서버가 켜질 때 DB 에 맞춘다)
  test_server.py
common/                rules.py, timekeys.py, version.py
deploy/                docker-compose.prod.yml, Caddyfile, setup-aws.sh, backup.sh, update.sh
tools/build.py         PyInstaller 배포판
```

## 표시 층

- 캐릭터 크기만 한 테두리 없는 투명 창(78x84)을 작업표시줄 바로 위에서 옮긴다. 화면 전체를 덮지 않으므로
  캐릭터가 없는 자리는 원래대로 클릭된다.
- **윈도우**: `-transparentcolor` 로 특정 색을 뚫는다. 그 색 자리는 클릭도 통과한다. 투명색 방식은 반투명이
  없으므로 도트는 안티앨리어싱 없이 작은 칸에 찍고 3배로 키운다.
- **맥**: Tk 은 투명 위젯에 그림을 못 그려서 CALayer 로 그린다. 투명한 자리도 클릭을 먹으므로 커서 밑에
  도트가 있는지 보고 `ignoresMouseEvents` 를 켜고 끈다. 메뉴는 NSMenu 대신 Tk 으로 그린다
  (NSMenu 가 열린 동안 Tk 타이머가 돌면 죽는다).
- 왼쪽 클릭: 반응. 오른쪽 클릭(맥은 Control+클릭도): 메뉴. 마우스를 올리면 이름 · 레벨 · 오늘 경험치.
- 표시 방식을 바꿀 때는 `overlay.py` 만 교체한다. 게임 로직과는 `set_view()`, `say()`, `react()` 로만 이야기한다.

## 게임 로직

- 1분마다 OS 유휴 시간을 보고 5분 미만이면 활동 1분을 쌓는다. 자리 비움이면 캐릭터가 잔다.
- 5분마다 (상호작용 직후에는 2초 뒤) 쌓인 것을 서버로 보낸다. 실패하면 다음에 다시 보낸다.
- 네트워크는 Tk 스레드 밖(Worker)에서 돈다. 서버가 느려도 캐릭터가 멈추지 않는다.
- 저장해 둔 로그인 정보로 바로 켜지고, 서버 확인은 뒤에서 한다 (오프라인이어도 켜진다).
- **경험치 판정은 서버가 한다.** 클라이언트는 "활동 몇 분, 먹이 몇 번" 만 보낸다.

### 서버 판정 (`POST /api/progress/sync`)

1. 활동 시간 ≤ 마지막 동기화 뒤 실제로 흐른 시간 × 1.1 (+1분)
2. 상호작용별 하루 횟수 제한
3. 하루 경험치 상한
4. 레벨/진화 단계 다시 계산
5. 랭킹 반영 계정이면 주간 개인 점수에, 학교가 있으면 주간 학교 점수에 더한다

## API

| 메서드 | 경로 | 인증 | 설명 |
| --- | --- | --- | --- |
| GET | `/api/health` | | 상태 확인 |
| GET | `/api/version` | | 서버 버전 (클라이언트가 새 버전 안내에 쓴다) |
| GET | `/api/schools` | | 학교 목록 |
| POST | `/api/signup` | | 가입 `{nickname, password, school_id, device_id}` |
| POST | `/api/login` | | 로그인 `{nickname, password, device_id}` |
| POST | `/api/logout` | O | 이 토큰 끝내기 |
| GET | `/api/me` | O | 내 정보, 캐릭터, 오늘 진행도 |
| PUT | `/api/me/school` | O | 학교 바꾸기 (30일에 한 번) |
| POST | `/api/progress/sync` | O | 활동/상호작용 동기화 |
| GET | `/api/rankings/schools?week=` | | 주간 학교 랭킹 |
| GET | `/api/rankings/users?week=&school_id=` | | 주간 개인 랭킹 (school_id 를 주면 학교 안) |

오류는 `{"detail": {"code": ..., "message": ...}}`. 클라이언트는 message 를 그대로 보여준다.

## 어뷰징 방지

- **기기 식별**: Windows `MachineGuid`, macOS `IOPlatformUUID`.
  - 클라이언트: `SHA-256("myuni-device:" + 원본)` 만 보낸다. 원본은 기기 밖으로 나가지 않는다.
  - 서버: 거기에 `HMAC-SHA256(device_salt)` 를 한 번 더 걸어 저장한다. salt 는 환경 변수 또는 DB 옆 파일.
- **기기당 랭킹 계정 1개**: 한 기기에서 여러 계정 로그인은 된다. 그 기기에서 처음 가입/로그인한 계정만
  랭킹에 들어가고, 나머지 계정은 키우기만 된다 (메뉴에 안내가 뜬다).
- **가입 고지**: 가입 화면에 "중복 계정 방지용으로만 사용, 원본은 저장하지 않음" 문구.
- **학교 변경**: 30일에 한 번. 가입 때 학교를 고르면 그때부터 30일. 안 골랐다면 첫 선택은 바로 된다.
- **학교 목록**: 선택식. 서버는 `schools` 에 있는 id 만 받는다.
- **IP 제한 없음** (공용망 문제).
- 비밀번호 PBKDF2-HMAC-SHA256 (20만 번). 토큰은 해시만 저장. 같은 닉네임으로 10분에 10번 틀리면 잠시 막는다.
  없는 닉네임으로 로그인해도 같은 시간이 걸린다.

## 데이터 모델

`server/app/db.py` 의 SCHEMA. 처음 계획에서 추가한 것:

| 테이블/컬럼 | 이유 |
| --- | --- |
| `sessions(token_hash, user_id, device_hash, ...)` | 로그인 토큰 (해시만) |
| `devices(device_hash, ranked_user_id)` | 기기당 랭킹 계정 1개 |
| `characters.last_synced_at` | 활동 시간을 실제로 흐른 시간 안으로 자른다 |
| `daily_progress(user_id, day, exp, interactions)` | 하루 상한 / 횟수 제한 |
| `user_weekly_scores(week, user_id, school_id, score)` | 주간 개인 랭킹, 학교 내부 랭킹 |

- 주차 키는 ISO 주차 (`2026-W45`). 시즌 초기화는 새 주차 키로 쌓는 방식이라 배치가 필요 없고 지난 기록도 남는다.
- 주 중간에 학교를 바꾸면 그 전에 얻은 점수는 이전 학교에 남는다.

## 미정 규칙 (지금은 임시값)

전부 `common/rules.py` 에 있다. 바꾸면 클라이언트와 서버에 같이 적용된다.

| 항목 | 임시값 | 메모 |
| --- | --- | --- |
| 활동 경험치 | 1분에 1 | 자리 비움 기준 5분 |
| 먹이 주기 | +5, 하루 5번 | |
| 놀아 주기 | +8, 하루 5번 | |
| 일일 미션 | 없음 | |
| 하루 상한 | 300 | 약 5시간 사용 기준 |
| 레벨 곡선 | 다음 레벨까지 `50 × lv^1.4` | |
| 진화 | 알(1) → 아기(3) → 청소년(10) → 어른(25) | 단계 수/조건 미정 |
| 학교 점수 | 랭킹 계정들의 주간 경험치 **합계** | 큰 학교가 유리함. 평균이나 상위 N명 합계도 검토 |
| 개인 랭킹 점수 | 주간 경험치 | 레벨/총 경험치는 매주 초기화와 맞지 않아 주간 획득량으로 둠 |

## 배포 (AWS)

```
[데스크톱 앱] --HTTPS--> [Lightsail 인스턴스 (서울)]
                           ├─ Caddy (80/443, 인증서 자동)
                           └─ myuni-server (FastAPI) ── /data/myuni.db (도커 볼륨)
                                                         └─ backup.sh → ~/myuni-backups (+ S3 선택)
```

- 처음 한 번: `deploy/setup-aws.sh` (스왑, 도커, 도메인, 띄우기).
- 코드 갱신: 서버 안에서 `bash deploy/update.sh` (백업 → pull → 다시 빌드 → 확인).
- 백업: `bash deploy/backup.sh --install` 로 매일. `MYUNI_BACKUP_S3` 를 주면 S3 에도 올린다.
  `device_salt` 도 같이 뜬다 - 잃으면 기기 판정이 전부 새로 시작된다.
- 배포판은 서명하지 않았다. 윈도우는 SmartScreen, 맥은 "확인되지 않은 개발자" 경고가 뜬다.
  공개 배포 전에 코드 서명(윈도우 인증서, Apple Developer ID + 공증)을 붙여야 한다.

## 다음 할 일

- [ ] 학교 목록 · 상징 동물 · 상징색 정리 (공식 자료로 검증)
- [ ] 캐릭터 아트 (학교별 스프라이트 시트)와 진화 단계별 디자인
- [ ] 학교 바꾸기 화면 (서버 API 는 있음)
- [ ] 일일 미션
- [ ] 자동 시작 (윈도우 시작 프로그램, 맥 로그인 항목)
- [ ] 자동 업데이트 (지금은 새 버전이 나오면 안내만 함)
- [ ] 다중 모니터 (지금은 주 모니터만)
- [ ] 코드 서명
- [ ] 실제 윈도우 · 맥에서 투명 창 · 클릭 통과 · 트레이 확인 (리눅스 가상 화면에서만 돌려 봄)

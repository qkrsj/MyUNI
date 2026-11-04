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
| 인프라 | AWS |

## 기술 스택

| 영역 | 선택 | 이유 |
| --- | --- | --- |
| 데스크톱 | Electron + TypeScript (electron-vite) | 투명 창 + 클릭 통과(`setIgnoreMouseEvents(…, { forward: true })`)가 Win/Mac 모두 안정적 |
| 서버 | Node.js + Fastify + TypeScript | 클라이언트와 규칙 코드를 공유 |
| DB | PostgreSQL | 랭킹 집계, 트랜잭션, 제약 조건 |
| 공용 | `packages/shared` | 경험치 규칙, 날짜/시즌 키, API 스키마(zod)를 클라/서버가 같이 사용 |

## 구조

```
apps/desktop      Electron 앱
  src/main          [게임 로직 + 서버 통신] 게임 루프, 자리 비움 감지, 동기화, 기기 ID, 세션
  src/preload       렌더러에 노출하는 최소 API (window.myuni)
  src/renderer      [표시 층] 펫 창(canvas), 로그인 창
apps/server       Fastify API + SQL 마이그레이션
packages/shared   규칙, 시간 키, API 타입/스키마
```

### 표시 층

- 주 모니터 작업 영역 맨 아래에 높이 140px 의 투명·테두리 없는 창을 띄우고, 기본은 클릭 통과.
- 렌더러가 마우스 위치를 받아(forward) 캐릭터 위에 있을 때만 클릭을 받도록 전환.
- 왼쪽 클릭: 반응(경험치 없음). 오른쪽 클릭: 메뉴 (먹이 주기, 놀아 주기, 로그아웃, 종료).
- 캐릭터 그림은 `renderer/sprite.ts` 의 `drawPet()` 하나로 모여 있다. 지금은 도형으로 그린 임시 그림이고,
  학교별 스프라이트 시트(`schools.sprite_set`)가 생기면 같은 시그니처로 교체한다.
- 표시 방식을 바꿀 때는 `main/windows.ts` 와 `renderer/pet.*` 만 교체하면 된다. 게임 로직은 `PetView` / `PetEvent` 로만 통신한다.

### 게임 로직

- 1분마다 OS 유휴 시간(`powerMonitor.getSystemIdleTime()`)을 확인해, 5분 미만이면 활동 1분으로 적립. 자리 비움이면 캐릭터가 잠든다.
- 5분마다 (상호작용 직후에는 2초 뒤) 적립분을 서버로 보낸다. 실패하면 다음에 다시 보낸다.
- **경험치 계산은 서버가 최종 판정**한다. 클라이언트는 "활동 몇 분, 먹이 몇 번"만 보낸다.

### 서버 판정 (`POST /progress/sync`)

1. 활동 시간 ≤ 마지막 동기화 이후 실제 경과 시간 × 1.1 (+1분)
2. 상호작용별 하루 횟수 제한
3. 하루 경험치 상한
4. 레벨/진화 단계 재계산
5. 랭킹 반영 계정이면 주간 개인 점수, 학교가 있으면 주간 학교 점수에 더함

## API

| 메서드 | 경로 | 인증 | 설명 |
| --- | --- | --- | --- |
| GET | `/health` | | 상태 확인 |
| GET | `/schools` | | 학교 목록 |
| POST | `/auth/signup` | | 가입 `{ nickname, password, schoolId, deviceId }` |
| POST | `/auth/login` | | 로그인 `{ nickname, password, deviceId }` |
| GET | `/me` | O | 내 정보, 캐릭터, 오늘 진행도 |
| PUT | `/me/school` | O | 학교 변경 (30일에 1번) |
| POST | `/progress/sync` | O | 활동/상호작용 동기화 |
| GET | `/rankings/schools?week=` | | 주간 학교 랭킹 |
| GET | `/rankings/users?week=&schoolId=` | | 주간 개인 랭킹 (schoolId 주면 학교 내부) |

인증은 JWT (30일). 데스크톱 앱은 토큰을 OS 키체인(`safeStorage`)으로 암호화해 저장한다.

## 어뷰징 방지

- **기기 식별**: Windows `MachineGuid`, macOS `IOPlatformUUID`.
  - 클라이언트: `SHA-256("myuni-device:" + 원본)` 만 서버로 보낸다. 원본은 기기 밖으로 나가지 않는다.
  - 서버: 여기에 `HMAC-SHA256(DEVICE_HASH_SALT)` 를 한 번 더 걸어 저장한다. DB 가 유출돼도 salt 없이는 대조할 수 없다.
- **기기당 랭킹 계정 1개**: 한 기기에서 여러 계정 로그인은 허용. `devices` 테이블에 그 기기에서 처음 가입/로그인한 계정이 랭킹 반영 계정으로 기록된다. 나머지 계정은 키우기는 되지만 랭킹에는 안 들어간다.
- **가입 고지**: 가입 화면에 "중복 계정 방지용으로만 사용" 문구.
- **학교 변경**: 30일에 1번. 가입 때 학교를 고르면 그 시점부터 30일. 가입 때 안 골랐다면 첫 선택은 바로 가능.
- **학교 목록**: 선택식만 허용 (서버가 `schools` 테이블에 있는 ID 만 받음).
- **IP 제한 없음** (공용망 문제).
- 닉네임은 대소문자 구분 없이 유일. 없는 닉네임으로 로그인해도 같은 시간이 걸리도록 더미 해시 비교.

## 데이터 모델

`apps/server/migrations/001_init.sql` 참고. 처음 계획에서 추가한 것:

| 테이블/컬럼 | 이유 |
| --- | --- |
| `devices(device_hash, ranked_user_id)` | 기기당 랭킹 계정 1개 판정 |
| `characters.last_synced_at` | 활동 시간을 실제 경과 시간으로 제한 |
| `daily_progress(user_id, day, exp, interactions)` | 하루 상한 / 횟수 제한 |
| `user_weekly_scores(week, user_id, school_id, score)` | 주간 개인 랭킹, 학교 내부 랭킹 |

- 주차 키는 ISO 주차 문자열 (`2026-W45`). 시즌 초기화는 테이블을 비우는 게 아니라 새 주차 키로 쌓는 방식이라 별도 배치가 필요 없고, 지난 시즌 기록도 남는다.
- 주 중간에 학교를 바꾸면 그 전에 얻은 점수는 이전 학교에 남는다.

## 미정 규칙 (현재 임시값)

모두 `packages/shared/src/rules.ts` 의 `RULES` 와 함수에 모여 있다. 값을 바꾸면 클라/서버에 같이 적용된다.

| 항목 | 임시값 | 메모 |
| --- | --- | --- |
| 활동 경험치 | 1분당 1 | 자리 비움 기준 5분 |
| 먹이 주기 | +5, 하루 5번 | |
| 놀아 주기 | +8, 하루 5번 | |
| 일일 미션 | 미구현 | |
| 하루 상한 | 300 | 약 5시간 사용 기준 |
| 레벨 곡선 | 다음 레벨까지 `50 × lv^1.4` | |
| 진화 | 알(1) → 아기(3) → 청소년(10) → 성체(25) | 단계 수/조건 미정 |
| 학교 점수 | 랭킹 계정들의 주간 획득 경험치 **합계** | 큰 학교가 유리함. 평균 또는 상위 N명 합계도 검토 필요 |
| 개인 랭킹 점수 | 주간 획득 경험치 | 레벨/총 경험치는 매주 초기화와 맞지 않아 주간 획득량으로 둠 |

## AWS 배포 계획 (예정)

```
[데스크톱 앱] ──HTTPS──> [ALB 또는 App Runner] ──> [ECS Fargate: apps/server 컨테이너]
                                                      │
                                                      ├─> [RDS PostgreSQL (프라이빗 서브넷)]
                                                      └─< [Secrets Manager: JWT_SECRET, DEVICE_HASH_SALT, DB 접속 정보]
```

- 컨테이너: `apps/server/Dockerfile` → ECR.
- 처음에는 App Runner(+ VPC 커넥터로 RDS)가 가장 간단하고, 트래픽이 늘면 ECS Fargate + ALB 로.
- 마이그레이션은 배포 파이프라인에서 별도 태스크로 `npm run migrate` 실행.
- 데스크톱 배포판은 `MAIN_VITE_API_URL=https://api.<도메인> npm run dist:win|dist:mac`. 배포용 빌드에는 코드 서명(Windows 인증서, Apple Developer ID + 공증)이 필요하다.
- 인프라 코드(CDK 또는 Terraform)는 다음 단계에서 `infra/` 에 추가.

## 다음 할 일

- [ ] 학교 목록/상징 동물/상징색 데이터 정리 (공식 자료로 검증)
- [ ] 캐릭터 아트 (학교별 스프라이트 시트) 와 진화 단계별 디자인
- [ ] 랭킹 화면 (펫 메뉴 → 랭킹 창)
- [ ] 일일 미션
- [ ] 학교 변경 UI
- [ ] 로그인 시도 횟수 제한 (rate limit)
- [ ] AWS 인프라 코드, 배포 파이프라인
- [ ] 앱 아이콘, 트레이 아이콘, 자동 시작, 자동 업데이트
- [ ] 다중 모니터 대응 (지금은 주 모니터만)

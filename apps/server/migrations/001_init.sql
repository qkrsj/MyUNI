CREATE TABLE schools (
  id               SERIAL PRIMARY KEY,
  name             TEXT NOT NULL UNIQUE,
  animal           TEXT NOT NULL,
  color_primary    TEXT NOT NULL,
  color_secondary  TEXT NOT NULL,
  sprite_set       TEXT NOT NULL
);

CREATE TABLE users (
  id                 BIGSERIAL PRIMARY KEY,
  nickname           TEXT NOT NULL,
  password_hash      TEXT NOT NULL,
  school_id          INT REFERENCES schools(id),
  school_changed_at  TIMESTAMPTZ,
  device_hash        TEXT NOT NULL,          -- 가입 시 기기 (HMAC 값, 원본 아님)
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX users_nickname_lower_idx ON users (lower(nickname));

-- 기기당 랭킹 반영 계정 1개. 그 기기에서 처음 가입/로그인한 계정이 지정된다.
CREATE TABLE devices (
  device_hash     TEXT PRIMARY KEY,
  ranked_user_id  BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX devices_ranked_user_idx ON devices (ranked_user_id);

CREATE TABLE characters (
  user_id          BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  level            INT NOT NULL DEFAULT 1,
  total_exp        BIGINT NOT NULL DEFAULT 0,
  evolution_stage  INT NOT NULL DEFAULT 0,
  last_active_at   TIMESTAMPTZ,
  last_synced_at   TIMESTAMPTZ
);

-- 하루 상한 / 상호작용 횟수 제한 판정용
CREATE TABLE daily_progress (
  user_id       BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  day           DATE NOT NULL,
  exp           INT NOT NULL DEFAULT 0,
  interactions  JSONB NOT NULL DEFAULT '{}',
  PRIMARY KEY (user_id, day)
);

-- 주간 개인 점수 (school_id 는 획득 시점의 소속)
CREATE TABLE user_weekly_scores (
  week       TEXT NOT NULL,
  user_id    BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  school_id  INT REFERENCES schools(id),
  score      BIGINT NOT NULL DEFAULT 0,
  PRIMARY KEY (week, user_id)
);
CREATE INDEX user_weekly_scores_rank_idx ON user_weekly_scores (week, score DESC);

-- 주간 학교 점수 (랭킹 반영 계정만 합산)
CREATE TABLE weekly_scores (
  week       TEXT NOT NULL,
  school_id  INT NOT NULL REFERENCES schools(id),
  score      BIGINT NOT NULL DEFAULT 0,
  PRIMARY KEY (week, school_id)
);
CREATE INDEX weekly_scores_rank_idx ON weekly_scores (week, score DESC);

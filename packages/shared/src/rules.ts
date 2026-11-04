/**
 * 게임 규칙. 클라이언트(표시용 예측)와 서버(최종 판정)가 같은 코드를 쓴다.
 * 수치는 모두 임시값이며 플레이 테스트 후 조정한다. (docs/ARCHITECTURE.md "미정 규칙" 참고)
 */
export const RULES = {
  /** 컴퓨터를 사용 중일 때(자리 비움 아님) 1분당 경험치 */
  activeExpPerMinute: 1,
  /** 이 시간(초) 이상 입력이 없으면 자리 비움으로 본다 */
  idleThresholdSec: 300,
  /** 하루 경험치 상한 (모든 출처 합계) */
  dailyExpCap: 300,
  /** 상호작용별 경험치와 하루 횟수 제한 */
  interactions: {
    feed: { exp: 5, dailyLimit: 5 },
    play: { exp: 8, dailyLimit: 5 },
  },
  /** 서버가 허용하는 활동 시간 = 실제 경과 시간 × 이 값 (타이머 오차 여유) */
  activeMinutesSlack: 1.1,
} as const;

export type InteractionKind = keyof typeof RULES.interactions;
export const INTERACTION_KINDS = Object.keys(RULES.interactions) as InteractionKind[];

// ---------- 레벨 ----------

/** 레벨 n → n+1 에 필요한 경험치 */
export function expToNextLevel(level: number): number {
  return Math.round(50 * Math.pow(level, 1.4));
}

/** 해당 레벨에 도달하기 위한 누적 경험치 */
export function totalExpForLevel(level: number): number {
  let sum = 0;
  for (let l = 1; l < level; l++) sum += expToNextLevel(l);
  return sum;
}

export const MAX_LEVEL = 99;

export function levelFromTotalExp(totalExp: number): number {
  let level = 1;
  let need = expToNextLevel(level);
  let remaining = totalExp;
  while (level < MAX_LEVEL && remaining >= need) {
    remaining -= need;
    level++;
    need = expToNextLevel(level);
  }
  return level;
}

// ---------- 진화 (단계 구성은 미정, 임시) ----------

export const EVOLUTION_STAGES = [
  { stage: 0, key: 'egg', minLevel: 1 },
  { stage: 1, key: 'baby', minLevel: 3 },
  { stage: 2, key: 'teen', minLevel: 10 },
  { stage: 3, key: 'adult', minLevel: 25 },
] as const;

export type EvolutionKey = (typeof EVOLUTION_STAGES)[number]['key'];

export function evolutionStageForLevel(level: number): number {
  let stage = 0;
  for (const s of EVOLUTION_STAGES) if (level >= s.minLevel) stage = s.stage;
  return stage;
}

// ---------- 하루 경험치 계산 ----------

export type InteractionCounts = Record<InteractionKind, number>;

export interface DailyCounters {
  exp: number;
  interactions: InteractionCounts;
}

export interface ProgressGain {
  activeMinutes: number;
  interactions: Partial<InteractionCounts>;
}

export function emptyInteractions(): InteractionCounts {
  return Object.fromEntries(INTERACTION_KINDS.map((k) => [k, 0])) as InteractionCounts;
}

export function emptyDailyCounters(): DailyCounters {
  return { exp: 0, interactions: emptyInteractions() };
}

/**
 * 하루 카운터에 획득량을 적용한다. 횟수 제한과 하루 상한을 넘는 부분은 버린다.
 * 반환값의 granted 가 실제로 지급되는 경험치.
 */
export function applyGain(
  counters: DailyCounters,
  gain: ProgressGain,
): { granted: number; counters: DailyCounters } {
  const interactions = { ...counters.interactions };
  let raw = Math.max(0, Math.floor(gain.activeMinutes)) * RULES.activeExpPerMinute;

  for (const kind of INTERACTION_KINDS) {
    const requested = Math.max(0, Math.floor(gain.interactions[kind] ?? 0));
    const rule = RULES.interactions[kind];
    const allowed = Math.min(requested, Math.max(0, rule.dailyLimit - interactions[kind]));
    interactions[kind] += allowed;
    raw += allowed * rule.exp;
  }

  const granted = Math.min(raw, Math.max(0, RULES.dailyExpCap - counters.exp));
  return { granted, counters: { exp: counters.exp + granted, interactions } };
}

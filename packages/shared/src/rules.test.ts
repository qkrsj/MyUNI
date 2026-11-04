import { describe, expect, it } from 'vitest';
import {
  RULES,
  applyGain,
  emptyDailyCounters,
  evolutionStageForLevel,
  levelFromTotalExp,
  totalExpForLevel,
} from './rules.js';
import { dayKey, weekKey } from './time.js';

describe('level curve', () => {
  it('round-trips total exp and level', () => {
    for (let lv = 1; lv < 40; lv++) {
      expect(levelFromTotalExp(totalExpForLevel(lv))).toBe(lv);
      if (lv > 1) expect(levelFromTotalExp(totalExpForLevel(lv) - 1)).toBe(lv - 1);
    }
  });

  it('maps levels to evolution stages', () => {
    expect(evolutionStageForLevel(1)).toBe(0);
    expect(evolutionStageForLevel(3)).toBe(1);
    expect(evolutionStageForLevel(99)).toBe(3);
  });
});

describe('applyGain', () => {
  it('grants active time and interactions', () => {
    const { granted, counters } = applyGain(emptyDailyCounters(), {
      activeMinutes: 10,
      interactions: { feed: 2 },
    });
    expect(granted).toBe(10 + 2 * RULES.interactions.feed.exp);
    expect(counters.interactions.feed).toBe(2);
  });

  it('enforces per-interaction daily limits', () => {
    const first = applyGain(emptyDailyCounters(), { activeMinutes: 0, interactions: { play: 4 } });
    const second = applyGain(first.counters, { activeMinutes: 0, interactions: { play: 10 } });
    expect(second.counters.interactions.play).toBe(RULES.interactions.play.dailyLimit);
    expect(second.granted).toBe(RULES.interactions.play.exp);
  });

  it('enforces the daily exp cap', () => {
    const { granted, counters } = applyGain(emptyDailyCounters(), { activeMinutes: 10_000, interactions: {} });
    expect(granted).toBe(RULES.dailyExpCap);
    expect(applyGain(counters, { activeMinutes: 5, interactions: { feed: 1 } }).granted).toBe(0);
  });

  it('ignores negative and fractional input', () => {
    expect(applyGain(emptyDailyCounters(), { activeMinutes: -5.5, interactions: { feed: -1 } }).granted).toBe(0);
  });
});

describe('time keys (KST)', () => {
  it('rolls the day at midnight KST', () => {
    expect(dayKey(new Date('2026-11-03T14:59:59Z'))).toBe('2026-11-03');
    expect(dayKey(new Date('2026-11-03T15:00:00Z'))).toBe('2026-11-04');
  });

  it('rolls the season on Monday 00:00 KST', () => {
    // 2026-11-09 is a Monday
    expect(weekKey(new Date('2026-11-08T14:59:59Z'))).toBe('2026-W45');
    expect(weekKey(new Date('2026-11-08T15:00:00Z'))).toBe('2026-W46');
    expect(weekKey(new Date('2027-01-01T00:00:00Z'))).toBe('2026-W53');
  });
});

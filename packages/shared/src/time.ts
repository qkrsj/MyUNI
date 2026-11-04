/**
 * 날짜/시즌 키. 기준 시간대는 한국 시간(KST, UTC+9) 고정.
 * - 하루: 'YYYY-MM-DD'
 * - 시즌(주간): ISO 주차 'YYYY-Www', 월요일 00:00 KST 에 초기화
 */
const KST_OFFSET_MS = 9 * 60 * 60 * 1000;

function toKst(date: Date): Date {
  return new Date(date.getTime() + KST_OFFSET_MS);
}

export function dayKey(date: Date = new Date()): string {
  return toKst(date).toISOString().slice(0, 10);
}

export function weekKey(date: Date = new Date()): string {
  const d = toKst(date);
  // ISO 주차: 목요일이 속한 연도 기준
  const day = d.getUTCDay() || 7;
  const thursday = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate() + 4 - day));
  const yearStart = Date.UTC(thursday.getUTCFullYear(), 0, 1);
  const week = Math.ceil(((thursday.getTime() - yearStart) / 86400000 + 1) / 7);
  return `${thursday.getUTCFullYear()}-W${String(week).padStart(2, '0')}`;
}

export const SCHOOL_CHANGE_COOLDOWN_DAYS = 30;

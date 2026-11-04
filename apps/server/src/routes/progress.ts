import type { FastifyInstance } from 'fastify';
import {
  RULES,
  applyGain,
  dayKey,
  evolutionStageForLevel,
  levelFromTotalExp,
  syncRequest,
  weekKey,
  type SyncResponse,
} from '@myuni/shared';
import { withTx } from '../db.js';
import { HttpError, parse } from '../http.js';
import { loadMe, normalizeInteractions } from '../repo.js';

/**
 * 클라이언트는 마지막 동기화 이후 쌓인 활동 시간/상호작용 횟수만 보낸다.
 * 경험치 계산과 모든 제한(경과 시간, 횟수, 하루 상한)은 서버가 판정한다.
 */
export async function progressRoutes(app: FastifyInstance): Promise<void> {
  const { db } = app;

  app.post('/progress/sync', { onRequest: [app.authenticate] }, async (req): Promise<SyncResponse> => {
    const body = parse(syncRequest, req.body);
    const userId = req.userId;

    return withTx(db, async (tx) => {
      const now = new Date();
      const charRes = await tx.query<{ total_exp: number; last_synced_at: Date | null }>(
        'SELECT total_exp, last_synced_at FROM characters WHERE user_id = $1 FOR UPDATE',
        [userId],
      );
      const character = charRes.rows[0];
      if (!character) throw new HttpError(404, 'not_found', '캐릭터를 찾을 수 없습니다');

      // 지난 동기화 이후 실제로 흐른 시간보다 많이 켜 둘 수는 없다
      const elapsedMin = character.last_synced_at
        ? (now.getTime() - character.last_synced_at.getTime()) / 60_000
        : 0;
      const activeMinutes = Math.min(body.activeMinutes, Math.floor(elapsedMin * RULES.activeMinutesSlack) + 1);

      const day = dayKey(now);
      await tx.query(
        'INSERT INTO daily_progress (user_id, day) VALUES ($1, $2) ON CONFLICT DO NOTHING',
        [userId, day],
      );
      const dailyRes = await tx.query<{ exp: number; interactions: unknown }>(
        'SELECT exp, interactions FROM daily_progress WHERE user_id = $1 AND day = $2 FOR UPDATE',
        [userId, day],
      );
      const daily = dailyRes.rows[0]!;
      const { granted, counters } = applyGain(
        { exp: daily.exp, interactions: normalizeInteractions(daily.interactions) },
        { activeMinutes, interactions: body.interactions },
      );

      await tx.query('UPDATE daily_progress SET exp = $3, interactions = $4 WHERE user_id = $1 AND day = $2', [
        userId,
        day,
        counters.exp,
        JSON.stringify(counters.interactions),
      ]);

      const totalExp = character.total_exp + granted;
      const level = levelFromTotalExp(totalExp);
      const didSomething = activeMinutes > 0 || Object.values(body.interactions).some((n) => (n ?? 0) > 0);
      await tx.query(
        `UPDATE characters
            SET total_exp = $2, level = $3, evolution_stage = $4, last_synced_at = $5,
                last_active_at = CASE WHEN $6 THEN $5 ELSE last_active_at END
          WHERE user_id = $1`,
        [userId, totalExp, level, evolutionStageForLevel(level), now, didSomething],
      );

      if (granted > 0) await addWeeklyScore(tx, userId, weekKey(now), granted);

      return { granted, me: (await loadMe(tx, userId, now))! };
    });
  });
}

/** 랭킹 반영 계정만 주간 개인/학교 점수에 더한다. */
async function addWeeklyScore(
  tx: import('../db.js').Tx,
  userId: number,
  week: string,
  amount: number,
): Promise<void> {
  const { rows } = await tx.query<{ school_id: number | null; ranked: boolean }>(
    `SELECT school_id, EXISTS (SELECT 1 FROM devices WHERE ranked_user_id = $1) AS ranked
       FROM users WHERE id = $1`,
    [userId],
  );
  const user = rows[0];
  if (!user?.ranked) return;

  await tx.query(
    `INSERT INTO user_weekly_scores (week, user_id, school_id, score) VALUES ($1, $2, $3, $4)
     ON CONFLICT (week, user_id)
     DO UPDATE SET score = user_weekly_scores.score + EXCLUDED.score, school_id = EXCLUDED.school_id`,
    [week, userId, user.school_id, amount],
  );
  if (user.school_id !== null) {
    await tx.query(
      `INSERT INTO weekly_scores (week, school_id, score) VALUES ($1, $2, $3)
       ON CONFLICT (week, school_id) DO UPDATE SET score = weekly_scores.score + EXCLUDED.score`,
      [week, user.school_id, amount],
    );
  }
}

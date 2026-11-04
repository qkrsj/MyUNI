import type { FastifyInstance } from 'fastify';
import { z } from 'zod';
import { weekKey, type SchoolRankingEntry, type UserRankingEntry } from '@myuni/shared';
import { parse } from '../http.js';

const weekQuery = z.object({
  week: z
    .string()
    .regex(/^\d{4}-W\d{2}$/)
    .optional(),
  schoolId: z.coerce.number().int().positive().optional(),
});

const LIMIT = 100;

export async function rankingRoutes(app: FastifyInstance): Promise<void> {
  const { db } = app;

  app.get('/rankings/schools', async (req): Promise<{ week: string; entries: SchoolRankingEntry[] }> => {
    const q = parse(weekQuery, req.query);
    const week = q.week ?? weekKey();
    const { rows } = await db.query(
      `SELECT RANK() OVER (ORDER BY ws.score DESC)::int AS rank,
              s.id, s.name, s.animal, ws.score,
              (SELECT count(*)::int FROM user_weekly_scores u
                WHERE u.week = ws.week AND u.school_id = ws.school_id) AS members
         FROM weekly_scores ws
         JOIN schools s ON s.id = ws.school_id
        WHERE ws.week = $1
        ORDER BY ws.score DESC, s.name
        LIMIT ${LIMIT}`,
      [week],
    );
    return {
      week,
      entries: rows.map((r) => ({
        rank: r.rank,
        school: { id: r.id, name: r.name, animal: r.animal },
        score: r.score,
        members: r.members,
      })),
    };
  });

  /** 개인 랭킹. schoolId 를 주면 학교 내부 랭킹 */
  app.get('/rankings/users', async (req): Promise<{ week: string; entries: UserRankingEntry[] }> => {
    const q = parse(weekQuery, req.query);
    const week = q.week ?? weekKey();
    const { rows } = await db.query(
      `SELECT RANK() OVER (ORDER BY uws.score DESC)::int AS rank,
              u.nickname, s.name AS school_name, uws.score
         FROM user_weekly_scores uws
         JOIN users u ON u.id = uws.user_id
         LEFT JOIN schools s ON s.id = u.school_id
        WHERE uws.week = $1 AND ($2::int IS NULL OR uws.school_id = $2)
        ORDER BY uws.score DESC, u.nickname
        LIMIT ${LIMIT}`,
      [week, q.schoolId ?? null],
    );
    return {
      week,
      entries: rows.map((r) => ({ rank: r.rank, nickname: r.nickname, schoolName: r.school_name, score: r.score })),
    };
  });
}

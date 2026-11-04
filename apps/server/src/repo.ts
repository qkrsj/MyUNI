import { INTERACTION_KINDS, dayKey, emptyInteractions, type InteractionCounts, type Me, type School } from '@myuni/shared';
import type { Queryable } from './db.js';

interface SchoolRow {
  id: number;
  name: string;
  animal: string;
  color_primary: string;
  color_secondary: string;
  sprite_set: string;
}

export function toSchool(row: SchoolRow): School {
  return {
    id: row.id,
    name: row.name,
    animal: row.animal,
    colorPrimary: row.color_primary,
    colorSecondary: row.color_secondary,
    spriteSet: row.sprite_set,
  };
}

export function normalizeInteractions(raw: unknown): InteractionCounts {
  const counts = emptyInteractions();
  if (raw && typeof raw === 'object') {
    for (const k of INTERACTION_KINDS) {
      const v = (raw as Record<string, unknown>)[k];
      if (typeof v === 'number') counts[k] = v;
    }
  }
  return counts;
}

export async function listSchools(q: Queryable): Promise<School[]> {
  const { rows } = await q.query<SchoolRow>('SELECT * FROM schools ORDER BY name');
  return rows.map(toSchool);
}

export async function schoolExists(q: Queryable, id: number): Promise<boolean> {
  const { rowCount } = await q.query('SELECT 1 FROM schools WHERE id = $1', [id]);
  return !!rowCount;
}

export async function loadMe(q: Queryable, userId: number, now = new Date()): Promise<Me | null> {
  const { rows } = await q.query(
    `SELECT u.id, u.nickname, u.school_changed_at,
            s.id AS s_id, s.name AS s_name, s.animal AS s_animal, s.color_primary AS s_cp,
            s.color_secondary AS s_cs, s.sprite_set AS s_sprite,
            c.level, c.total_exp, c.evolution_stage,
            EXISTS (SELECT 1 FROM devices d WHERE d.ranked_user_id = u.id) AS ranked,
            dp.exp AS today_exp, dp.interactions AS today_interactions
       FROM users u
       JOIN characters c ON c.user_id = u.id
       LEFT JOIN schools s ON s.id = u.school_id
       LEFT JOIN daily_progress dp ON dp.user_id = u.id AND dp.day = $2
      WHERE u.id = $1`,
    [userId, dayKey(now)],
  );
  const r = rows[0];
  if (!r) return null;
  return {
    id: r.id,
    nickname: r.nickname,
    school: r.s_id
      ? toSchool({
          id: r.s_id,
          name: r.s_name,
          animal: r.s_animal,
          color_primary: r.s_cp,
          color_secondary: r.s_cs,
          sprite_set: r.s_sprite,
        })
      : null,
    schoolChangedAt: r.school_changed_at ? new Date(r.school_changed_at).toISOString() : null,
    ranked: r.ranked,
    character: { level: r.level, totalExp: r.total_exp, evolutionStage: r.evolution_stage },
    today: { exp: r.today_exp ?? 0, interactions: normalizeInteractions(r.today_interactions) },
  };
}

/** 이 기기에 아직 랭킹 반영 계정이 없으면 이 계정을 지정한다. */
export async function claimDevice(q: Queryable, deviceHash: string, userId: number): Promise<void> {
  await q.query(
    'INSERT INTO devices (device_hash, ranked_user_id) VALUES ($1, $2) ON CONFLICT (device_hash) DO NOTHING',
    [deviceHash, userId],
  );
}

import type { FastifyInstance } from 'fastify';
import { SCHOOL_CHANGE_COOLDOWN_DAYS, changeSchoolRequest, type Me } from '@myuni/shared';
import { withTx } from '../db.js';
import { HttpError, parse } from '../http.js';
import { listSchools, loadMe, schoolExists } from '../repo.js';

export async function meRoutes(app: FastifyInstance): Promise<void> {
  const { db } = app;

  app.get('/schools', async () => ({ schools: await listSchools(db) }));

  app.get('/me', { onRequest: [app.authenticate] }, async (req): Promise<Me> => {
    const me = await loadMe(db, req.userId);
    if (!me) throw new HttpError(404, 'not_found', '계정을 찾을 수 없습니다');
    return me;
  });

  app.put('/me/school', { onRequest: [app.authenticate] }, async (req): Promise<Me> => {
    const { schoolId } = parse(changeSchoolRequest, req.body);
    return withTx(db, async (tx) => {
      const { rows } = await tx.query<{ school_id: number | null; school_changed_at: Date | null }>(
        'SELECT school_id, school_changed_at FROM users WHERE id = $1 FOR UPDATE',
        [req.userId],
      );
      const user = rows[0];
      if (!user) throw new HttpError(404, 'not_found', '계정을 찾을 수 없습니다');
      if (user.school_id === schoolId) return (await loadMe(tx, req.userId))!;
      if (!(await schoolExists(tx, schoolId))) throw new HttpError(400, 'unknown_school', '존재하지 않는 학교입니다');

      if (user.school_changed_at) {
        const nextAllowed = new Date(user.school_changed_at.getTime() + SCHOOL_CHANGE_COOLDOWN_DAYS * 86400_000);
        if (nextAllowed > new Date()) {
          throw new HttpError(409, 'school_change_cooldown', '학교는 한 달에 한 번만 바꿀 수 있습니다', {
            nextAllowedAt: nextAllowed.toISOString(),
          });
        }
      }
      await tx.query('UPDATE users SET school_id = $2, school_changed_at = now() WHERE id = $1', [
        req.userId,
        schoolId,
      ]);
      return (await loadMe(tx, req.userId))!;
    });
  });
}

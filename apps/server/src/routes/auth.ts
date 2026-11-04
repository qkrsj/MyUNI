import type { FastifyInstance } from 'fastify';
import { loginRequest, signupRequest, type AuthResponse } from '@myuni/shared';
import { DUMMY_PASSWORD_HASH, deviceHash, hashPassword, verifyPassword } from '../crypto.js';
import { withTx } from '../db.js';
import { HttpError, parse } from '../http.js';
import { claimDevice, loadMe, schoolExists } from '../repo.js';

export async function authRoutes(app: FastifyInstance): Promise<void> {
  const { db, config } = app;

  app.post('/auth/signup', async (req): Promise<AuthResponse> => {
    const body = parse(signupRequest, req.body);
    const passwordHash = await hashPassword(body.password);
    const device = deviceHash(body.deviceId, config.deviceHashSalt);

    const me = await withTx(db, async (tx) => {
      if (body.schoolId !== null && !(await schoolExists(tx, body.schoolId))) {
        throw new HttpError(400, 'unknown_school', '존재하지 않는 학교입니다');
      }
      const inserted = await tx.query<{ id: number }>(
        `INSERT INTO users (nickname, password_hash, school_id, school_changed_at, device_hash)
         VALUES ($1, $2, $3, CASE WHEN $3::int IS NULL THEN NULL ELSE now() END, $4)
         ON CONFLICT DO NOTHING
         RETURNING id`,
        [body.nickname, passwordHash, body.schoolId, device],
      );
      const userId = inserted.rows[0]?.id;
      if (!userId) throw new HttpError(409, 'nickname_taken', '이미 사용 중인 닉네임입니다');
      await tx.query('INSERT INTO characters (user_id, last_synced_at) VALUES ($1, now())', [userId]);
      await claimDevice(tx, device, userId);
      return (await loadMe(tx, userId))!;
    });

    return { token: app.jwt.sign({ sub: String(me.id) }), me };
  });

  app.post('/auth/login', async (req): Promise<AuthResponse> => {
    const body = parse(loginRequest, req.body);
    const { rows } = await db.query<{ id: number; password_hash: string }>(
      'SELECT id, password_hash FROM users WHERE lower(nickname) = lower($1)',
      [body.nickname],
    );
    const user = rows[0];
    const ok = await verifyPassword(body.password, user?.password_hash ?? DUMMY_PASSWORD_HASH);
    if (!user || !ok) throw new HttpError(401, 'invalid_credentials', '닉네임 또는 비밀번호가 올바르지 않습니다');

    await claimDevice(db, deviceHash(body.deviceId, config.deviceHashSalt), user.id);
    const me = (await loadMe(db, user.id))!;
    return { token: app.jwt.sign({ sub: String(user.id) }), me };
  });
}

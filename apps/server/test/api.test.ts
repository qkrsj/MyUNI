/**
 * 실제 PostgreSQL 이 필요한 통합 테스트.
 * TEST_DATABASE_URL 이 없으면 건너뛴다. 테스트 DB 는 매번 스키마를 지우고 다시 만든다.
 */
import { createHash } from 'node:crypto';
import { afterAll, beforeAll, beforeEach, describe, expect, it } from 'vitest';
import type { FastifyInstance } from 'fastify';
import { RULES, type AuthResponse, type Me, type SyncResponse } from '@myuni/shared';
import { buildApp } from '../src/app.js';
import { createDb, type Db } from '../src/db.js';
import { migrate } from '../src/migrate.js';

const url = process.env.TEST_DATABASE_URL;
const device = (name: string) => createHash('sha256').update(name).digest('hex');

describe.skipIf(!url)('API (PostgreSQL)', () => {
  let db: Db;
  let app: FastifyInstance;

  beforeAll(async () => {
    db = createDb(url!);
    app = await buildApp(
      { databaseUrl: url!, jwtSecret: 'x'.repeat(32), deviceHashSalt: 'y'.repeat(32), port: 0 },
      db,
      { logger: false },
    );
  });

  beforeEach(async () => {
    await db.query('DROP SCHEMA public CASCADE; CREATE SCHEMA public;');
    await migrate(db);
  });

  afterAll(async () => {
    await app?.close();
    await db?.end();
  });

  async function signup(nickname: string, deviceName: string, schoolId: number | null = 1) {
    const res = await app.inject({
      method: 'POST',
      url: '/auth/signup',
      payload: { nickname, password: 'password123', schoolId, deviceId: device(deviceName) },
    });
    return { status: res.statusCode, body: res.json() as AuthResponse };
  }

  function authed(token: string) {
    return { authorization: `Bearer ${token}` };
  }

  async function backdateSync(userId: number, minutes: number) {
    await db.query(`UPDATE characters SET last_synced_at = now() - make_interval(mins => $2) WHERE user_id = $1`, [
      userId,
      minutes,
    ]);
  }

  it('signs up, logs in, and rejects duplicate nicknames case-insensitively', async () => {
    const first = await signup('Duck', 'pc1');
    expect(first.status).toBe(200);
    expect(first.body.me.ranked).toBe(true);
    expect(first.body.me.school?.animal).toBe('tiger');

    expect((await signup('duck', 'pc2')).status).toBe(409);

    const login = await app.inject({
      method: 'POST',
      url: '/auth/login',
      payload: { nickname: 'DUCK', password: 'password123', deviceId: device('pc1') },
    });
    expect(login.statusCode).toBe(200);

    const bad = await app.inject({
      method: 'POST',
      url: '/auth/login',
      payload: { nickname: 'Duck', password: 'wrong-password', deviceId: device('pc1') },
    });
    expect(bad.statusCode).toBe(401);
  });

  it('never stores the raw device id', async () => {
    await signup('Alice', 'pc1');
    const { rows } = await db.query('SELECT device_hash FROM users');
    expect(rows[0].device_hash).toMatch(/^[0-9a-f]{64}$/);
    expect(rows[0].device_hash).not.toBe(device('pc1'));
  });

  it('ranks only the first account per device', async () => {
    const a = await signup('Alice', 'shared-pc');
    const b = await signup('Bob', 'shared-pc');
    expect(a.body.me.ranked).toBe(true);
    expect(b.body.me.ranked).toBe(false);

    for (const user of [a, b]) {
      await backdateSync(user.body.me.id, 30);
      const res = await app.inject({
        method: 'POST',
        url: '/progress/sync',
        headers: authed(user.body.token),
        payload: { activeMinutes: 20, interactions: {} },
      });
      expect((res.json() as SyncResponse).granted).toBe(20);
    }

    const users = (await app.inject({ url: '/rankings/users' })).json();
    expect(users.entries.map((e: { nickname: string }) => e.nickname)).toEqual(['Alice']);
    const schools = (await app.inject({ url: '/rankings/schools' })).json();
    expect(schools.entries[0]).toMatchObject({ rank: 1, score: 20, members: 1 });
  });

  it('caps active minutes by real elapsed time and exp by the daily cap', async () => {
    const { body } = await signup('Alice', 'pc1');

    // 방금 가입: 경과 시간 0분 → 최대 1분만 인정
    let res = await app.inject({
      method: 'POST',
      url: '/progress/sync',
      headers: authed(body.token),
      payload: { activeMinutes: 600, interactions: {} },
    });
    expect((res.json() as SyncResponse).granted).toBe(1);

    await backdateSync(body.me.id, 24 * 60);
    res = await app.inject({
      method: 'POST',
      url: '/progress/sync',
      headers: authed(body.token),
      payload: { activeMinutes: 1000, interactions: { feed: 99 } },
    });
    const sync = res.json() as SyncResponse;
    expect(sync.me.today.exp).toBe(RULES.dailyExpCap);
    expect(sync.me.today.interactions.feed).toBe(RULES.interactions.feed.dailyLimit);
    expect(sync.me.character.totalExp).toBe(RULES.dailyExpCap);
    expect(sync.me.character.level).toBeGreaterThan(1);
  });

  it('limits school changes to once per cooldown', async () => {
    const { body } = await signup('Alice', 'pc1', null);
    const change = (schoolId: number) =>
      app.inject({ method: 'PUT', url: '/me/school', headers: authed(body.token), payload: { schoolId } });

    expect((await change(1)).statusCode).toBe(200);
    const blocked = await change(2);
    expect(blocked.statusCode).toBe(409);
    expect(blocked.json().error).toBe('school_change_cooldown');

    await db.query(`UPDATE users SET school_changed_at = now() - interval '31 days'`);
    expect(((await change(2)).json() as Me).school?.id).toBe(2);
  });

  it('requires auth for protected routes', async () => {
    expect((await app.inject({ url: '/me' })).statusCode).toBe(401);
    expect((await app.inject({ url: '/me', headers: { authorization: 'Bearer nope' } })).statusCode).toBe(401);
  });
});

import { createHmac, randomBytes, scrypt, timingSafeEqual, type ScryptOptions } from 'node:crypto';

const PARAMS = { N: 16384, r: 8, p: 1, maxmem: 64 * 1024 * 1024 };
const KEYLEN = 32;

function scryptAsync(password: string, salt: Buffer, keylen: number, opts: ScryptOptions): Promise<Buffer> {
  return new Promise((resolve, reject) =>
    scrypt(password, salt, keylen, opts, (err, key) => (err ? reject(err) : resolve(key))),
  );
}

export async function hashPassword(password: string): Promise<string> {
  const salt = randomBytes(16);
  const hash = await scryptAsync(password, salt, KEYLEN, PARAMS);
  return ['scrypt', PARAMS.N, PARAMS.r, PARAMS.p, salt.toString('base64'), hash.toString('base64')].join('$');
}

export async function verifyPassword(password: string, stored: string): Promise<boolean> {
  const [algo, n, r, p, saltB64, hashB64] = stored.split('$');
  if (algo !== 'scrypt' || !saltB64 || !hashB64) return false;
  const expected = Buffer.from(hashB64, 'base64');
  const actual = await scryptAsync(password, Buffer.from(saltB64, 'base64'), expected.length, {
    N: Number(n),
    r: Number(r),
    p: Number(p),
    maxmem: PARAMS.maxmem,
  });
  return timingSafeEqual(expected, actual);
}

/** 존재하지 않는 닉네임으로 로그인할 때도 같은 시간이 걸리게 하기 위한 더미 해시 */
export const DUMMY_PASSWORD_HASH = await hashPassword('dummy-password-for-timing');

/**
 * 클라이언트가 보낸 SHA-256(기기 ID)에 서버 salt 로 HMAC 을 한 번 더 건다.
 * DB 가 유출돼도 salt 없이는 기기 ID 와 대조할 수 없다.
 */
export function deviceHash(clientDeviceId: string, salt: string): string {
  return createHmac('sha256', salt).update(clientDeviceId).digest('hex');
}

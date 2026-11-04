import { app, safeStorage } from 'electron';
import { readFile, rm, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import type { Me } from '@myuni/shared';

/** 로그인 토큰과 마지막 상태. 가능하면 OS 키체인(safeStorage)으로 암호화해서 저장한다. */
export interface StoredSession {
  token: string;
  me: Me;
}

const file = () => join(app.getPath('userData'), 'session.bin');

export async function loadSession(): Promise<StoredSession | null> {
  try {
    const buf = await readFile(file());
    const json = safeStorage.isEncryptionAvailable() ? safeStorage.decryptString(buf) : buf.toString('utf8');
    return JSON.parse(json) as StoredSession;
  } catch {
    return null;
  }
}

export async function saveSession(session: StoredSession): Promise<void> {
  const json = JSON.stringify(session);
  const data = safeStorage.isEncryptionAvailable() ? safeStorage.encryptString(json) : Buffer.from(json, 'utf8');
  await writeFile(file(), data);
}

export async function clearSession(): Promise<void> {
  await rm(file(), { force: true });
}

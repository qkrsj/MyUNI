import { execFile } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { promisify } from 'node:util';

const run = promisify(execFile);

/** OS 가 제공하는 기기 고유값 원본. 이 값은 기기 밖으로 보내지 않는다. */
async function rawMachineId(): Promise<string> {
  if (process.platform === 'win32') {
    const { stdout } = await run('reg', [
      'query',
      'HKLM\\SOFTWARE\\Microsoft\\Cryptography',
      '/v',
      'MachineGuid',
      '/reg:64',
    ]);
    const match = /MachineGuid\s+REG_SZ\s+(\S+)/i.exec(stdout);
    if (match?.[1]) return match[1];
  } else if (process.platform === 'darwin') {
    const { stdout } = await run('ioreg', ['-rd1', '-c', 'IOPlatformExpertDevice']);
    const match = /"IOPlatformUUID"\s*=\s*"([^"]+)"/.exec(stdout);
    if (match?.[1]) return match[1];
  } else {
    // 개발용 (Linux)
    return (await readFile('/etc/machine-id', 'utf8')).trim();
  }
  throw new Error('기기 고유값을 읽을 수 없습니다');
}

let cached: Promise<string> | undefined;

/**
 * 서버로 보내는 기기 식별값: SHA-256(원본).
 * 서버는 여기에 다시 비밀 salt 로 HMAC 을 걸어 저장한다.
 */
export function deviceId(): Promise<string> {
  cached ??= rawMachineId().then((raw) => createHash('sha256').update(`myuni-device:${raw}`).digest('hex'));
  return cached;
}

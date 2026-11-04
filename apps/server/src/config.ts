function required(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`환경 변수 ${name} 가 필요합니다`);
  return v;
}

export interface Config {
  databaseUrl: string;
  jwtSecret: string;
  deviceHashSalt: string;
  port: number;
}

export function loadConfig(): Config {
  const config: Config = {
    databaseUrl: required('DATABASE_URL'),
    jwtSecret: required('JWT_SECRET'),
    deviceHashSalt: required('DEVICE_HASH_SALT'),
    port: Number(process.env.PORT ?? 3000),
  };
  if (config.jwtSecret.length < 32) throw new Error('JWT_SECRET 은 32자 이상이어야 합니다');
  if (config.deviceHashSalt.length < 32) throw new Error('DEVICE_HASH_SALT 는 32자 이상이어야 합니다');
  return config;
}

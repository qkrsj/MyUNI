import type {
  AuthResponse,
  LoginRequest,
  Me,
  School,
  SignupRequest,
  SyncRequest,
  SyncResponse,
} from '@myuni/shared';

export const API_URL: string =
  process.env.MYUNI_API_URL ?? import.meta.env.MAIN_VITE_API_URL ?? 'http://localhost:3000';

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(method: string, path: string, body?: unknown, token?: string): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method,
      headers: {
        ...(body !== undefined ? { 'content-type': 'application/json' } : {}),
        ...(token ? { authorization: `Bearer ${token}` } : {}),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: AbortSignal.timeout(10_000),
    });
  } catch {
    throw new ApiError(0, 'network', '서버에 연결할 수 없습니다');
  }
  const data = (await res.json().catch(() => ({}))) as { error?: string; message?: string };
  if (!res.ok) throw new ApiError(res.status, data.error ?? 'unknown', data.message ?? `요청 실패 (${res.status})`);
  return data as T;
}

export const api = {
  schools: () => request<{ schools: School[] }>('GET', '/schools').then((r) => r.schools),
  signup: (body: SignupRequest) => request<AuthResponse>('POST', '/auth/signup', body),
  login: (body: LoginRequest) => request<AuthResponse>('POST', '/auth/login', body),
  me: (token: string) => request<Me>('GET', '/me', undefined, token),
  sync: (token: string, body: SyncRequest) => request<SyncResponse>('POST', '/progress/sync', body, token),
};

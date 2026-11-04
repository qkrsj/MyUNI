import Fastify, { type FastifyInstance, type FastifyReply, type FastifyRequest } from 'fastify';
import fastifyJwt from '@fastify/jwt';
import type { Config } from './config.js';
import type { Db } from './db.js';
import { HttpError } from './http.js';
import { authRoutes } from './routes/auth.js';
import { meRoutes } from './routes/me.js';
import { progressRoutes } from './routes/progress.js';
import { rankingRoutes } from './routes/rankings.js';

declare module 'fastify' {
  interface FastifyInstance {
    db: Db;
    config: Config;
    authenticate: (req: FastifyRequest, reply: FastifyReply) => Promise<void>;
  }
  interface FastifyRequest {
    userId: number;
  }
}

declare module '@fastify/jwt' {
  interface FastifyJWT {
    payload: { sub: string };
    user: { sub: string };
  }
}

export async function buildApp(config: Config, db: Db, opts: { logger?: boolean } = {}): Promise<FastifyInstance> {
  const app = Fastify({ logger: opts.logger ?? true });

  app.decorate('db', db);
  app.decorate('config', config);
  app.decorateRequest('userId', 0);

  await app.register(fastifyJwt, { secret: config.jwtSecret, sign: { expiresIn: '30d' } });

  app.decorate('authenticate', async (req: FastifyRequest) => {
    try {
      await req.jwtVerify();
    } catch {
      throw new HttpError(401, 'unauthorized', '로그인이 필요합니다');
    }
    req.userId = Number(req.user.sub);
  });

  app.setErrorHandler((err, req, reply) => {
    if (err instanceof HttpError) {
      return reply.code(err.statusCode).send({ error: err.code, message: err.message, details: err.details });
    }
    const status = (err as { statusCode?: number }).statusCode;
    if (status && status < 500) {
      return reply.code(status).send({ error: 'bad_request', message: (err as Error).message });
    }
    req.log.error(err);
    return reply.code(500).send({ error: 'internal', message: '서버 오류가 발생했습니다' });
  });

  app.get('/health', async () => ({ ok: true }));

  await app.register(authRoutes);
  await app.register(meRoutes);
  await app.register(progressRoutes);
  await app.register(rankingRoutes);

  return app;
}

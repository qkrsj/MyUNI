# 레포 루트에서 빌드: docker build -f apps/server/Dockerfile -t myuni-server .
FROM node:22-slim
WORKDIR /app
ENV NODE_ENV=production

COPY package.json package-lock.json ./
COPY packages/shared/package.json packages/shared/
COPY apps/server/package.json apps/server/
COPY apps/desktop/package.json apps/desktop/
RUN npm ci --omit=dev -w @myuni/server -w @myuni/shared

COPY packages/shared/src packages/shared/src
COPY apps/server/src apps/server/src
COPY apps/server/migrations apps/server/migrations

WORKDIR /app/apps/server
USER node
EXPOSE 3000
# 배포 파이프라인에서 마이그레이션은 별도 태스크로 실행: npm run migrate
CMD ["npx", "tsx", "src/index.ts"]

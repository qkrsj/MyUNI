#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# 서버를 최신 코드로 올린다. 서버 안에서 돌린다.
#
#   bash deploy/update.sh
#
# 밀어 넣는다고 저절로 배포되지 않는다. 클라이언트만 새 버전이 되고 서버가 옛 버전으로
# 남으면 새로 만든 경로가 없어서 실패한다. 하는 일: 백업 -> 받기 -> 다시 빌드 -> 확인.
# ---------------------------------------------------------------------------
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE/.."

echo "== 1. 백업"
bash deploy/backup.sh

echo "== 2. 새 코드 받기"
echo "   지금: $(git log --oneline -1)"
git pull --ff-only -q
echo "   받음: $(git log --oneline -1)"

echo "== 3. 다시 빌드"
docker compose -f deploy/docker-compose.prod.yml up -d --build

echo "== 4. 확인"
sleep 6
DOMAIN=$(grep MYUNI_DOMAIN deploy/.env | cut -d= -f2)
curl -fsS --max-time 20 "https://$DOMAIN/api/version" && echo || {
  echo "   !! 응답이 없습니다:  docker compose -f deploy/docker-compose.prod.yml logs --tail 50"
  exit 1
}

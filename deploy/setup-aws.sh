#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# AWS Lightsail 리눅스 VM 한 대에 MyUNi 서버를 올린다. 여러 번 돌려도 안전하다.
#
# 서버(FastAPI)와 DB(SQLite 파일)를 한 대에 둔다. 서울 리전에 두면 한국에서 왕복이 몇 ms 다.
#
# 미리 해둘 것 (Lightsail 콘솔):
#   1) 인스턴스 생성 - 서울(ap-northeast-2), Ubuntu, 512MB 이상
#   2) 고정 IP(Static IP)를 만들어 붙인다 (안 붙이면 재부팅 때 주소가 바뀐다)
#   3) Networking > IPv4 Firewall 에 HTTP(80), HTTPS(443) 추가 (기본은 22 만 열려 있다)
#   4) 도메인이 이 IP 를 가리키게 한다 (Route 53, 또는 무료 https://www.duckdns.org)
#
# 그다음 SSH 로 들어와서:
#   git clone https://github.com/qkrsj/MyUNi.git ~/MyUNi
#   bash ~/MyUNi/deploy/setup-aws.sh
#
# 물어보는 게 싫으면:  MYUNI_DOMAIN=x.duckdns.org ACME_EMAIL=me@example.com bash deploy/setup-aws.sh
# (curl ... | bash 로 돌리지 마세요 - read 가 스크립트 나머지 줄을 답으로 먹습니다)
# ---------------------------------------------------------------------------
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

say()  { printf '\n\033[1;33m== %s\033[0m\n' "$*"; }
ok()   { printf '   \033[32mOK\033[0m  %s\n' "$*"; }
warn() { printf '   \033[31m!!\033[0m  %s\n' "$*"; }

if [ "$(id -u)" -eq 0 ]; then
  warn "root 로 돌리지 마세요. 일반 사용자(ubuntu)로 실행하세요."
  exit 1
fi

# ---------------------------------------------------------------- 1. 스왑
# 제일 싼 인스턴스는 메모리가 512MB 라 스왑 없이 도커 빌드를 하면 죽는다.
if ! swapon --show | grep -q .; then
  say "스왑 2GB 만들기"
  sudo fallocate -l 2G /swapfile 2>/dev/null || sudo dd if=/dev/zero of=/swapfile bs=1M count=2048
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile >/dev/null
  sudo swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
  ok "스왑 켜짐"
fi

# ---------------------------------------------------------------- 2. 도커
if ! command -v docker >/dev/null 2>&1; then
  say "도커 설치"
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER"
fi

# 방금 도커 그룹에 넣었으면 지금 셸은 모른다. sg 로 이번 실행에만 적용한다.
SG=""
if ! docker info >/dev/null 2>&1; then
  if sg docker -c "docker info" >/dev/null 2>&1; then
    SG="yes"
  else
    warn "아직 도커 권한이 없습니다. 한 번 나갔다 다시 들어와서 이 스크립트를 다시 돌리세요."
    exit 1
  fi
fi
d() {
  if [ -n "$SG" ]; then sg docker -c "cd '$PWD' && docker $*"; else docker "$@"; fi
}
ok "도커: $(d --version)"

# ---------------------------------------------------------------- 3. 포트
busy=""
for port in 80 443; do
  if sudo ss -lntp 2>/dev/null | grep -q ":$port "; then busy="$busy $port"; fi
done
if [ -n "$busy" ] && ! d ps --format '{{.Names}}' | grep -q myuni-caddy; then
  warn "포트$busy 를 이미 다른 프로그램이 쓰고 있어서 Caddy 가 못 뜹니다."
  sudo ss -lntp | grep -E ":(80|443) " || true
  exit 1
fi

# ---------------------------------------------------------------- 4. 도메인
cd "$APP_DIR/deploy"
if [ ! -f .env ]; then
  say "도메인 설정"
  DOMAIN="${MYUNI_DOMAIN:-}"
  EMAIL="${ACME_EMAIL:-}"
  [ -n "$DOMAIN" ] || read -rp "   이 VM 을 가리키는 도메인: " DOMAIN
  [ -n "$EMAIL" ] || read -rp "   이메일 (인증서 만료 알림용): " EMAIL
  [ -n "$DOMAIN" ] || { warn "도메인 없이는 HTTPS 를 켤 수 없습니다."; exit 1; }
  printf 'MYUNI_DOMAIN=%s\nACME_EMAIL=%s\n' "$DOMAIN" "$EMAIL" > .env
  chmod 600 .env
  ok ".env 저장"
fi

# ---------------------------------------------------------------- 5. 실행
say "빌드하고 띄우기 (처음이면 몇 분 걸립니다)"
d compose -f docker-compose.prod.yml up -d --build
sleep 8
d compose -f docker-compose.prod.yml ps

DOMAIN=$(grep MYUNI_DOMAIN .env | cut -d= -f2)
if curl -fsS --max-time 20 "https://$DOMAIN/api/health" >/dev/null 2>&1; then
  ok "https://$DOMAIN 정상 동작"
  echo
  warn "남은 일:"
  echo "     1) 백업 켜기:  bash deploy/backup.sh --install"
  echo "        SQLite 파일 하나가 유일본입니다. 인스턴스가 날아가면 끝입니다."
  echo "     2) GitHub 저장소 Settings > Variables 에 MYUNI_SERVER_URL=https://$DOMAIN 을 넣고"
  echo "        새 버전을 릴리스하면 배포판이 이 주소로 붙습니다."
else
  warn "아직 응답이 없습니다. 인증서 발급에 1~2분 걸리기도 합니다."
  echo "   확인:  docker compose -f deploy/docker-compose.prod.yml logs -f caddy"
  echo "   흔한 원인: 도메인이 이 VM 의 고정 IP 를 안 가리킴 (dig +short $DOMAIN),"
  echo "              Lightsail 방화벽에 80/443 이 없음"
fi

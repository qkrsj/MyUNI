#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# DB 를 떠서 보관한다. 하루 한 번 cron 으로 돈다.
#
#   bash deploy/backup.sh --install   # cron 에 걸기 (매일 한국 시각 새벽 4시 13분)
#   bash deploy/backup.sh             # 지금 한 번 뜨기
#
# 여기서는 SQLite 파일 하나가 유일본이다. 인스턴스가 날아가면 그것으로 끝이다.
# deploy/.env 에 MYUNI_BACKUP_S3=s3://버킷/경로 를 넣고 aws CLI 를 설정해 두면
# S3 에도 올린다 (같은 인스턴스 안의 백업만으로는 인스턴스와 함께 사라진다).
#
# device_salt 도 같이 뜬다. 이게 없으면 DB 를 되살려도 기기 판정이 전부 새로 시작된다.
# ---------------------------------------------------------------------------
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="${MYUNI_BACKUP_DIR:-$HOME/myuni-backups}"
KEEP="${MYUNI_BACKUP_KEEP:-14}"
CONTAINER="${MYUNI_CONTAINER:-myuni-server}"

ok()  { printf '   \033[32mOK\033[0m  %s\n' "$*"; }
die() { printf '   \033[31m!!\033[0m  %s\n' "$*" >&2; exit 1; }

[ -f "$HERE/.env" ] && set -a && . "$HERE/.env" && set +a

if [ "${1:-}" = "--install" ]; then
  mkdir -p "$OUT_DIR"
  # 서버 시계는 UTC 다. 한국 시각 04:13 = UTC 전날 19:13
  line="13 19 * * * bash $HERE/backup.sh >> $OUT_DIR/backup.log 2>&1"
  (crontab -l 2>/dev/null | grep -Fv "$HERE/backup.sh"; echo "$line") | crontab -
  ok "cron 등록: $line"
  exit 0
fi

mkdir -p "$OUT_DIR"
stamp="$(date -u +%Y%m%d-%H%M%S)"
name="myuni-$stamp"

# 돌고 있는 DB 를 안전하게 뜬다 (SQLite 온라인 백업 - 파일을 그냥 복사하면 깨질 수 있다)
docker exec "$CONTAINER" python -c "
import sqlite3
src = sqlite3.connect('/data/myuni.db')
dst = sqlite3.connect('/data/backup.db')
src.backup(dst)
dst.close(); src.close()
" || die "DB 를 못 떴습니다"
docker cp "$CONTAINER:/data/backup.db" "$OUT_DIR/$name.db"
docker exec "$CONTAINER" rm -f /data/backup.db
docker cp "$CONTAINER:/data/device_salt" "$OUT_DIR/device_salt" 2>/dev/null || true

tar -C "$OUT_DIR" -czf "$OUT_DIR/$name.tar.gz" "$name.db" $( [ -f "$OUT_DIR/device_salt" ] && echo device_salt )
rm -f "$OUT_DIR/$name.db"
chmod 600 "$OUT_DIR/$name.tar.gz"
ok "$OUT_DIR/$name.tar.gz ($(du -h "$OUT_DIR/$name.tar.gz" | cut -f1))"

if [ -n "${MYUNI_BACKUP_S3:-}" ]; then
  aws s3 cp "$OUT_DIR/$name.tar.gz" "${MYUNI_BACKUP_S3%/}/$name.tar.gz" --sse AES256 --only-show-errors \
    && ok "S3 에 올림: ${MYUNI_BACKUP_S3%/}/$name.tar.gz" \
    || printf '   \033[31m!!\033[0m  S3 업로드 실패 (로컬 백업은 남아 있다)\n'
fi

# 오래된 것 정리
ls -1t "$OUT_DIR"/myuni-*.tar.gz 2>/dev/null | tail -n +"$((KEEP + 1))" | xargs -r rm -f

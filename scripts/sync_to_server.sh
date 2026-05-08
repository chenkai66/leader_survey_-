#!/usr/bin/env bash
set -euo pipefail

LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTE_DIR="/root/Project/leader_survey_review"

echo "==========================================="
echo "  Leader Survey -> CK Planet (via ecs-run)"
echo "==========================================="
echo "Local  : $LOCAL_DIR"
echo "Remote : $REMOTE_DIR"
echo ""

TAR_FILE="/tmp/leader_survey_$(date +%s).tar.gz"
echo "[1/4] Packaging..."
tar -czf "$TAR_FILE" -C "$LOCAL_DIR" \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='.venv' \
    --exclude='*.pyc' \
    --exclude='.DS_Store' \
    .
echo "  tar size: $(du -h "$TAR_FILE" | cut -f1)"

echo "[2/4] Encoding base64..."
B64_FILE="${TAR_FILE}.b64"
base64 < "$TAR_FILE" > "$B64_FILE"
B64_SIZE=$(wc -c < "$B64_FILE")
echo "  base64 size: $((B64_SIZE / 1024)) KB"

echo "[3/4] Uploading via ecs-run..."
CHUNK_SIZE=8000
SPLIT_DIR=$(mktemp -d)
split -b "$CHUNK_SIZE" "$B64_FILE" "$SPLIT_DIR/chunk_"

ecs-run "mkdir -p $REMOTE_DIR && rm -f /tmp/ls_sync.b64" >/dev/null

CHUNKS=("$SPLIT_DIR"/chunk_*)
TOTAL=${#CHUNKS[@]}
echo "  uploading $TOTAL chunks..."
i=0
for C in "${CHUNKS[@]}"; do
    i=$((i+1))
    DATA=$(cat "$C")
    ecs-run "printf '%s' '$DATA' >> /tmp/ls_sync.b64" >/dev/null
    if [ $((i % 10)) -eq 0 ] || [ $i -eq $TOTAL ]; then
        echo "    chunk $i/$TOTAL"
    fi
done

rm -rf "$SPLIT_DIR" "$TAR_FILE" "$B64_FILE"

echo "[4/4] Decoding and extracting on server..."
ecs-run "cd $REMOTE_DIR && base64 -d /tmp/ls_sync.b64 > /tmp/ls_sync.tar.gz && tar -xzf /tmp/ls_sync.tar.gz && rm /tmp/ls_sync.b64 /tmp/ls_sync.tar.gz"

echo ""
echo "==========================================="
echo "  Sync done -> $REMOTE_DIR"
echo "==========================================="

#!/usr/bin/env bash
# pull_file.sh — chunked pull from server (avoids scp; uses ecs-run RunCommand).
# Required because ecs-run output is bounded; we split base64 server-side and
# concatenate locally.
#
# Usage: pull_file.sh <ecs_target> <remote_path> <local_path>
set -e

TARGET="$1"
REMOTE="$2"
LOCAL="$3"

if [ -z "$TARGET" ] || [ -z "$REMOTE" ] || [ -z "$LOCAL" ]; then
    echo "Usage: pull_file.sh <ecs_target> <remote_path> <local_path>"
    exit 1
fi

REMOTE_TMP="/tmp/_pull_$(basename $REMOTE)"

# On server: encode + flatten + split
ecs-run "$TARGET" "base64 $REMOTE | tr -d '\n' > ${REMOTE_TMP}.b64 && split -b 7000 -a 3 ${REMOTE_TMP}.b64 ${REMOTE_TMP}.chunk_ && ls ${REMOTE_TMP}.chunk_* | wc -l"

chunks_list=$(ecs-run "$TARGET" "ls ${REMOTE_TMP}.chunk_*")
> "${LOCAL}.b64"
for chunk in $chunks_list; do
    ecs-run "$TARGET" "cat $chunk" >> "${LOCAL}.b64"
done

base64 -d -i "${LOCAL}.b64" -o "$LOCAL"
rm -f "${LOCAL}.b64"
ecs-run "$TARGET" "rm -f ${REMOTE_TMP}.b64 ${REMOTE_TMP}.chunk_*" >/dev/null

wc -c "$LOCAL"

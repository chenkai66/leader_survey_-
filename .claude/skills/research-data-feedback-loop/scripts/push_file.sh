#!/usr/bin/env bash
# push_file.sh — chunked push to server (avoids scp / file size limits in
# ecs-run RunCommand single-call argument).
#
# Usage: push_file.sh <ecs_target> <local_path> <remote_path>
set -e

TARGET="$1"
LOCAL="$2"
REMOTE="$3"

if [ -z "$TARGET" ] || [ -z "$LOCAL" ] || [ -z "$REMOTE" ]; then
    echo "Usage: push_file.sh <ecs_target> <local_path> <remote_path>"
    exit 1
fi

REMOTE_TMP="/tmp/_push_$(basename $REMOTE)"

base64 -i "$LOCAL" -o "${LOCAL}.b64.tmp"
tr -d '\n' < "${LOCAL}.b64.tmp" > "${LOCAL}.b64.flat"
rm "${LOCAL}.b64.tmp"

split_dir=$(mktemp -d)
split -b 7000 -a 3 "${LOCAL}.b64.flat" "$split_dir/c_"
n_chunks=$(ls "$split_dir"/c_* | wc -l | tr -d ' ')
echo "  pushing $LOCAL -> $REMOTE  in $n_chunks chunks"

ecs-run "$TARGET" "rm -f ${REMOTE_TMP}.b64" >/dev/null

for chunk in "$split_dir"/c_*; do
    DATA=$(cat "$chunk")
    ecs-run "$TARGET" "printf '%s' '$DATA' >> ${REMOTE_TMP}.b64" >/dev/null
done

ecs-run "$TARGET" "base64 -d ${REMOTE_TMP}.b64 > $REMOTE && wc -c $REMOTE && rm ${REMOTE_TMP}.b64"

rm -rf "$split_dir" "${LOCAL}.b64.flat"

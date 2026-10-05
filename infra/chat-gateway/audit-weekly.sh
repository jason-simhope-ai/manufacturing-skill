#!/bin/sh
# Weekly audit verify + off-host heads push (docs/audit-operations.md §2, DEPLOY.md §6).
# Run by mfg-twin-audit-weekly.service as the service user, with the gateway's EnvironmentFile
# (MFG_TEAM_AUDIT_HMAC_KEY) and these variables from the unit:
#   MFG_TEAM_STATE_DIR  the gateway's state dir           HEADS_DIR   local heads dir (latest.json lives here)
#   ARCHIVE_DEST        user@host:/path/ (off-host, WORM)   PUSH_KEY    ssh private key allowed to push only
# Week one has no latest.json: run the first verify by hand with --heads-out only (DEPLOY.md D7);
# this script refuses to run without an anchor so a deleted latest.json cannot skip the comparison.
set -eu
: "${MFG_TEAM_STATE_DIR:?}" "${HEADS_DIR:?}" "${ARCHIVE_DEST:?}" "${PUSH_KEY:?}"
W=$(date +%G-W%V)
OUT="$HEADS_DIR/heads-$W.json"
if [ ! -f "$HEADS_DIR/latest.json" ]; then
    echo "audit-weekly: $HEADS_DIR/latest.json missing; week one runs by hand with --heads-out only (DEPLOY.md D7)" >&2
    exit 2
fi
python3 -m chat_gateway audit-verify "$MFG_TEAM_STATE_DIR/audit" \
    --anchor "$HEADS_DIR/latest.json" --heads-out "$OUT"
# Off-host first: latest.json only advances once the archive holds this week's file.
rsync -a --chmod=F0440 -e "ssh -i $PUSH_KEY -o BatchMode=yes -o StrictHostKeyChecking=yes" "$OUT" "$ARCHIVE_DEST"
cp "$OUT" "$HEADS_DIR/latest.json"

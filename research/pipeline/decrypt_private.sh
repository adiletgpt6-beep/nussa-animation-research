#!/usr/bin/env bash
# Decrypt the encrypted review packs (transcripts + contact sheets) OUTSIDE the repo.
# Usage: decrypt_private.sh <age-identity-file> <output-dir>
set -euo pipefail
KEY="$1"; OUT="$2"; mkdir -p "$OUT"
for f in "$(dirname "$0")"/../data/private/*.private.tar.age; do
  [ -e "$f" ] || continue
  age -d -i "$KEY" "$f" | tar -x -C "$OUT"
done
echo "decrypted to $OUT"

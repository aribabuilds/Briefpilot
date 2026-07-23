#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

copy_if_missing() {
  local example="$1"
  local target="$2"
  if [ -f "$target" ]; then
    echo "skip: $target already exists"
  else
    cp "$example" "$target"
    echo "created: $target"
  fi
}

copy_if_missing "$root_dir/.env.example" "$root_dir/.env"
copy_if_missing "$root_dir/frontend/.env.example" "$root_dir/frontend/.env"
copy_if_missing "$root_dir/backend/.env.example" "$root_dir/backend/.env"

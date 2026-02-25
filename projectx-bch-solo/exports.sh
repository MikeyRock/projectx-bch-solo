#!/usr/bin/env bash
set -euo pipefail

# If JWT_SECRET is missing (can happen on SSH restarts), read it from
# the running auth container so app_proxy can validate auth tokens.
if [[ -z "${JWT_SECRET:-}" ]] && command -v docker >/dev/null 2>&1; then
  jwt_secret_from_auth=""
  for auth_container in auth umbrel-auth umbrel_auth; do
    jwt_secret_from_auth="$(
      docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "${auth_container}" 2>/dev/null \
      | sed -n 's/^JWT_SECRET=//p' \
      | tail -n 1
    )"
    if [[ -n "${jwt_secret_from_auth:-}" ]]; then
      break
    fi
  done
  if [[ -n "${jwt_secret_from_auth:-}" ]]; then
    export JWT_SECRET="${jwt_secret_from_auth}"
  fi
fi

export JWT_SECRET="${JWT_SECRET:-DEADBEEF}"

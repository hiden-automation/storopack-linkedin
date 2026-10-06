#!/usr/bin/env bash
# Uso: scripts/commit_push.sh "mensagem" [comando que (re)aplica a mudança]
# Sem comando: commita o que mudou e faz push com rebase.
# Com comando: em caso de corrida, descarta, volta para origin/main e reaplica o comando.
set -euo pipefail

msg="$1"
apply="${2:-}"

git config user.name "storobot"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

for attempt in 1 2 3 4 5; do
  if [ -n "$apply" ] && [ "$attempt" -gt 1 ]; then
    git fetch -q origin main
    git reset -q --hard origin/main
    bash -c "$apply"
  fi
  git add -A docs cache data
  if git diff --cached --quiet; then
    echo "nada para commitar"
    exit 0
  fi
  git commit -q -m "$msg"
  if [ -z "$apply" ]; then
    git pull -q --rebase -X theirs origin main || { git rebase --abort || true; }
  fi
  if git push -q origin HEAD:main; then
    echo "push ok"
    exit 0
  fi
  echo "push falhou (tentativa $attempt), tentando novamente..."
  if [ -z "$apply" ]; then git reset -q --soft HEAD~1; fi
  sleep $((attempt * 3))
done
echo "não foi possível fazer push" >&2
exit 1

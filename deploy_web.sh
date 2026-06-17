#!/usr/bin/env bash
# Деплой фронтенда на total-hunter.com
# Использование: bash deploy_web.sh "сообщение коммита"

set -e

MSG="${1:-update}"
TOKEN=$(cat /c/Users/Admin/AppData/Roaming/com.vercel.cli/Data/auth.json | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
TEAM="team_CkkRPXdwtRtsL9YCk8n4Fzla"
PROJECT="prj_mWtcb6hJCkl40YLWheeIlxD5NmXj"
HOOK="https://api.vercel.com/v1/integrations/deploy/prj_mWtcb6hJCkl40YLWheeIlxD5NmXj/D0wsErcYcw"

echo "=== Коммит и пуш ==="
git push origin main
echo "✅ Запушено"

echo ""
echo "=== Триггер Vercel build ==="
curl -s -X POST "$HOOK" | grep -o '"job":{[^}]*}' || echo "hook triggered"
echo "✅ Build запущен"

echo ""
echo "=== Ждём НОВЫЙ build (poll) ==="
OLD_ID=$(curl -s "https://api.vercel.com/v6/deployments?projectId=$PROJECT&teamId=$TEAM&limit=1" \
  -H "Authorization: Bearer $TOKEN" | grep -o '"uid":"[^"]*"' | head -1 | cut -d'"' -f4)

until NEW_ID=$(curl -s "https://api.vercel.com/v6/deployments?projectId=$PROJECT&teamId=$TEAM&limit=1" \
  -H "Authorization: Bearer $TOKEN" | grep -o '"uid":"[^"]*"' | head -1 | cut -d'"' -f4) && \
  [ "$NEW_ID" != "$OLD_ID" ] && \
  STATE=$(curl -s "https://api.vercel.com/v6/deployments/$NEW_ID?teamId=$TEAM" \
    -H "Authorization: Bearer $TOKEN" | grep -o '"readyState":"[^"]*"' | head -1 | cut -d'"' -f4) && \
  [ "$STATE" = "READY" ]; do
  echo "  $NEW_ID → $STATE..."
  sleep 10
done
echo "Build READY: $NEW_ID"

echo ""
echo "=== Привязываем домен ==="
curl -s -X POST "https://api.vercel.com/v2/deployments/$NEW_ID/aliases?teamId=$TEAM" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"alias":"total-hunter.com"}' | grep -o '"alias":"[^"]*"'

echo ""
echo "✅ ГОТОВО: https://total-hunter.com"

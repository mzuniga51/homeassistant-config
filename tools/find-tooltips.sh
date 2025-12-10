set -eu
DIR="${1:-/config}"

echo "🔎 Scanning $DIR for tooltip usage…"
echo "   patterns:  'tooltip:'  and  'ha-tooltip'"
echo

grep -RIn -i -E '\btooltip[[:space:]]*:|ha-tooltip' "$DIR" \
  --include='*.yaml' --include='*.yml' --include='*.json' \
  --include='*.js' --include='*.ts' --include='*.css' --include='*.html' \
  --exclude-dir='.git' --exclude-dir='.storage' --exclude-dir='www/community' \
  --exclude-dir='custom_components' --exclude-dir='blueprints' 2>/dev/null \
| tee /config/tooltip-usage.txt || true

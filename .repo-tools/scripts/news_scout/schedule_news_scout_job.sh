#!/bin/bash
#
# Schedule News Scout — daily AI news digest at 08:00 (with hourly retries until 12:00).
# Installs a launchd job that runs news_scout.news_scout.
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
PLIST_NAME="com.user.news-scout.plist"
PLIST_TEMPLATE="$SCRIPT_DIR/$PLIST_NAME.template"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"
CONFIG_FILE="$SCRIPT_DIR/config.yaml"
VENV_PYTHON="$REPO_ROOT/.repo-tools/.venv/bin/python3"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   📰 News Scout Setup${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "Repository:    $REPO_ROOT"
echo "Primary slot:  08:00 daily (retries every hour through 12:00)"
echo ""

if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}❌ config.yaml not found${NC}"
    echo "  cp $SCRIPT_DIR/config.yaml.template $CONFIG_FILE"
    echo "  Edit $CONFIG_FILE and set anthropic_api_key"
    exit 1
fi

if grep -q "YOUR_ANTHROPIC_API_KEY_HERE" "$CONFIG_FILE"; then
    echo -e "${RED}❌ config.yaml still has placeholder anthropic_api_key${NC}"
    echo "  Edit $CONFIG_FILE and set anthropic_api_key to your real key."
    exit 1
fi

# Verify Python venv + deps
if [ ! -x "$VENV_PYTHON" ]; then
    echo -e "${YELLOW}⚠ venv missing at $VENV_PYTHON — creating it...${NC}"
    python3 -m venv "$REPO_ROOT/.repo-tools/.venv"
fi
echo "Installing/updating Python deps..."
"$VENV_PYTHON" -m pip install --quiet --upgrade pip
"$VENV_PYTHON" -m pip install --quiet -r "$SCRIPT_DIR/requirements.txt"

# Generate plist from template, substituting __REPO_ROOT__
mkdir -p "$REPO_ROOT/.repo-tools/logs"
sed "s|__REPO_ROOT__|$REPO_ROOT|g" "$PLIST_TEMPLATE" > "$PLIST_DEST"
echo -e "${GREEN}✓ plist written to $PLIST_DEST${NC}"

# Reload
launchctl unload "$PLIST_DEST" 2>/dev/null || true
launchctl load "$PLIST_DEST"
echo -e "${GREEN}✓ launchd job loaded${NC}"
echo ""
echo "Next steps:"
echo "  • Smoke test:   cd $REPO_ROOT/.repo-tools/scripts && $VENV_PYTHON -m news_scout.news_scout --dry-run"
echo "  • Live test:    cd $REPO_ROOT/.repo-tools/scripts && $VENV_PYTHON -m news_scout.news_scout --force --skip-delay"
echo "  • View logs:    tail -f $REPO_ROOT/.repo-tools/logs/news_scout.log"
echo "  • Unschedule:   launchctl unload $PLIST_DEST"

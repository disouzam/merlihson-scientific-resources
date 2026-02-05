#!/bin/bash
#
# Schedule Telegram Review Uploader
#
# This script installs a launchd job that runs the Telegram uploader
# every day at 11:00 AM. The job will:
# - Check git log for reviews added in the last 24 hours
# - Upload them to appropriate Telegram channels (Hebrew/English)
# - Log all actions
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get absolute path to repo root
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PLIST_NAME="com.user.telegram-review-uploader.plist"
PLIST_TEMPLATE="$REPO_ROOT/.repo-tools/scripts/$PLIST_NAME.template"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"
CONFIG_FILE="$REPO_ROOT/.repo-tools/scripts/telegram_config.yaml"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   📱 Telegram Review Uploader Setup${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Repository: $REPO_ROOT"
echo "Schedule: Every day at 11:00 AM"
echo ""

# Check if config exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}❌ Error: telegram_config.yaml not found!${NC}"
    echo ""
    echo "Please create the config file first:"
    echo -e "  ${YELLOW}1.${NC} cd $REPO_ROOT/.repo-tools/scripts"
    echo -e "  ${YELLOW}2.${NC} cp telegram_config.yaml.template telegram_config.yaml"
    echo -e "  ${YELLOW}3.${NC} Edit telegram_config.yaml with your bot tokens and channel IDs"
    echo ""
    echo "Bot setup instructions:"
    echo "  • Message @BotFather on Telegram to create bots"
    echo "  • Get bot tokens (format: 123456789:ABC...)"
    echo "  • Add bots as admins to your channels"
    echo "  • Get channel IDs (format: -1001234567890)"
    echo ""
    echo "See .repo-tools/docs/TELEGRAM_SETUP.md for detailed instructions"
    exit 1
fi

# Validate config has been filled in
if grep -q "YOUR_.*_HERE" "$CONFIG_FILE"; then
    echo -e "${RED}❌ Error: telegram_config.yaml contains placeholder values!${NC}"
    echo ""
    echo "Please edit the config file and replace all YOUR_*_HERE placeholders"
    echo "with your actual bot tokens and channel IDs."
    echo ""
    echo -e "Edit: ${YELLOW}$CONFIG_FILE${NC}"
    exit 1
fi

# Check Python dependencies
echo -e "${YELLOW}🔍 Checking Python dependencies...${NC}"
if ! python3 -c "import requests, yaml" 2>/dev/null; then
    echo -e "${YELLOW}📦 Installing Python dependencies...${NC}"
    pip3 install requests pyyaml --quiet
    echo -e "${GREEN}✓ Dependencies installed${NC}"
else
    echo -e "${GREEN}✓ Dependencies already installed${NC}"
fi

# Test the script
echo ""
echo -e "${YELLOW}🧪 Testing script...${NC}"
if python3 "$REPO_ROOT/.repo-tools/scripts/telegram_uploader.py" --dry-run --hours 24 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Script test passed${NC}"
else
    echo -e "${RED}❌ Script test failed!${NC}"
    echo "Please check your telegram_config.yaml for errors"
    exit 1
fi

# Ensure LaunchAgents directory exists
mkdir -p "$HOME/Library/LaunchAgents"

# Unload existing job if present
if launchctl list | grep -q "telegram-review-uploader"; then
    echo ""
    echo -e "${YELLOW}⚠️  Existing job found, unloading...${NC}"
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
fi

# Create plist from template
echo ""
echo -e "${YELLOW}📝 Creating launchd configuration...${NC}"
sed "s|REPO_ROOT_PLACEHOLDER|$REPO_ROOT|g" "$PLIST_TEMPLATE" > "$PLIST_DEST"
echo -e "${GREEN}✓ Configuration created${NC}"

# Load job
echo -e "${YELLOW}🚀 Loading job into launchd...${NC}"
launchctl load "$PLIST_DEST"
echo -e "${GREEN}✓ Job loaded successfully${NC}"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}   ✅ Telegram uploader scheduled successfully!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Details:"
echo "  • Runs every day at 11:00 AM"
echo "  • Checks git log for reviews added in last 24 hours"
echo "  • Uploads Hebrew reviews → Hebrew channel"
echo "  • Uploads English reviews → English channel"
echo "  • Automatically splits long messages"
echo "  • Prevents duplicates via dual detection"
echo ""
echo "Logs:"
echo "  • Execution: $REPO_ROOT/.repo-tools/logs/telegram_uploader.log"
echo "  • Errors: $REPO_ROOT/.repo-tools/logs/telegram_uploader_error.log"
echo "  • Upload history: $REPO_ROOT/.repo-tools/logs/telegram_uploads.log"
echo ""
echo "Management:"
echo -e "  • ${BLUE}Test now:${NC}      python3 $REPO_ROOT/.repo-tools/scripts/telegram_uploader.py --dry-run"
echo -e "  • ${BLUE}Run now:${NC}       launchctl start com.user.telegram-review-uploader"
echo -e "  • ${BLUE}View status:${NC}   launchctl list | grep telegram"
echo -e "  • ${BLUE}View logs:${NC}     tail -f $REPO_ROOT/.repo-tools/logs/telegram_uploader.log"
echo -e "  • ${BLUE}Uninstall:${NC}     launchctl unload $PLIST_DEST"
echo ""
echo -e "${YELLOW}💡 Tip:${NC} Reviews committed at 5 AM will be uploaded at 11 AM automatically!"
echo ""

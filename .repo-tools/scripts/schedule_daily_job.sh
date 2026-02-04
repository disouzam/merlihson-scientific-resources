#!/bin/bash
#
# Schedule Daily Review Processing Job
#
# This script installs a launchd job that runs the daily review processor
# every day at 5:00 AM. The job will:
# - Check ~/Downloads for new Review_XXX.docx files
# - Process them (convert to markdown, commit, push)
# - Log all actions to .repo-tools/logs/
#

set -e

# Get absolute path to repo root
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PLIST_NAME="com.user.daily-review-processor.plist"
PLIST_TEMPLATE="$REPO_ROOT/.repo-tools/scripts/$PLIST_NAME.template"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo "📅 Setting up daily review processing job..."
echo ""
echo "Repository: $REPO_ROOT"
echo "Schedule: Every day at 5:00 AM"
echo ""

# Check if template exists
if [ ! -f "$PLIST_TEMPLATE" ]; then
    echo "❌ Error: Template file not found: $PLIST_TEMPLATE"
    exit 1
fi

# Ensure LaunchAgents directory exists
mkdir -p "$HOME/Library/LaunchAgents"

# Unload existing job if present
if launchctl list | grep -q "com.user.daily-review-processor"; then
    echo "⚠️  Existing job found, unloading..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
fi

# Replace placeholder with actual repo path
echo "Creating launchd plist..."
sed "s|REPO_ROOT_PLACEHOLDER|$REPO_ROOT|g" "$PLIST_TEMPLATE" > "$PLIST_DEST"

# Load the job
echo "Loading job into launchd..."
launchctl load "$PLIST_DEST"

echo ""
echo "✅ Daily review processing job installed successfully!"
echo ""
echo "Details:"
echo "  • Runs every day at 5:00 AM"
echo "  • Checks ~/Downloads for new Review_XXX.docx files"
echo "  • Automatically processes, commits, and pushes to GitHub"
echo ""
echo "Logs:"
echo "  • Output: $REPO_ROOT/.repo-tools/logs/daily_processor.log"
echo "  • Errors: $REPO_ROOT/.repo-tools/logs/daily_processor_error.log"
echo ""
echo "Management:"
echo "  • View status:  launchctl list | grep daily-review"
echo "  • Run now:      launchctl start com.user.daily-review-processor"
echo "  • Test script:  $REPO_ROOT/.repo-tools/scripts/daily_review_processor.py --dry-run"
echo "  • Uninstall:    launchctl unload $PLIST_DEST"
echo ""

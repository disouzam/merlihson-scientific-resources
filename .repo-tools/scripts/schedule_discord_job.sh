#!/bin/bash
#
# Discord Review Poster - LaunchAgent Installer
#
# This script installs the Discord poster as a scheduled launchd job
# that runs daily at 12:00 PM and 12:30 PM (backup).
#
# Usage:
#   ./schedule_discord_job.sh install    # Install and start the job
#   ./schedule_discord_job.sh uninstall  # Stop and remove the job
#   ./schedule_discord_job.sh status     # Check job status
#   ./schedule_discord_job.sh logs       # View recent logs
#

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PLIST_TEMPLATE="$SCRIPT_DIR/com.user.discord-review-poster.plist.template"
PLIST_NAME="com.user.discord-review-poster.plist"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_DEST="$LAUNCH_AGENTS_DIR/$PLIST_NAME"
JOB_LABEL="com.user.discord-review-poster"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Functions
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo "  $1"
}

# Install function
install_job() {
    echo ""
    echo "=========================================="
    echo "Installing Discord Review Poster Job"
    echo "=========================================="
    echo ""

    # Check if template exists
    if [ ! -f "$PLIST_TEMPLATE" ]; then
        print_error "Template file not found: $PLIST_TEMPLATE"
        exit 1
    fi

    # Create LaunchAgents directory if it doesn't exist
    if [ ! -d "$LAUNCH_AGENTS_DIR" ]; then
        mkdir -p "$LAUNCH_AGENTS_DIR"
        print_success "Created $LAUNCH_AGENTS_DIR"
    fi

    # Replace REPO_ROOT_PATH with actual path
    sed "s|REPO_ROOT_PATH|$REPO_ROOT|g" "$PLIST_TEMPLATE" > "$PLIST_DEST"
    print_success "Created plist file: $PLIST_DEST"

    # Unload if already loaded
    if launchctl list | grep -q "$JOB_LABEL"; then
        launchctl unload "$PLIST_DEST" 2>/dev/null || true
        print_info "Unloaded existing job"
    fi

    # Load the job
    launchctl load "$PLIST_DEST"
    print_success "Loaded job: $JOB_LABEL"

    echo ""
    print_success "Installation complete!"
    echo ""
    print_info "The Discord poster will run automatically at:"
    print_info "  • 12:00 PM (primary)"
    print_info "  • 12:30 PM (backup)"
    echo ""
    print_info "Logs will be written to:"
    print_info "  $REPO_ROOT/.repo-tools/logs/discord_poster.log"
    echo ""
    print_info "Run './schedule_discord_job.sh status' to check job status"
    echo ""
}

# Uninstall function
uninstall_job() {
    echo ""
    echo "=========================================="
    echo "Uninstalling Discord Review Poster Job"
    echo "=========================================="
    echo ""

    # Unload the job
    if launchctl list | grep -q "$JOB_LABEL"; then
        launchctl unload "$PLIST_DEST" 2>/dev/null || true
        print_success "Unloaded job: $JOB_LABEL"
    else
        print_warning "Job not loaded: $JOB_LABEL"
    fi

    # Remove plist file
    if [ -f "$PLIST_DEST" ]; then
        rm "$PLIST_DEST"
        print_success "Removed plist file: $PLIST_DEST"
    else
        print_warning "Plist file not found: $PLIST_DEST"
    fi

    echo ""
    print_success "Uninstallation complete!"
    echo ""
}

# Status function
check_status() {
    echo ""
    echo "=========================================="
    echo "Discord Review Poster - Job Status"
    echo "=========================================="
    echo ""

    if launchctl list | grep -q "$JOB_LABEL"; then
        print_success "Job is loaded and active"
        echo ""
        print_info "Job details:"
        launchctl list | grep "$JOB_LABEL"
        echo ""

        if [ -f "$PLIST_DEST" ]; then
            print_info "Schedule:"
            print_info "  • 12:00 PM daily (primary)"
            print_info "  • 12:30 PM daily (backup)"
        fi
    else
        print_warning "Job is not loaded"
        echo ""
        print_info "Run './schedule_discord_job.sh install' to install the job"
    fi
    echo ""
}

# View logs function
view_logs() {
    LOG_FILE="$REPO_ROOT/.repo-tools/logs/discord_poster.log"
    ERROR_LOG="$REPO_ROOT/.repo-tools/logs/discord_poster_error.log"

    echo ""
    echo "=========================================="
    echo "Discord Poster - Recent Logs"
    echo "=========================================="
    echo ""

    if [ -f "$LOG_FILE" ]; then
        print_info "Last 20 lines of main log:"
        echo ""
        tail -20 "$LOG_FILE"
        echo ""
    else
        print_warning "Log file not found: $LOG_FILE"
        echo ""
    fi

    if [ -f "$ERROR_LOG" ] && [ -s "$ERROR_LOG" ]; then
        print_warning "Error log (last 20 lines):"
        echo ""
        tail -20 "$ERROR_LOG"
        echo ""
    fi
}

# Test run function
test_run() {
    echo ""
    echo "=========================================="
    echo "Testing Discord Poster (Dry Run)"
    echo "=========================================="
    echo ""

    cd "$REPO_ROOT"
    source .repo-tools/.venv/bin/activate
    python3 .repo-tools/scripts/discord_poster.py --dry-run

    echo ""
    print_success "Test complete!"
    echo ""
}

# Main script
case "${1:-}" in
    install)
        install_job
        ;;
    uninstall)
        uninstall_job
        ;;
    status)
        check_status
        ;;
    logs)
        view_logs
        ;;
    test)
        test_run
        ;;
    *)
        echo ""
        echo "Discord Review Poster - Scheduler"
        echo ""
        echo "Usage:"
        echo "  $0 install     Install and start the scheduled job"
        echo "  $0 uninstall   Stop and remove the scheduled job"
        echo "  $0 status      Check if the job is running"
        echo "  $0 logs        View recent logs"
        echo "  $0 test        Run a dry-run test"
        echo ""
        exit 1
        ;;
esac

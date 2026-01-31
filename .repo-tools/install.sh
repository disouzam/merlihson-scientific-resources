#!/bin/bash
#
# Repository Automator - Installation Script
#
# This script sets up the repo_automator tool:
# 1. Creates a Python virtual environment
# 2. Installs dependencies
# 3. Creates convenience wrapper scripts
#
# Usage:
#   cd .repo-tools && ./install.sh
#
# After installation:
#   ./repo-auto run          # Run full automation
#   ./repo-auto watch        # Start file watcher
#   ./repo-auto --help       # Show all options
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   📦 Repository Automator - Installation${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo

# Check Python version
echo -e "${YELLOW}🔍 Checking Python version...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}❌ Python not found. Please install Python 3.8 or higher.${NC}"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "   Python version: ${GREEN}$PYTHON_VERSION${NC}"

# Create virtual environment
VENV_DIR="$SCRIPT_DIR/.venv"
if [ -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}🔄 Virtual environment exists, updating...${NC}"
else
    echo -e "${YELLOW}📁 Creating virtual environment...${NC}"
    $PYTHON_CMD -m venv "$VENV_DIR"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo -e "${YELLOW}⬆️  Upgrading pip...${NC}"
pip install --upgrade pip --quiet

# Install dependencies
echo -e "${YELLOW}📦 Installing dependencies...${NC}"
pip install -r requirements.txt --quiet

# Create convenience wrapper script
echo -e "${YELLOW}🔧 Creating wrapper script...${NC}"

cat > "$SCRIPT_DIR/repo-auto" << 'WRAPPER'
#!/bin/bash
# Convenience wrapper for repo_automator
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$SCRIPT_DIR/.venv/bin/activate"
python -m repo_automator "$@"
WRAPPER

chmod +x "$SCRIPT_DIR/repo-auto"

# Create a root-level symlink for convenience
REPO_ROOT="$SCRIPT_DIR/.."
if [ ! -L "$REPO_ROOT/repo-auto" ]; then
    echo -e "${YELLOW}🔗 Creating symlink in repo root...${NC}"
    ln -sf .repo-tools/repo-auto "$REPO_ROOT/repo-auto"
fi

echo
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}   ✅ Installation Complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo
echo -e "Usage:"
echo -e "  ${BLUE}./repo-auto run${NC}           # Run full automation"
echo -e "  ${BLUE}./repo-auto run --dry-run${NC} # Preview changes"
echo -e "  ${BLUE}./repo-auto scan${NC}          # Just scan, no updates"
echo -e "  ${BLUE}./repo-auto watch${NC}         # Start file watcher"
echo -e "  ${BLUE}./repo-auto --help${NC}        # Show all options"
echo
echo -e "${YELLOW}SAFETY: This tool NEVER deletes files.${NC}"
echo -e "${YELLOW}It only updates READMEs and metadata.${NC}"
echo

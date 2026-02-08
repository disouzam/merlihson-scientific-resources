# Skills Management Guide

## Overview

This directory contains skill definitions that extend Claude Code's capabilities for managing the scientific review automation system.

## Skills Maintenance Principle

**CRITICAL: When system changes occur, ALL relevant skills and documentation MUST be updated automatically.**

### What Requires Skill Updates

When any of the following changes occur, update all affected skills and documentation:

1. **Schedule Changes**
   - Processing times (daily_processor)
   - Upload times (telegram_uploader)
   - Posting times (discord_poster)
   - Backup run times

2. **Workflow Changes**
   - New steps in the automation pipeline
   - Modified file paths or directories
   - New configuration files
   - Changed API endpoints

3. **Feature Additions**
   - New automation scripts
   - New channels or platforms
   - New validation rules
   - New safety features

4. **Configuration Changes**
   - Updated config file locations
   - New config parameters
   - Changed default values
   - Modified environment requirements

### Files That Must Be Updated Together

When making changes, always check and update:

1. **Skills** (`.repo-tools/skills/`)
   - `discord-post.md` - Discord automation commands
   - Any skill that references the changed component

2. **Documentation** (`.repo-tools/docs/`)
   - `IMPLEMENTATION_COMPLETE.md` - Complete system overview
   - `DISCORD_AUTOMATION.md` - Discord-specific documentation
   - `TELEGRAM_SETUP.md` - Telegram-specific documentation
   - Any doc that describes the changed workflow

3. **Configuration Templates** (`.repo-tools/scripts/`)
   - `*.plist.template` files for launchd jobs
   - Any template that embeds the changed values

4. **Plan Files** (`~/.claude/plans/`)
   - Update any active plan files if they reference the changed system

### Update Checklist

When making a system change, use this checklist:

- [ ] Make the primary change (code, config, schedule)
- [ ] Update all skill files that reference the change
- [ ] Update all documentation files with the new information
- [ ] Update configuration templates
- [ ] Verify the change is reflected consistently across all files
- [ ] Test that the updated skills work correctly

### Example: Schedule Change

When adding new processing times (like 8 AM and 9 AM backup runs):

1. ✅ Update the active plist file (`~/Library/LaunchAgents/*.plist`)
2. ✅ Update the plist template (`.repo-tools/scripts/*.plist.template`)
3. ✅ Update skill workflow section (`discord-post.md`)
4. ✅ Update documentation workflows (`IMPLEMENTATION_COMPLETE.md`, `DISCORD_AUTOMATION.md`)
5. ✅ Reload the launchd job
6. ✅ Verify all references to the schedule are consistent

## Skill Format

Each skill should include:

1. **Frontmatter** - Name and description
2. **User Commands** - Natural language examples users can say
3. **What This Skill Does** - Clear explanation of functionality
4. **Implementation Details** - Technical specifics
5. **Action Instructions** - Step-by-step execution guide
6. **Error Scenarios** - Troubleshooting information
7. **Integration** - How it fits in the complete workflow

## Testing Skills

After updating skills:

1. Read the skill file to verify markdown formatting
2. Check that all referenced files and paths exist
3. Verify schedule times are consistent across all documents
4. Test any changed commands manually
5. Confirm automation runs as expected

## Current Skills

### discord-post.md
Manages Discord posting automation, Telegram link handling, and Substack scraping.

**Key sections to update when:**
- Schedule changes → "Integration with Daily Workflow"
- New commands → "User Commands" and "Action Instructions"
- Configuration changes → "Implementation Details" and "Configuration"
- Error handling → "Error Scenarios & Solutions"

## Best Practices

1. **Consistency** - Use the same terminology across all skills and docs
2. **Completeness** - Don't leave any document partially updated
3. **Testing** - Always test after making changes
4. **Timestamps** - Include "Last Updated" dates when making significant changes
5. **Clarity** - Write for future maintainers who may not know the context

## Automation Principle

**"Update Once, Update Everywhere"**

When you change one component of the system, immediately identify and update all related skills, documentation, and configuration files. This ensures users always get consistent, accurate information regardless of which skill or doc they consult.

---

**Last Updated:** 2026-02-08
**Maintainer:** Claude Code Automation

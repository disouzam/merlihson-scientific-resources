# Skills Management Guide

---

## 🤖 INSTRUCTIONS FOR CLAUDE CODE

**READ THIS FIRST - MANDATORY BEHAVIOR:**

When you make ANY system change (schedules, workflows, configs, features), you MUST automatically:

1. ✅ **Update ALL related skills** in `.repo-tools/skills/`
2. ✅ **Update ALL related documentation** in `.repo-tools/docs/`
3. ✅ **Update configuration templates** in `.repo-tools/scripts/`
4. ✅ **Commit and push** all changes together

**DO NOT WAIT to be asked.** This is required behavior for every system modification.

**DO NOT SKIP any related file.** Check the "Files That Must Be Updated Together" section below.

**DO NOT push partial updates.** All related files must be updated in a single commit.

If you modify a schedule, workflow, or configuration, you have NOT completed the task until all skills and documentation reflect the change.

---

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

### arxiv-to-repo.md
Scans Chrome tabs for arxiv papers, downloads PDFs to `learning-materials/arxiv-papers/`, closes processed tabs, and commits/pushes. CLI alias: `arxiv-to-repo`.

**Key sections to update when:**
- Destination folder changes → "Implementation Details"
- Naming convention changes → "Implementation Details"
- New flags/options → "Action Instructions" and CLAUDE.md Commands section

### discord-post.md
Manages Discord posting automation, Telegram link handling, and Substack scraping.

**Key sections to update when:**
- Schedule changes → "Integration with Daily Workflow"
- New commands → "User Commands" and "Action Instructions"
- Configuration changes → "Implementation Details" and "Configuration"
- Error handling → "Error Scenarios & Solutions"

### paper-recommender (no skill file — runs autonomously)
Daily arXiv paper recommender bot. Fetches new papers from arXiv, ranks by relevance to Mike's interests using Claude Haiku, sends top 10 to Telegram. Cross-machine dedup via git-tracked `last_run.txt`.

**Location:** `.repo-tools/scripts/paper_recommender/`
**Config:** `.repo-tools/scripts/paper_recommender/config.yaml` (gitignored)
**Schedule:** launchd `RunAtLoad` (triggers on first login/wake, runs once per day)

**Key sections to update when:**
- arXiv categories change → `config.yaml` and `config.yaml.template`
- Telegram channel changes → `config.yaml`
- Model changes → `config.yaml`
- Schedule changes → `com.user.paper-recommender.plist.template`

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

## 🔄 Mandatory Workflow for System Changes

**FOR CLAUDE CODE: This is your standard operating procedure. Follow it automatically.**

```
Step 1: Make the primary change
        ↓
Step 2: Identify all related files using the checklist above
        ↓
Step 3: Update ALL skills that reference the change
        ↓
Step 4: Update ALL docs that reference the change
        ↓
Step 5: Update ALL templates that embed the change
        ↓
Step 6: Stage all changes: git add <all modified files>
        ↓
Step 7: Commit with descriptive message
        ↓
Step 8: Push to GitHub
        ↓
Step 9: Confirm to user: "All pushed and documentation updated"
```

**Example conversation:**
```
User: "Add 8 AM and 9 AM backup runs"

Claude:
1. Updates plist file ✅
2. Updates plist template ✅
3. Updates discord-post.md skill ✅
4. Updates IMPLEMENTATION_COMPLETE.md ✅
5. Updates DISCORD_AUTOMATION.md ✅
6. Updates TELEGRAM_SETUP.md ✅
7. Updates scripts/README.md ✅
8. Commits all changes ✅
9. Pushes to GitHub ✅
10. Reports: "All pushed and documentation updated" ✅

NO reminder needed. This happens automatically.
```

---

**Last Updated:** 2026-02-21
**Maintainer:** Claude Code Automation

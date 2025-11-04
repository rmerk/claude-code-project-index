# Story 3.1: Smart Configuration Presets with Auto-Detection

Status: backlog

## Story

As a developer,
I want the indexer to automatically detect my project size and create an optimal configuration,
So that Epic 2 features are enabled by default without requiring manual configuration.

## Acceptance Criteria

1. Three preset templates created (small/medium/large) in `~/.claude-code-project-index/templates/`
2. First `/index` run auto-detects project size and creates `.project-index.json` with appropriate preset
3. Config includes metadata (`_preset`, `_generated`) for upgrade tracking
4. Subsequent runs detect if project crossed preset boundaries (small→medium, medium→large)
5. Interactive prompt asks user before upgrading config (with backup to `.project-index.json.backup`)
6. User can accept upgrade (new preset applied) or decline (keeps existing config)
7. `--no-prompt` flag skips interactive prompts for CI/automation
8. `--upgrade-to=preset` flag forces specific preset upgrade
9. Clear messaging explains detected size, current preset, and recommended preset
10. README updated with preset documentation and upgrade behavior

## Tasks / Subtasks

- [x] Design Preset Specifications (AC: #1)
  - [x] Define small preset: <100 files, single-file mode, minimal config
  - [x] Define medium preset: 100-5000 files, auto-split at 500, tiered docs, relevance scoring
  - [x] Define large preset: 5000+ files, forced split, aggressive optimization, top-3 modules
  - [x] Document preset selection criteria (file count thresholds)
  - [x] Design metadata format (_preset, _generated fields)

- [ ] Create Preset Template Files (AC: #1)
  - [ ] Create `templates/small.json` with minimal configuration
  - [ ] Create `templates/medium.json` with balanced Epic 2 features
  - [ ] Create `templates/large.json` with aggressive Epic 2 optimizations
  - [ ] Add metadata fields to all templates (_preset, _generated: "auto")
  - [ ] Validate all templates are valid JSON
  - [ ] Test templates load correctly in project_index.py

- [ ] Implement Auto-Detection Logic (AC: #2, #3, #4)
  - [ ] Create `auto_detect_preset(file_count)` function
    - [ ] Return "small" for <100 files
    - [ ] Return "medium" for 100-4999 files
    - [ ] Return "large" for 5000+ files
  - [ ] Create `load_preset_template(preset_name)` function
    - [ ] Load from `~/.claude-code-project-index/templates/{preset}.json`
    - [ ] Replace `_generated: "auto"` with current timestamp
    - [ ] Graceful fallback if template not found
  - [ ] Create `detect_preset_from_config(config)` function
    - [ ] Check `_preset` metadata field first
    - [ ] Fallback to threshold heuristic if no metadata
    - [ ] Return "small", "medium", or "large"

- [ ] Modify load_configuration() Function (AC: #2, #3, #4, #5, #6)
  - [ ] Count files using `len(get_git_files())`
  - [ ] Determine current preset with `auto_detect_preset(file_count)`
  - [ ] **If no .project-index.json exists:**
    - [ ] Load preset template
    - [ ] Save to .project-index.json with metadata
    - [ ] Print: "📊 Created .project-index.json with {preset} preset"
    - [ ] Print: "   {file_count} files detected"
    - [ ] Return config
  - [ ] **If .project-index.json exists:**
    - [ ] Load existing config
    - [ ] Detect original preset with `detect_preset_from_config()`
    - [ ] Compare original preset vs current preset
    - [ ] If same: return config (no changes)
    - [ ] If different: trigger upgrade prompt (see next task)

- [ ] Implement Interactive Upgrade Prompt (AC: #5, #6)
  - [ ] Print warning header: "⚠️  Project size changed significantly:"
  - [ ] Show file count progression
  - [ ] Show current preset vs recommended preset
  - [ ] Print: "Upgrade .project-index.json to {preset} preset?"
  - [ ] Print: "(Current config will be backed up to .project-index.json.backup)"
  - [ ] Prompt: "Upgrade? [Y/n]: "
  - [ ] **If user accepts (y/yes/enter):**
    - [ ] Backup existing config with `shutil.copy()` to `.project-index.json.backup`
    - [ ] Load new preset template
    - [ ] Save new config to .project-index.json
    - [ ] Print: "✅ Backup saved: .project-index.json.backup"
    - [ ] Print: "✅ Upgraded to {preset} preset"
    - [ ] Print: "   Review changes: diff .project-index.json.backup .project-index.json"
    - [ ] Return new config
  - [ ] **If user declines (n/no):**
    - [ ] Print: "Keeping existing config"
    - [ ] Return existing config unchanged

- [ ] Add Command-Line Flags (AC: #7, #8)
  - [ ] Implement `--no-prompt` flag
    - [ ] Check `'--no-prompt' in sys.argv`
    - [ ] Skip interactive prompt, auto-upgrade silently
    - [ ] Print: "Auto-upgrading (--no-prompt mode)"
  - [ ] Implement `--upgrade-to=small|medium|large` flag
    - [ ] Parse flag value from sys.argv
    - [ ] Validate preset name (small/medium/large)
    - [ ] Force specific preset regardless of file count
    - [ ] Create backup and upgrade
    - [ ] Print: "Forcing upgrade to {preset} preset"
  - [ ] Implement `--dry-run` flag (optional)
    - [ ] Show what would happen without making changes
    - [ ] Print detected preset and exit

- [ ] Update install.sh (AC: #1)
  - [ ] Add template directory creation after file installation (line ~148)
  - [ ] Create `templates/` directory: `mkdir -p "$INSTALL_DIR/templates"`
  - [ ] Generate `templates/small.json` with heredoc
  - [ ] Generate `templates/medium.json` with heredoc
  - [ ] Generate `templates/large.json` with heredoc
  - [ ] Print: "✓ Configuration templates created"
  - [ ] Test install.sh on clean system

- [ ] Documentation (AC: #9, #10)
  - [ ] Add "Configuration Presets" section to README
    - [ ] Document small preset (when to use, what's enabled)
    - [ ] Document medium preset (default, recommended)
    - [ ] Document large preset (5000+ files, aggressive optimization)
  - [ ] Add "Auto-Detection and Upgrades" section
    - [ ] Explain first-run behavior (auto-detects, creates config)
    - [ ] Explain upgrade prompts (when triggered, how to respond)
    - [ ] Document backup behavior (.project-index.json.backup)
  - [ ] Add "Command-Line Flags" section
    - [ ] Document `--no-prompt` for CI/automation
    - [ ] Document `--upgrade-to=preset` for manual upgrades
    - [ ] Document `--dry-run` for preview
  - [ ] Add FAQ entries
    - [ ] "How do I force a specific preset?"
    - [ ] "Can I customize the preset after creation?"
    - [ ] "What happens if I delete .project-index.json?"
  - [ ] Update usage examples with preset workflow

- [ ] Testing (All ACs)
  - [ ] Unit tests for auto_detect_preset()
    - [ ] Test 50 files → "small"
    - [ ] Test 99 files → "small"
    - [ ] Test 100 files → "medium"
    - [ ] Test 4999 files → "medium"
    - [ ] Test 5000 files → "large"
    - [ ] Test 10000 files → "large"
  - [ ] Unit tests for load_preset_template()
    - [ ] Test loading each preset (small/medium/large)
    - [ ] Test _generated timestamp replacement
    - [ ] Test graceful fallback if template missing
    - [ ] Test invalid JSON handling
  - [ ] Unit tests for detect_preset_from_config()
    - [ ] Test config with _preset metadata
    - [ ] Test config without metadata (threshold heuristic)
    - [ ] Test edge cases (threshold=100, 1000)
  - [ ] Integration tests for load_configuration()
    - [ ] Test first run (no config) → creates small preset (50 files)
    - [ ] Test first run (no config) → creates medium preset (1000 files)
    - [ ] Test first run (no config) → creates large preset (6000 files)
    - [ ] Test upgrade prompt (small→medium boundary crossing)
    - [ ] Test upgrade prompt (medium→large boundary crossing)
    - [ ] Test user accepts upgrade (backup created, new config saved)
    - [ ] Test user declines upgrade (existing config unchanged)
  - [ ] Command-line flag tests
    - [ ] Test --no-prompt skips interactive prompt
    - [ ] Test --upgrade-to=large forces large preset
    - [ ] Test --dry-run shows preview without changes
  - [ ] Install.sh integration tests
    - [ ] Test templates/ directory created
    - [ ] Test all 3 preset files exist
    - [ ] Test templates are valid JSON
  - [ ] End-to-end workflow tests
    - [ ] Install on clean system → templates created
    - [ ] Run /index in 50-file project → small preset
    - [ ] Add 500 files, run /index → upgrade prompt → accept → medium preset
    - [ ] Add 5000 files, run /index → upgrade prompt → decline → keeps medium
    - [ ] Verify backup file created (.project-index.json.backup)

## Dev Notes

### Architecture Alignment

**From Epic 2 Retrospective (Action Item 2):**

This story implements the critical production-readiness gap identified in the Epic 2 retrospective:
- **Problem:** Epic 2 features (tiered docs, relevance scoring, impact analysis) exist but disabled by default
- **Root Cause:** No smart configuration system - users must manually configure to enable features
- **Solution:** Auto-detect project size, apply appropriate preset with all Epic 2 features enabled
- **User Impact:** Zero-config experience - Epic 2 features "just work" out of the box

**Design Philosophy:**
- **Smart defaults > Manual configuration** - Most users shouldn't need to touch config
- **Interactive prompts > Silent changes** - Build trust, prevent confusion
- **Backups mandatory** - Any automatic file modification creates backup first
- **User control preserved** - Can decline upgrades, force specific presets, customize after creation

**Preset Selection Criteria:**

| Preset | File Count | Mode | Threshold | Features Enabled |
|--------|-----------|------|-----------|------------------|
| **Small** | <100 | single | 100 | Minimal (fast, simple) |
| **Medium** | 100-4999 | auto | 500 | Tiered docs, relevance scoring (balanced) |
| **Large** | 5000+ | split | 1000 | All Epic 2 features (aggressive optimization) |

**Why These Thresholds:**
- **100 files**: Small projects don't benefit from split architecture or tiered docs
- **5000 files**: Large projects need aggressive optimization (top-3 modules, strict tiering)
- **Medium is default**: Most projects fall in 100-5000 range, need balanced approach

**Configuration Lifecycle:**

```
First Run (No .project-index.json):
1. Count files with get_git_files()
2. Determine preset (small/medium/large)
3. Load template from ~/.claude-code-project-index/templates/{preset}.json
4. Save to .project-index.json with metadata (_preset, _generated)
5. User can now customize if desired

Subsequent Runs (Has .project-index.json):
1. Count files
2. Determine current appropriate preset
3. Read existing config, extract original preset from metadata
4. If presets match: Use existing config (no changes)
5. If presets differ:
   a. Show upgrade prompt with details
   b. User accepts: Backup → Load new preset → Save → Return new config
   c. User declines: Return existing config unchanged
```

**Metadata Design:**

```json
{
  "_preset": "medium",           // Which preset this config came from
  "_generated": "2025-11-04T...", // When it was created
  "mode": "auto",                 // Actual config starts here
  "threshold": 500,
  ...
}
```

Metadata enables:
- Detecting which preset a config originated from (for upgrade detection)
- Tracking when config was created (for troubleshooting)
- Distinguishing auto-generated from user-customized configs

### Learnings from Epic 2 Retrospective

**Key Insights:**

1. **Epic 2 delivered all features but they weren't accessible**
   - Tiered docs code exists but requires doc_tiers config
   - Relevance scoring exists but requires relevance_scoring config
   - Users shouldn't need deep config knowledge to use Epic 2

2. **Ryan's feedback: "I want it to use our enhanced indexing, not the default"**
   - Target users are working with medium-to-large projects (500+ files)
   - They expect Epic 2 features enabled by default
   - Default should be "medium" preset with full feature set

3. **Configuration needs lifecycle management**
   - Projects grow from small → medium → large over time
   - Config should adapt as project scales
   - Interactive prompts prevent surprising users with silent changes

4. **User control is critical**
   - Auto-detection is smart default, not forced behavior
   - Users can decline upgrades
   - Users can force specific presets with flags
   - Users can customize config after creation

**Integration Points:**

- **Epic 1 (Split Architecture)**: Presets use mode="auto" or mode="split" from Story 1.8
- **Epic 2 (Enhanced Intelligence)**: Presets enable tiered docs (2.1-2.2), relevance scoring (2.7), impact analysis (2.8)
- **Story 1.8**: Reuses existing load_configuration() pattern, extends with auto-detection
- **Action Item 1 (MCP Installation)**: Pairs with this - both are production-readiness work

### Project Structure Notes

**Files to Create:**
- `~/.claude-code-project-index/templates/small.json` - Small project preset
- `~/.claude-code-project-index/templates/medium.json` - Medium project preset (DEFAULT)
- `~/.claude-code-project-index/templates/large.json` - Large project preset
- `scripts/test_smart_presets.py` - Unit tests for preset logic

**Files to Modify:**
- `scripts/project_index.py` - Add auto-detection functions, modify load_configuration()
- `install.sh` - Add template creation after file installation (~line 148)
- `README.md` - Add "Configuration Presets" and "Auto-Detection" sections

**Dependencies:**
- Existing: `get_git_files()` from index_utils.py (for file counting)
- Existing: `load_configuration()` pattern from Story 1.8
- New: `shutil` module for backup creation
- New: `sys.argv` parsing for command-line flags

**Data Flow:**

```
User runs /index in project
    ↓
load_configuration() called
    ↓
Count files with get_git_files()
    ↓
auto_detect_preset(file_count) → "small" | "medium" | "large"
    ↓
Check if .project-index.json exists?
    ↓
NO: First run
    ↓
load_preset_template(preset) → Load from templates/{preset}.json
    ↓
Save to .project-index.json with metadata
    ↓
Return config

YES: Existing config
    ↓
Load .project-index.json
    ↓
detect_preset_from_config(config) → original preset
    ↓
Compare: original preset vs current preset
    ↓
Same? → Return config (no changes)
Different? → Upgrade prompt
    ↓
User accepts? → Backup → Load new preset → Save → Return
User declines? → Return existing config
```

### References

- [Epic 2 Retrospective](docs/retrospectives/epic-2-retro-2025-11-04.md) - Action Item 2 source
- [Story 1.8: Configuration and Documentation](docs/stories/1-8-configuration-and-documentation.md) - load_configuration() pattern
- [Epic 2: Enhanced Intelligence](docs/epics.md#epic-2-enhanced-intelligence--developer-tools) - Features to enable by default
- [config.yaml](bmad/bmm/config.yaml) - Existing config format reference

## Dev Agent Record

### Context Reference

- Story Context XML: (to be created by story-context workflow)

### Agent Model Used

(To be filled during implementation)

### Debug Log References

(To be filled during implementation)

### Completion Notes List

(To be filled during implementation)

### File List

**Files to Create:**
- `~/.claude-code-project-index/templates/small.json`
- `~/.claude-code-project-index/templates/medium.json`
- `~/.claude-code-project-index/templates/large.json`
- `scripts/test_smart_presets.py`

**Files to Modify:**
- `scripts/project_index.py`
- `install.sh`
- `README.md`

### Change Log

**2025-11-04** - Story 3.1 Created
- Created story file for Smart Configuration Presets
- Extracted requirements from Epic 2 Retrospective Action Item 2
- Defined 10 acceptance criteria with corresponding tasks (8 task categories, 70+ subtasks total)
- Incorporated learnings from Epic 2 retrospective (default config matters, user control critical)
- Documented three preset specifications (small/medium/large)
- Defined configuration lifecycle (first run, subsequent runs, upgrade prompts)
- Outlined metadata design (_preset, _generated fields)
- Referenced Story 1.8 for load_configuration() pattern
- Story status: backlog → drafted

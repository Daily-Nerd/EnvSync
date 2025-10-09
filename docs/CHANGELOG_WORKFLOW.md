# Changelog Management Workflow

TripWire uses a **hybrid approach** for changelog management: manual curation with automated validation and extraction.

## Philosophy

We maintain a **manually curated** CHANGELOG.md following the ["Keep a Changelog"](https://keepachangelog.com/en/1.0.0/) format because:

1. **Quality over automation**: Library users need detailed explanations, code examples, and design rationale
2. **User focus**: Changelog entries explain "why" and "how to use", not just "what changed"
3. **Human judgment**: Breaking changes and migration steps require careful human explanation
4. **Project scale**: With 3-4 releases per year, manual maintenance is sustainable

Automation handles validation and distribution, ensuring consistency without sacrificing quality.

---

## Release Workflow

### 1. During Development

As you develop features, keep notes of changes but **don't update CHANGELOG.md yet**. Focus on:
- Writing clear commit messages
- Documenting breaking changes in PR descriptions
- Noting user-facing impacts

### 2. Pre-Release: Update CHANGELOG.md

When preparing a release (e.g., v0.5.0), manually update CHANGELOG.md:

```bash
# Edit CHANGELOG.md
vim CHANGELOG.md
```

**Required structure:**

```markdown
## [Unreleased]

## [0.5.0] - 2025-10-15

### Added

- **Feature Name**: Brief description with user benefit
  - Sub-feature details
  - Code example if relevant

### Changed

- Description of modifications to existing features
- Backward compatibility notes

### Fixed

- Bug fix descriptions with context

### Technical Details

- Test coverage statistics
- Architecture changes
- Performance improvements

### Design Decisions

- Rationale for major technical choices
- Trade-offs explained
```

**Best practices:**
- Use **bold** for feature names
- Include code examples for API changes
- Explain breaking changes with migration steps
- Add "Technical Details" for developer context
- Document design decisions for major features

### 3. Update Version Links

The comparison links at the bottom of CHANGELOG.md can be updated manually or with automation:

```bash
# Automatic (recommended)
.github/scripts/update_changelog_links.sh 0.5.0 0.4.0

# Or edit manually:
[Unreleased]: https://github.com/Daily-Nerd/TripWire/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/Daily-Nerd/TripWire/compare/v0.4.0...v0.5.0
```

### 4. Commit and Push

```bash
git add CHANGELOG.md
git commit -m "Update CHANGELOG for v0.5.0"
git push origin main
```

### 5. Automated Release

When you push a version tag, CI automatically:

1. **Validates CHANGELOG.md** exists and has content for the version
2. **Extracts release notes** from CHANGELOG.md for GitHub release
3. **Creates GitHub release** with extracted notes
4. **Publishes to PyPI**

```bash
# Create and push tag
git tag -a v0.5.0 -m "Release v0.5.0"
git push origin v0.5.0
```

---

## Automation Scripts

### 1. Validate CHANGELOG.md

**Script:** `.github/scripts/validate_changelog.sh`

**Usage:**
```bash
.github/scripts/validate_changelog.sh 0.5.0
```

**Checks:**
- Version header exists: `## [0.5.0]`
- Version has content (not empty)
- Version link exists (warning if missing)

**When it runs:**
- Automatically in CI during `validate-release` job
- Before any release is published

### 2. Extract Release Notes

**Script:** `.github/scripts/extract_changelog.sh`

**Usage:**
```bash
.github/scripts/extract_changelog.sh 0.5.0 > RELEASE_NOTES.md
```

**Output:**
- Extracts version-specific section from CHANGELOG.md
- Adds installation instructions
- Adds quick start code example
- Formats for GitHub release body

**When it runs:**
- Automatically in `create-release` job
- Generates content for GitHub release page

### 3. Update Version Links

**Script:** `.github/scripts/update_changelog_links.sh`

**Usage:**
```bash
# With previous version
.github/scripts/update_changelog_links.sh 0.5.0 0.4.0

# Auto-detect previous version from git
.github/scripts/update_changelog_links.sh 0.5.0
```

**Actions:**
- Updates `[Unreleased]` link to compare against new version
- Adds new version comparison link
- Backs up original file

**When to use:**
- Optionally after updating CHANGELOG.md
- Not required (can edit manually)

---

## CI/CD Integration

### Release Pipeline Changes

The release workflow (`.github/workflows/release.yml`) includes:

**1. Changelog Validation (added to `validate-release` job):**
```yaml
- name: Validate CHANGELOG.md
  run: |
    chmod +x .github/scripts/validate_changelog.sh
    .github/scripts/validate_changelog.sh ${{ steps.version.outputs.version }}
```

**2. Release Notes Extraction (in `create-release` job):**
```yaml
- name: Extract release notes from CHANGELOG.md
  id: changelog
  run: |
    chmod +x .github/scripts/extract_changelog.sh
    .github/scripts/extract_changelog.sh ${{ needs.validate-release.outputs.version }} > RELEASE_NOTES.md
```

**3. GitHub Release Creation:**
```yaml
- name: Create Release
  uses: softprops/action-gh-release@v2
  with:
    body_path: RELEASE_NOTES.md  # Uses extracted changelog
```

---

## Common Scenarios

### Scenario 1: Regular Release

```bash
# 1. Update CHANGELOG.md with new version section
vim CHANGELOG.md

# 2. Commit changes
git add CHANGELOG.md
git commit -m "Update CHANGELOG for v0.5.0"

# 3. Create and push tag (triggers release)
git tag -a v0.5.0 -m "Release v0.5.0"
git push origin v0.5.0

# 4. CI handles the rest automatically
```

### Scenario 2: Pre-release (RC)

```bash
# 1. Update CHANGELOG.md with RC version
vim CHANGELOG.md  # Add ## [0.5.0-rc1] section

# 2. Commit and tag
git add CHANGELOG.md
git commit -m "Update CHANGELOG for v0.5.0-rc1"
git tag -a v0.5.0-rc1 -m "Release v0.5.0-rc1 (pre-release)"
git push origin v0.5.0-rc1

# 3. CI publishes to Test PyPI only
```

### Scenario 3: Fixing Forgotten Changelog Entry

```bash
# If you pushed a tag but forgot to update CHANGELOG.md:

# 1. Delete the tag (if release hasn't completed)
git tag -d v0.5.0
git push origin :refs/tags/v0.5.0

# 2. Update CHANGELOG.md
vim CHANGELOG.md

# 3. Commit and re-tag
git add CHANGELOG.md
git commit -m "Add missing CHANGELOG entry for v0.5.0"
git tag -a v0.5.0 -m "Release v0.5.0"
git push origin main
git push origin v0.5.0
```

### Scenario 4: Hotfix Release

```bash
# For urgent bugfix releases:

# 1. Minimal CHANGELOG entry is acceptable
vim CHANGELOG.md
# Add:
## [0.4.1] - 2025-10-10
### Fixed
- Critical bug in config parser causing crashes on Windows

# 2. Release immediately
git add CHANGELOG.md
git commit -m "Hotfix: Update CHANGELOG for v0.4.1"
git tag -a v0.4.1 -m "Hotfix: v0.4.1"
git push origin v0.4.1
```

---

## Quality Standards

### Excellent Changelog Entry Example

```markdown
## [0.4.0] - 2025-10-09

### Added

- **Type Inference from Annotations**: TripWire now automatically infers types from variable annotations - no need to specify `type=` twice!
  ```python
  # Before (still works)
  PORT: int = env.require("PORT", type=int, min_val=1, max_val=65535)

  # Now (recommended)
  PORT: int = env.require("PORT", min_val=1, max_val=65535)
  ```
  - Supports `int`, `float`, `bool`, `str`, `list`, `dict`
  - Handles `Optional[T]` annotations (extracts `T`)
  - Works with module-level and function-level variables
  - Falls back to `str` if type cannot be inferred

### Design Decisions

- **Why .env + TOML only?** Covers 95% of Python projects. YAML has security risks, JSON has poor UX for env vars.
```

**What makes this excellent:**
- Starts with user benefit ("no need to specify `type=` twice!")
- Shows before/after code examples
- Lists technical capabilities
- Explains design rationale
- User-focused language

### Poor Changelog Entry Example

```markdown
## [0.4.0] - 2025-10-09

### Added
- Type inference
- Config diff command
- TOML support

### Changed
- Updated type system
```

**Why this is poor:**
- No context or explanation
- No code examples
- No user benefit explained
- Too terse for library users

---

## Why Not Full Automation?

We evaluated and rejected these approaches:

### Conventional Commits + Auto-generation

**Evaluated tools:** conventional-changelog, semantic-release, git-changelog

**Rejection reasons:**
1. **Current commits are inconsistent** (~40% use `feat:`/`fix:`, 60% don't)
2. **Generated content is low-quality** for library documentation
3. **No code examples** or design rationale
4. **Breaking changes need human explanation**
5. **Migration steps can't be automated**

**When it might work:** High-volume projects with 10+ releases/year and consistent conventional commits

### GitHub Release Notes Auto-generation

**Feature:** GitHub's "Auto-generate release notes" based on PR titles

**Rejection reasons:**
1. **PR-focused, not user-focused** (internal language)
2. **No grouping** by change type (Added/Changed/Fixed)
3. **No code examples or design context**
4. **Includes internal refactors** not relevant to users

**When it might work:** Internal tools or projects where commit log = changelog

### Full Manual (No Automation)

**Approach:** Write changelog entries at release time, manually copy to GitHub

**Rejection reasons:**
1. **Manual copy-paste is error-prone**
2. **Inconsistent formatting** across releases
3. **No validation** that changelog was updated
4. **Wastes time** on mechanical steps

**When it might work:** Never - some automation always helps

---

## Future Enhancements

Potential improvements for high-volume release scenarios:

### 1. Changelog Template Command

```bash
# Generate template for next release
tripwire changelog template --version 0.5.0

# Output:
## [0.5.0] - 2025-10-15

### Added

### Changed

### Fixed

### Technical Details
```

### 2. PR-Based Changelog Fragments

If release velocity increases, consider:
- Each PR includes `.changelog/0.5.0-feature-name.md` fragment
- At release time, merge fragments into CHANGELOG.md
- Tools: towncrier, scriv

**Implementation:**
```bash
# Developer adds fragment with PR
echo "- **New feature**: Description" > .changelog/0.5.0-feat-xyz.md

# At release time:
towncrier build --version 0.5.0  # Merges all fragments
```

**When to adopt:** When you have 5+ contributors and 10+ releases/year

### 3. AI-Assisted Changelog Generation

- Use LLM to draft entries from git log + PR descriptions
- Human reviews and enhances with examples/rationale
- Speeds up initial draft, maintains quality

---

## Troubleshooting

### CI Fails: "Version [X.X.X] not found in CHANGELOG.md"

**Cause:** You forgot to add a section for the release version

**Fix:**
```bash
# 1. Delete the tag
git tag -d vX.X.X
git push origin :refs/tags/vX.X.X

# 2. Update CHANGELOG.md
vim CHANGELOG.md  # Add ## [X.X.X] section

# 3. Commit and re-tag
git add CHANGELOG.md
git commit -m "Add CHANGELOG entry for vX.X.X"
git tag -a vX.X.X -m "Release vX.X.X"
git push origin main vX.X.X
```

### CI Fails: "Version [X.X.X] in CHANGELOG.md has no content"

**Cause:** Version header exists but section is empty

**Fix:**
```bash
# Add at least one bullet point to the version section
vim CHANGELOG.md

# Example minimum:
## [0.5.0] - 2025-10-15
### Added
- Initial release of feature X
```

### GitHub Release Shows Wrong Content

**Cause:** Extraction script pulled wrong section

**Debug:**
```bash
# Test extraction locally
.github/scripts/extract_changelog.sh 0.5.0

# Check for formatting issues in CHANGELOG.md
# Ensure version header exactly matches: ## [0.5.0]
```

---

## Summary

**What's Manual:**
- Writing changelog entries (the important part!)
- Adding code examples and design rationale
- Explaining breaking changes and migrations
- Committing CHANGELOG.md

**What's Automated:**
- Validating changelog exists and has content
- Extracting release notes for GitHub
- Publishing releases
- Ensuring consistency

**Best Practice:**
Update CHANGELOG.md as part of your release preparation checklist, just like updating version numbers. The automation ensures you don't forget and handles the mechanical distribution.

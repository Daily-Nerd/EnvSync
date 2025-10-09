# Release Checklist

Use this checklist when preparing a new TripWire release.

## Pre-Release (1-2 days before)

- [ ] **Review git log** since last release
  ```bash
  git log v0.4.0..HEAD --oneline --no-merges
  ```

- [ ] **Review closed PRs** and merged features
  ```bash
  gh pr list --state merged --base main --limit 20
  ```

- [ ] **List breaking changes** and migration steps needed

- [ ] **Gather user feedback** from issues and discussions

## Update CHANGELOG.md

- [ ] **Add new version section** with today's date
  ```markdown
  ## [0.5.0] - YYYY-MM-DD
  ```

- [ ] **Categorize changes:**
  - [ ] Added (new features)
  - [ ] Changed (modifications to existing features)
  - [ ] Fixed (bug fixes)
  - [ ] Deprecated (features being removed)
  - [ ] Removed (deleted features)
  - [ ] Security (security fixes)

- [ ] **Write user-focused descriptions** (not just commit messages)

- [ ] **Add code examples** for new features and breaking changes

- [ ] **Document migration steps** for breaking changes

- [ ] **Add Technical Details section:**
  - [ ] Test coverage statistics
  - [ ] Architecture changes
  - [ ] Performance improvements

- [ ] **Add Design Decisions section** for major features

- [ ] **Update version comparison links** at bottom
  ```markdown
  [Unreleased]: https://github.com/Daily-Nerd/TripWire/compare/v0.5.0...HEAD
  [0.5.0]: https://github.com/Daily-Nerd/TripWire/compare/v0.4.0...v0.5.0
  ```

## Update Version Numbers

- [ ] **Update pyproject.toml**
  ```toml
  version = "0.5.0"
  ```

- [ ] **Update src/tripwire/__init__.py**
  ```python
  __version__ = "0.5.0"
  ```

- [ ] **Update src/tripwire/cli.py**
  ```python
  @click.version_option(version="0.5.0")
  ```

- [ ] **Run version consistency check locally:**
  ```bash
  grep -r "0.5.0" pyproject.toml src/tripwire/__init__.py src/tripwire/cli.py
  ```

## Pre-Release Testing

- [ ] **Run full test suite:**
  ```bash
  pytest --cov=tripwire --cov-report=term
  ```

- [ ] **Run type checking:**
  ```bash
  mypy src/tripwire
  ```

- [ ] **Run linting:**
  ```bash
  ruff check .
  black . --check
  ```

- [ ] **Run security scans:**
  ```bash
  bandit -r src/tripwire -ll
  pip-audit
  ```

- [ ] **Test CLI commands manually:**
  ```bash
  tripwire --version
  tripwire --help
  tripwire init --project-type=web
  tripwire check
  tripwire generate
  ```

- [ ] **Validate CHANGELOG.md:**
  ```bash
  .github/scripts/validate_changelog.sh 0.5.0
  ```

- [ ] **Test changelog extraction:**
  ```bash
  .github/scripts/extract_changelog.sh 0.5.0
  ```

## Commit and Tag

- [ ] **Commit all changes:**
  ```bash
  git add CHANGELOG.md pyproject.toml src/tripwire/__init__.py src/tripwire/cli.py
  git commit -m "Bump version to 0.5.0"
  ```

- [ ] **Push to main:**
  ```bash
  git push origin main
  ```

- [ ] **Wait for CI to pass** on main branch
  ```bash
  gh run watch
  ```

- [ ] **Create and push tag:**
  ```bash
  git tag -a v0.5.0 -m "Release v0.5.0"
  git push origin v0.5.0
  ```

## Monitor Release Process

- [ ] **Watch release workflow:**
  ```bash
  gh run watch
  ```

- [ ] **Verify stages complete:**
  - [ ] validate-release
  - [ ] tests (all platforms: Ubuntu, Windows, macOS)
  - [ ] build-package
  - [ ] test-pypi (for pre-releases)
  - [ ] pypi (for stable releases)
  - [ ] create-release

## Post-Release Verification

- [ ] **Check GitHub Release page:**
  ```bash
  gh release view v0.5.0
  ```

- [ ] **Verify PyPI package:**
  - [ ] Visit https://pypi.org/project/tripwire-py/0.5.0/
  - [ ] Check description renders correctly
  - [ ] Verify file sizes are reasonable

- [ ] **Test installation from PyPI:**
  ```bash
  python -m venv /tmp/test_tripwire
  source /tmp/test_tripwire/bin/activate
  pip install tripwire-py==0.5.0
  tripwire --version
  python -c "from tripwire import env; print('OK')"
  deactivate
  rm -rf /tmp/test_tripwire
  ```

- [ ] **Verify release notes** in GitHub release match CHANGELOG.md

## Communication

- [ ] **Announce release** (if applicable):
  - [ ] Twitter/social media
  - [ ] Discord/community channels
  - [ ] Mailing list
  - [ ] Project discussions

- [ ] **Update documentation** (if new features require it)

- [ ] **Close milestone** (if using GitHub milestones)
  ```bash
  gh milestone list
  gh milestone close "v0.5.0"
  ```

## Rollback (if needed)

If something goes wrong:

- [ ] **Delete GitHub release:**
  ```bash
  gh release delete v0.5.0
  ```

- [ ] **Delete git tag:**
  ```bash
  git tag -d v0.5.0
  git push origin :refs/tags/v0.5.0
  ```

- [ ] **Yank PyPI release** (last resort):
  ```bash
  # Log into PyPI web interface
  # Navigate to release → Manage → Yank release
  # Note: This doesn't delete, just marks as yanked
  ```

---

## Quick Command Reference

```bash
# View commits since last release
git log v0.4.0..HEAD --oneline --no-merges

# View all tags
git tag -l

# Test changelog scripts
.github/scripts/validate_changelog.sh 0.5.0
.github/scripts/extract_changelog.sh 0.5.0

# Check if version exists on PyPI
pip index versions tripwire-py

# Watch CI workflow
gh run watch

# View release on GitHub
gh release view v0.5.0
```

---

## For Pre-Releases (RC/Beta)

Additional steps for pre-release versions:

- [ ] **Use pre-release version format:**
  - Release candidates: `0.5.0-rc1`, `0.5.0-rc2`
  - Beta releases: `0.5.0-beta1`

- [ ] **Add CHANGELOG section for pre-release:**
  ```markdown
  ## [0.5.0-rc1] - 2025-10-09
  ```

- [ ] **Tag with pre-release suffix:**
  ```bash
  git tag -a v0.5.0-rc1 -m "Release v0.5.0-rc1 (pre-release)"
  git push origin v0.5.0-rc1
  ```

- [ ] **Verify release is marked as pre-release** on GitHub

- [ ] **Verify package goes to Test PyPI** (not production PyPI)

- [ ] **Test upgrade path** from RC to final release:
  ```bash
  pip install tripwire-py==0.5.0-rc1
  # Later:
  pip install --upgrade tripwire-py==0.5.0
  ```

---

## Emergency Hotfix Process

For critical bugs requiring immediate release:

1. **Create hotfix branch from latest tag:**
   ```bash
   git checkout -b hotfix/0.4.1 v0.4.0
   ```

2. **Fix bug and add minimal test**

3. **Update CHANGELOG.md** (minimal entry is OK)

4. **Bump version to patch release** (0.4.0 → 0.4.1)

5. **Merge to main and tag:**
   ```bash
   git checkout main
   git merge hotfix/0.4.1
   git tag -a v0.4.1 -m "Hotfix: v0.4.1"
   git push origin main v0.4.1
   ```

6. **Fast-track release** (CI handles it)

---

## Notes

- **Timing:** Schedule releases during business hours for faster issue response
- **Frequency:** Aim for quarterly major releases (0.X.0) and ad-hoc patch releases (0.X.Y)
- **Communication:** Announce breaking changes well in advance (via discussions/issues)
- **Testing:** Pre-releases (RC) are recommended for major versions with breaking changes

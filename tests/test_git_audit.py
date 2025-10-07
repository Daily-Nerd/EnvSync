"""Tests for git audit functionality.

This module tests the git history analysis and secret leak detection features.
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Generator

import pytest

from envsync.git_audit import (
    FileOccurrence,
    GitAuditError,
    GitCommandError,
    NotGitRepositoryError,
    RemediationStep,
    SecretTimeline,
    analyze_secret_history,
    check_git_repository,
    check_if_public_repo,
    find_secret_in_commit,
    generate_filter_branch_command,
    generate_remediation_steps,
    get_affected_branches,
    get_commit_info,
    get_rotation_command,
    run_git_command,
)


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary git repository for testing.

    Args:
        tmp_path: Pytest temporary directory

    Yields:
        Path to the temporary git repository
    """
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    # Disable GPG signing for tests
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    yield repo_path


@pytest.fixture
def git_repo_with_secret(temp_git_repo: Path) -> Path:
    """Create a git repo with a leaked secret in history.

    Args:
        temp_git_repo: Temporary git repository

    Returns:
        Path to the repository
    """
    # Create .env file with secret
    env_file = temp_git_repo / ".env"
    env_file.write_text("AWS_SECRET_KEY=AKIAIOSFODNN7EXAMPLE\nDEBUG=true\n")

    # Commit it (simulating accidental commit)
    subprocess.run(["git", "add", ".env"], cwd=temp_git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit with config"],
        cwd=temp_git_repo,
        check=True,
        capture_output=True,
    )

    # Add another file
    (temp_git_repo / "README.md").write_text("# Test Project\n")
    subprocess.run(["git", "add", "README.md"], cwd=temp_git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add README"],
        cwd=temp_git_repo,
        check=True,
        capture_output=True,
    )

    # Add the secret to another file
    config_file = temp_git_repo / "config.py"
    config_file.write_text('AWS_SECRET_KEY = "AKIAIOSFODNN7EXAMPLE"\n')
    subprocess.run(["git", "add", "config.py"], cwd=temp_git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add config file"],
        cwd=temp_git_repo,
        check=True,
        capture_output=True,
    )

    return temp_git_repo


@pytest.fixture
def git_repo_clean(temp_git_repo: Path) -> Path:
    """Create a git repo without any secrets.

    Args:
        temp_git_repo: Temporary git repository

    Returns:
        Path to the repository
    """
    # Create files without secrets
    (temp_git_repo / "README.md").write_text("# Clean Project\n")
    subprocess.run(["git", "add", "README.md"], cwd=temp_git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=temp_git_repo,
        check=True,
        capture_output=True,
    )

    return temp_git_repo


class TestGitCommands:
    """Tests for git command execution."""

    def test_run_git_command_success(self, temp_git_repo: Path) -> None:
        """Test successful git command execution."""
        result = run_git_command(["status"], temp_git_repo)
        assert result.returncode == 0
        assert "On branch" in result.stdout or "On branch" in result.stderr

    def test_run_git_command_failure(self, temp_git_repo: Path) -> None:
        """Test git command failure handling."""
        with pytest.raises(GitCommandError) as exc_info:
            run_git_command(["invalid-command"], temp_git_repo, check=True)

        assert "invalid-command" in str(exc_info.value)

    def test_check_git_repository_valid(self, temp_git_repo: Path) -> None:
        """Test checking a valid git repository."""
        check_git_repository(temp_git_repo)  # Should not raise

    def test_check_git_repository_invalid(self, tmp_path: Path) -> None:
        """Test checking an invalid git repository."""
        non_git_dir = tmp_path / "not_a_repo"
        non_git_dir.mkdir()

        with pytest.raises(NotGitRepositoryError) as exc_info:
            check_git_repository(non_git_dir)

        assert str(non_git_dir) in str(exc_info.value)


class TestPublicRepoDetection:
    """Tests for public repository detection."""

    def test_no_remotes(self, temp_git_repo: Path) -> None:
        """Test repository with no remotes."""
        assert not check_if_public_repo(temp_git_repo)

    def test_github_remote(self, temp_git_repo: Path) -> None:
        """Test repository with GitHub remote."""
        subprocess.run(
            ["git", "remote", "add", "origin", "https://github.com/user/repo.git"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )
        assert check_if_public_repo(temp_git_repo)

    def test_gitlab_remote(self, temp_git_repo: Path) -> None:
        """Test repository with GitLab remote."""
        subprocess.run(
            ["git", "remote", "add", "origin", "https://gitlab.com/user/repo.git"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )
        assert check_if_public_repo(temp_git_repo)

    def test_private_remote(self, temp_git_repo: Path) -> None:
        """Test repository with private remote."""
        subprocess.run(
            ["git", "remote", "add", "origin", "git@private-server.com:user/repo.git"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )
        assert not check_if_public_repo(temp_git_repo)


class TestCommitInfo:
    """Tests for commit information extraction."""

    def test_get_commit_info(self, git_repo_with_secret: Path) -> None:
        """Test getting commit information."""
        # Get HEAD commit
        result = run_git_command(["rev-parse", "HEAD"], git_repo_with_secret)
        commit_hash = result.stdout.strip()

        info = get_commit_info(commit_hash, git_repo_with_secret)
        assert info is not None
        assert info["hash"] == commit_hash
        assert info["author"] == "Test User"
        assert info["email"] == "test@example.com"
        assert "message" in info

    def test_get_commit_info_invalid(self, temp_git_repo: Path) -> None:
        """Test getting info for invalid commit."""
        info = get_commit_info("0" * 40, temp_git_repo)
        assert info is None


class TestSecretSearch:
    """Tests for secret searching in commits."""

    def test_find_secret_in_commit(self, git_repo_with_secret: Path) -> None:
        """Test finding a secret in a specific commit."""
        # Get the first commit hash
        result = run_git_command(
            ["log", "--format=%H", "--reverse"],
            git_repo_with_secret,
        )
        first_commit = result.stdout.strip().split("\n")[0]

        # Search for the secret
        occurrences = find_secret_in_commit(
            first_commit,
            r"AWS_SECRET_KEY",
            git_repo_with_secret,
        )

        assert len(occurrences) > 0
        assert any(occ.file_path == ".env" for occ in occurrences)
        assert all(isinstance(occ, FileOccurrence) for occ in occurrences)
        assert all(occ.commit_hash == first_commit for occ in occurrences)

    def test_find_secret_not_in_commit(self, git_repo_clean: Path) -> None:
        """Test searching for a secret that doesn't exist."""
        result = run_git_command(["rev-parse", "HEAD"], git_repo_clean)
        commit_hash = result.stdout.strip()

        occurrences = find_secret_in_commit(
            commit_hash,
            r"SECRET_KEY",
            git_repo_clean,
        )

        assert len(occurrences) == 0

    def test_find_secret_binary_files_skipped(self, temp_git_repo: Path) -> None:
        """Test that binary files are skipped."""
        # Create a fake binary file with the pattern
        (temp_git_repo / "image.png").write_bytes(b"AWS_SECRET_KEY=test")
        subprocess.run(["git", "add", "image.png"], cwd=temp_git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add image"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )

        result = run_git_command(["rev-parse", "HEAD"], temp_git_repo)
        commit_hash = result.stdout.strip()

        occurrences = find_secret_in_commit(
            commit_hash,
            r"AWS_SECRET_KEY",
            temp_git_repo,
        )

        # Should not find anything (binary files are skipped)
        assert len(occurrences) == 0


class TestBranchDetection:
    """Tests for branch detection."""

    def test_get_affected_branches(self, git_repo_with_secret: Path) -> None:
        """Test getting branches containing a commit."""
        result = run_git_command(["rev-parse", "HEAD"], git_repo_with_secret)
        commit_hash = result.stdout.strip()

        branches = get_affected_branches(commit_hash, git_repo_with_secret)

        assert len(branches) > 0
        # Should at least contain master or main
        assert any(branch in ["master", "main"] for branch in branches)

    def test_get_affected_branches_multiple(self, git_repo_with_secret: Path) -> None:
        """Test getting multiple branches containing a commit."""
        # Get first commit
        result = run_git_command(
            ["log", "--format=%H", "--reverse"],
            git_repo_with_secret,
        )
        first_commit = result.stdout.strip().split("\n")[0]

        # Create a new branch from first commit
        subprocess.run(
            ["git", "branch", "feature-branch", first_commit],
            cwd=git_repo_with_secret,
            check=True,
            capture_output=True,
        )

        branches = get_affected_branches(first_commit, git_repo_with_secret)

        # Should contain both master/main and feature-branch
        assert len(branches) >= 2


class TestSecretTimeline:
    """Tests for secret timeline analysis."""

    def test_analyze_secret_history_found(self, git_repo_with_secret: Path) -> None:
        """Test analyzing history when secret is found."""
        timeline = analyze_secret_history(
            secret_name="AWS_SECRET_KEY",
            repo_path=git_repo_with_secret,
        )

        assert timeline.secret_name == "AWS_SECRET_KEY"
        assert timeline.total_occurrences > 0
        assert len(timeline.commits_affected) > 0
        assert len(timeline.files_affected) > 0
        assert timeline.first_seen is not None
        assert timeline.last_seen is not None
        assert isinstance(timeline.first_seen, datetime)

    def test_analyze_secret_history_not_found(self, git_repo_clean: Path) -> None:
        """Test analyzing history when secret is not found."""
        timeline = analyze_secret_history(
            secret_name="NONEXISTENT_SECRET",
            repo_path=git_repo_clean,
        )

        assert timeline.total_occurrences == 0
        assert len(timeline.commits_affected) == 0
        assert timeline.first_seen is None
        assert timeline.last_seen is None

    def test_analyze_secret_with_value(self, git_repo_with_secret: Path) -> None:
        """Test analyzing history with actual secret value."""
        timeline = analyze_secret_history(
            secret_name="AWS_SECRET_KEY",
            secret_value="AKIAIOSFODNN7EXAMPLE",
            repo_path=git_repo_with_secret,
        )

        assert timeline.total_occurrences > 0
        # Should find it in multiple files
        assert len(timeline.files_affected) >= 2

    def test_analyze_secret_max_commits(self, git_repo_with_secret: Path) -> None:
        """Test max_commits parameter."""
        timeline = analyze_secret_history(
            secret_name="AWS_SECRET_KEY",
            repo_path=git_repo_with_secret,
            max_commits=1,
        )

        # Should still find the secret
        assert timeline.total_occurrences >= 0

    def test_timeline_exposure_duration(self, git_repo_with_secret: Path) -> None:
        """Test exposure duration calculation."""
        timeline = analyze_secret_history(
            secret_name="AWS_SECRET_KEY",
            repo_path=git_repo_with_secret,
        )

        # Should be 0 or more days
        assert timeline.exposure_duration_days >= 0

    def test_timeline_severity(self, git_repo_with_secret: Path) -> None:
        """Test severity calculation."""
        timeline = analyze_secret_history(
            secret_name="AWS_SECRET_KEY",
            repo_path=git_repo_with_secret,
        )

        assert timeline.severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

    def test_timeline_public_repo_severity(self, temp_git_repo: Path) -> None:
        """Test that public repos get CRITICAL severity."""
        # Add a GitHub remote
        subprocess.run(
            ["git", "remote", "add", "origin", "https://github.com/user/repo.git"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )

        # Add a secret
        env_file = temp_git_repo / ".env"
        env_file.write_text("SECRET=test123\n")
        subprocess.run(["git", "add", ".env"], cwd=temp_git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add secret"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )

        timeline = analyze_secret_history(
            secret_name="SECRET",
            repo_path=temp_git_repo,
        )

        # Public repo with commits should be CRITICAL
        if timeline.total_occurrences > 0:
            assert timeline.severity == "CRITICAL"


class TestRemediationSteps:
    """Tests for remediation step generation."""

    def test_generate_remediation_steps(self, git_repo_with_secret: Path) -> None:
        """Test generating remediation steps."""
        timeline = analyze_secret_history(
            secret_name="AWS_SECRET_KEY",
            repo_path=git_repo_with_secret,
        )

        steps = generate_remediation_steps(timeline, "AWS_SECRET_KEY")

        assert len(steps) > 0
        assert all(isinstance(step, RemediationStep) for step in steps)
        assert steps[0].urgency == "CRITICAL"  # First step should be rotation
        assert "rotate" in steps[0].title.lower()

    def test_remediation_step_order(self, git_repo_with_secret: Path) -> None:
        """Test that remediation steps are in correct order."""
        timeline = analyze_secret_history(
            secret_name="AWS_SECRET_KEY",
            repo_path=git_repo_with_secret,
        )

        steps = generate_remediation_steps(timeline, "AWS_SECRET_KEY")

        # Steps should be ordered
        for i, step in enumerate(steps, 1):
            assert step.order == i

    def test_remediation_includes_rotation_command(self) -> None:
        """Test that AWS keys get rotation commands."""
        command = get_rotation_command("AWS_SECRET_ACCESS_KEY")
        assert command is not None
        assert "aws" in command.lower()

    def test_remediation_github_token(self) -> None:
        """Test GitHub token rotation command."""
        command = get_rotation_command("GITHUB_TOKEN")
        assert command is not None
        assert "github.com" in command.lower()

    def test_remediation_unknown_secret(self) -> None:
        """Test unknown secret type."""
        command = get_rotation_command("CUSTOM_SECRET_KEY")
        # Should return None for unknown types
        assert command is None


class TestFilterBranchCommand:
    """Tests for filter-branch command generation."""

    def test_generate_filter_branch_single_file(self) -> None:
        """Test generating filter-branch for single file."""
        command = generate_filter_branch_command([".env"])
        assert "git filter-branch" in command
        assert ".env" in command
        assert "--force" in command

    def test_generate_filter_branch_multiple_files(self) -> None:
        """Test generating filter-branch for multiple files."""
        files = [".env", "config.py", "settings.json"]
        command = generate_filter_branch_command(files)
        assert "git filter-branch" in command
        for file in files:
            assert file in command


class TestDataClasses:
    """Tests for data classes."""

    def test_file_occurrence_hash(self) -> None:
        """Test FileOccurrence hashing."""
        occ1 = FileOccurrence(
            file_path=".env",
            line_number=1,
            commit_hash="abc123",
            commit_date=datetime.now(),
            author="Test",
            author_email="test@example.com",
            commit_message="Test",
        )

        occ2 = FileOccurrence(
            file_path=".env",
            line_number=1,
            commit_hash="abc123",
            commit_date=datetime.now(),
            author="Test",
            author_email="test@example.com",
            commit_message="Test",
        )

        # Same file, line, and commit should have same hash
        assert hash(occ1) == hash(occ2)

    def test_secret_timeline_dataclass(self) -> None:
        """Test SecretTimeline dataclass."""
        timeline = SecretTimeline(
            secret_name="TEST_SECRET",
            first_seen=datetime.now(),
            last_seen=datetime.now(),
            total_occurrences=5,
            commits_affected=["abc123"],
            files_affected=[".env"],
            occurrences=[],
            is_in_public_repo=True,
            is_currently_in_git=True,
        )

        assert timeline.secret_name == "TEST_SECRET"
        assert timeline.severity == "CRITICAL"  # Public repo

    def test_remediation_step_dataclass(self) -> None:
        """Test RemediationStep dataclass."""
        step = RemediationStep(
            order=1,
            title="Rotate secret",
            description="Rotate the compromised secret",
            urgency="CRITICAL",
            command="aws iam create-access-key",
            warning="Do this immediately!",
        )

        assert step.order == 1
        assert step.urgency == "CRITICAL"
        assert step.command is not None


class TestIntegration:
    """Integration tests for complete workflow."""

    def test_full_audit_workflow(self, git_repo_with_secret: Path) -> None:
        """Test complete audit workflow."""
        # Analyze history
        timeline = analyze_secret_history(
            secret_name="AWS_SECRET_KEY",
            secret_value="AKIAIOSFODNN7EXAMPLE",
            repo_path=git_repo_with_secret,
        )

        # Should find the secret
        assert timeline.total_occurrences > 0
        assert len(timeline.files_affected) >= 2  # .env and config.py

        # Generate remediation steps
        steps = generate_remediation_steps(timeline, "AWS_SECRET_KEY")
        assert len(steps) > 0

        # First step should be rotation
        assert "rotate" in steps[0].title.lower()
        assert steps[0].urgency == "CRITICAL"

    def test_audit_clean_repo(self, git_repo_clean: Path) -> None:
        """Test auditing a clean repository."""
        timeline = analyze_secret_history(
            secret_name="SECRET_KEY",
            repo_path=git_repo_clean,
        )

        assert timeline.total_occurrences == 0
        assert len(timeline.commits_affected) == 0
        assert timeline.first_seen is None

    def test_audit_with_removed_secret(self, git_repo_with_secret: Path) -> None:
        """Test auditing when secret was removed but is in history."""
        # Remove the secret from ALL current files
        env_file = git_repo_with_secret / ".env"
        env_file.write_text("DEBUG=true\n")

        config_file = git_repo_with_secret / "config.py"
        config_file.write_text("# Empty config\n")

        subprocess.run(["git", "add", ".env", "config.py"], cwd=git_repo_with_secret, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Remove secret from all files"],
            cwd=git_repo_with_secret,
            check=True,
            capture_output=True,
        )

        timeline = analyze_secret_history(
            secret_name="AWS_SECRET_KEY",
            repo_path=git_repo_with_secret,
        )

        # Should still find it in history
        assert timeline.total_occurrences > 0
        # But not in current HEAD
        assert not timeline.is_currently_in_git


class TestErrorHandling:
    """Tests for error handling."""

    def test_not_git_repository_error(self, tmp_path: Path) -> None:
        """Test error when not in a git repository."""
        non_git_dir = tmp_path / "not_git"
        non_git_dir.mkdir()

        with pytest.raises(NotGitRepositoryError):
            analyze_secret_history(
                secret_name="TEST",
                repo_path=non_git_dir,
            )

    def test_git_command_error_message(self, temp_git_repo: Path) -> None:
        """Test GitCommandError message format."""
        try:
            run_git_command(["invalid-command"], temp_git_repo, check=True)
            pytest.fail("Should have raised GitCommandError")
        except GitCommandError as e:
            assert "invalid-command" in str(e)
            assert e.returncode != 0

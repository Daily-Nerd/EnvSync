"""Git history audit for secret leak detection.

This module provides functionality to analyze git history and detect when secrets
were leaked, providing detailed timeline information and remediation steps.
"""

import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from envsync.exceptions import EnvSyncError


class GitAuditError(EnvSyncError):
    """Base error for git audit operations."""

    pass


class NotGitRepositoryError(GitAuditError):
    """Raised when current directory is not a git repository."""

    def __init__(self, path: Path) -> None:
        """Initialize NotGitRepositoryError.

        Args:
            path: Path that is not a git repository
        """
        self.path = path
        super().__init__(f"Not a git repository: {path}")


class GitCommandError(GitAuditError):
    """Raised when git command fails."""

    def __init__(self, command: str, stderr: str, returncode: int) -> None:
        """Initialize GitCommandError.

        Args:
            command: Git command that failed
            stderr: Standard error output
            returncode: Git command return code
        """
        self.command = command
        self.stderr = stderr
        self.returncode = returncode
        super().__init__(f"Git command failed (exit {returncode}): {command}\n{stderr}")


@dataclass
class FileOccurrence:
    """A single occurrence of a secret in a file at a specific commit."""

    file_path: str
    line_number: int
    commit_hash: str
    commit_date: datetime
    author: str
    author_email: str
    commit_message: str
    context: str = ""  # Line content with secret (redacted)

    def __hash__(self) -> int:
        """Hash based on unique commit + file + line."""
        return hash((self.commit_hash, self.file_path, self.line_number))


@dataclass
class SecretTimeline:
    """Complete timeline of a secret's history in git."""

    secret_name: str
    first_seen: Optional[datetime]
    last_seen: Optional[datetime]
    total_occurrences: int
    commits_affected: List[str]
    files_affected: List[str]
    occurrences: List[FileOccurrence]
    is_in_public_repo: bool
    is_currently_in_git: bool
    branches_affected: List[str] = field(default_factory=list)

    @property
    def exposure_duration_days(self) -> int:
        """Calculate exposure duration in days."""
        if not self.first_seen or not self.last_seen:
            return 0
        return (self.last_seen - self.first_seen).days

    @property
    def severity(self) -> str:
        """Calculate severity based on exposure context."""
        if self.is_in_public_repo and len(self.commits_affected) > 0:
            return "CRITICAL"
        elif self.is_currently_in_git:
            return "HIGH"
        elif len(self.commits_affected) > 10:
            return "MEDIUM"
        else:
            return "LOW"


@dataclass
class RemediationStep:
    """A remediation action with priority and details."""

    order: int
    title: str
    description: str
    urgency: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW"
    command: Optional[str] = None
    warning: Optional[str] = None


def run_git_command(
    args: List[str],
    repo_path: Path,
    check: bool = True,
    capture_output: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a git command and return the result.

    Args:
        args: Git command arguments (without 'git' prefix)
        repo_path: Path to git repository
        check: Whether to raise exception on non-zero exit
        capture_output: Whether to capture stdout/stderr

    Returns:
        Completed process result

    Raises:
        GitCommandError: If command fails and check=True
    """
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=repo_path,
            capture_output=capture_output,
            text=True,
            check=False,
        )

        if check and result.returncode != 0:
            raise GitCommandError(
                command=" ".join(["git"] + args),
                stderr=result.stderr,
                returncode=result.returncode,
            )

        return result
    except FileNotFoundError as e:
        raise GitCommandError(command="git", stderr=str(e), returncode=127) from e


def check_git_repository(repo_path: Path) -> None:
    """Check if directory is a git repository.

    Args:
        repo_path: Path to check

    Raises:
        NotGitRepositoryError: If not a git repository
    """
    git_dir = repo_path / ".git"
    if not git_dir.exists():
        raise NotGitRepositoryError(repo_path)

    # Verify with git command
    result = run_git_command(
        ["rev-parse", "--git-dir"],
        repo_path,
        check=False,
    )

    if result.returncode != 0:
        raise NotGitRepositoryError(repo_path)


def check_if_public_repo(repo_path: Path) -> bool:
    """Check if repository has a public remote.

    Args:
        repo_path: Path to git repository

    Returns:
        True if repository appears to have public remote
    """
    result = run_git_command(["remote", "-v"], repo_path, check=False)

    if result.returncode != 0:
        return False

    remotes = result.stdout.lower()

    # Check for common public hosting platforms
    public_indicators = [
        "github.com",
        "gitlab.com",
        "bitbucket.org",
        "codeberg.org",
        "git.sr.ht",
    ]

    return any(indicator in remotes for indicator in public_indicators)


def get_commit_info(commit_hash: str, repo_path: Path) -> Optional[Dict[str, str]]:
    """Get detailed information about a commit.

    Args:
        commit_hash: Git commit hash
        repo_path: Path to git repository

    Returns:
        Dictionary with commit information, or None if commit not found
    """
    result = run_git_command(
        ["show", "--no-patch", "--format=%H|%an|%ae|%aI|%s", commit_hash],
        repo_path,
        check=False,
    )

    if result.returncode != 0:
        return None

    parts = result.stdout.strip().split("|", 4)
    if len(parts) != 5:
        return None

    return {
        "hash": parts[0],
        "author": parts[1],
        "email": parts[2],
        "date": parts[3],
        "message": parts[4],
    }


def find_secret_in_commit(
    commit_hash: str,
    secret_pattern: str,
    repo_path: Path,
) -> List[FileOccurrence]:
    """Find all occurrences of a secret pattern in a specific commit.

    Args:
        commit_hash: Git commit hash to search
        secret_pattern: Regex pattern to search for
        repo_path: Path to git repository

    Returns:
        List of file occurrences found in the commit
    """
    occurrences: List[FileOccurrence] = []

    # Get commit info
    commit_info = get_commit_info(commit_hash, repo_path)
    if not commit_info:
        return occurrences

    # Get list of files in commit
    result = run_git_command(
        ["ls-tree", "-r", "--name-only", commit_hash],
        repo_path,
        check=False,
    )

    if result.returncode != 0:
        return occurrences

    files = result.stdout.strip().split("\n")

    # Search each file for the pattern
    pattern = re.compile(secret_pattern, re.IGNORECASE)

    for file_path in files:
        if not file_path:
            continue

        # Skip binary files
        if any(
            file_path.endswith(ext)
            for ext in [
                ".pyc",
                ".so",
                ".dylib",
                ".dll",
                ".exe",
                ".png",
                ".jpg",
                ".gif",
                ".pdf",
            ]
        ):
            continue

        # Get file content from commit
        file_result = run_git_command(
            ["show", f"{commit_hash}:{file_path}"],
            repo_path,
            check=False,
        )

        if file_result.returncode != 0:
            continue

        # Search for pattern in file content
        lines = file_result.stdout.split("\n")
        for line_num, line in enumerate(lines, 1):
            if pattern.search(line):
                # Redact the actual secret value for context
                redacted_line = pattern.sub("***REDACTED***", line)

                occurrences.append(
                    FileOccurrence(
                        file_path=file_path,
                        line_number=line_num,
                        commit_hash=commit_hash,
                        commit_date=datetime.fromisoformat(commit_info["date"]),
                        author=commit_info["author"],
                        author_email=commit_info["email"],
                        commit_message=commit_info["message"],
                        context=redacted_line.strip()[:100],
                    )
                )

    return occurrences


def get_affected_branches(commit_hash: str, repo_path: Path) -> List[str]:
    """Get list of branches that contain a specific commit.

    Args:
        commit_hash: Git commit hash
        repo_path: Path to git repository

    Returns:
        List of branch names containing the commit
    """
    result = run_git_command(
        ["branch", "--contains", commit_hash, "--all"],
        repo_path,
        check=False,
    )

    if result.returncode != 0:
        return []

    branches = []
    for line in result.stdout.strip().split("\n"):
        line = line.strip()
        if line:
            # Remove leading asterisk and clean up remote refs
            branch = line.lstrip("* ").strip()
            if branch.startswith("remotes/"):
                branch = branch.replace("remotes/", "", 1)
            branches.append(branch)

    return branches


def analyze_secret_history(
    secret_name: str,
    secret_value: Optional[str] = None,
    repo_path: Path = Path.cwd(),
    max_commits: int = 1000,
) -> SecretTimeline:
    """Analyze git history to find when and where a secret was leaked.

    Args:
        secret_name: Name of the environment variable (e.g., "AWS_SECRET_KEY")
        secret_value: Optional actual secret value to search for (more accurate)
        repo_path: Path to git repository
        max_commits: Maximum number of commits to analyze

    Returns:
        SecretTimeline with all occurrences and metadata

    Raises:
        NotGitRepositoryError: If path is not a git repository
        GitCommandError: If git commands fail
    """
    check_git_repository(repo_path)

    # Build search pattern
    if secret_value:
        # Search for the actual secret value (most accurate)
        # Escape special regex characters
        escaped_value = re.escape(secret_value)
        secret_pattern = escaped_value
    else:
        # Search for variable name patterns (less accurate but safer)
        # Look for: SECRET_NAME=value or SECRET_NAME: value or "SECRET_NAME": "value"
        secret_pattern = rf"{re.escape(secret_name)}\s*[:=]\s*['\"]?[^\s'\";]+['\"]?"

    # Find all commits that potentially contain the secret
    result = run_git_command(
        [
            "log",
            "-G",
            secret_pattern,
            "--all",
            "--format=%H",
            f"--max-count={max_commits}",
        ],
        repo_path,
        check=False,
    )

    commit_hashes: List[str] = []
    if result.returncode == 0 and result.stdout.strip():
        commit_hashes = result.stdout.strip().split("\n")

    # Collect all occurrences
    all_occurrences: List[FileOccurrence] = []
    seen_occurrences: Set[Tuple[str, str, int]] = set()

    for commit_hash in commit_hashes:
        occurrences = find_secret_in_commit(commit_hash, secret_pattern, repo_path)

        for occ in occurrences:
            key = (occ.commit_hash, occ.file_path, occ.line_number)
            if key not in seen_occurrences:
                seen_occurrences.add(key)
                all_occurrences.append(occ)

    # Sort occurrences by date
    all_occurrences.sort(key=lambda x: x.commit_date)

    # Check if secret is currently in git (HEAD)
    is_currently_in_git = False
    if commit_hashes:
        head_occurrences = find_secret_in_commit("HEAD", secret_pattern, repo_path)
        is_currently_in_git = len(head_occurrences) > 0

    # Collect metadata
    first_seen = all_occurrences[0].commit_date if all_occurrences else None
    last_seen = all_occurrences[-1].commit_date if all_occurrences else None

    unique_commits = list(dict.fromkeys([occ.commit_hash for occ in all_occurrences]))
    unique_files = list(set([occ.file_path for occ in all_occurrences]))

    # Get branches affected
    branches_affected: List[str] = []
    if unique_commits:
        branches_affected = get_affected_branches(unique_commits[0], repo_path)

    return SecretTimeline(
        secret_name=secret_name,
        first_seen=first_seen,
        last_seen=last_seen,
        total_occurrences=len(all_occurrences),
        commits_affected=unique_commits,
        files_affected=unique_files,
        occurrences=all_occurrences,
        is_in_public_repo=check_if_public_repo(repo_path),
        is_currently_in_git=is_currently_in_git,
        branches_affected=branches_affected,
    )


def generate_filter_branch_command(files: List[str]) -> str:
    """Generate git filter-branch command to remove files from history.

    Args:
        files: List of file paths to remove

    Returns:
        Complete git filter-branch command
    """
    files_str = " ".join(files)
    return f"git filter-branch --force --index-filter " f"'git rm --cached --ignore-unmatch {files_str}' HEAD"


def get_rotation_command(secret_name: str) -> Optional[str]:
    """Get secret rotation command based on secret type.

    Args:
        secret_name: Name of the secret variable

    Returns:
        Command to rotate the secret, or None if unknown
    """
    rotation_commands: Dict[str, str] = {
        "AWS_SECRET_ACCESS_KEY": "aws iam create-access-key --user-name <username>",
        "AWS_ACCESS_KEY_ID": "aws iam create-access-key --user-name <username>",
        "GITHUB_TOKEN": "Visit https://github.com/settings/tokens to generate new token",
        "OPENAI_API_KEY": "Visit https://platform.openai.com/api-keys to rotate key",
        "STRIPE_SECRET_KEY": "Visit https://dashboard.stripe.com/apikeys to rotate key",
        "DATABASE_URL": "Change database password and update connection string",
    }

    for pattern, command in rotation_commands.items():
        if pattern in secret_name.upper():
            return command

    return None


def generate_remediation_steps(
    timeline: SecretTimeline,
    secret_name: str,
) -> List[RemediationStep]:
    """Generate actionable remediation steps based on timeline analysis.

    Args:
        timeline: Secret timeline with leak information
        secret_name: Name of the leaked secret

    Returns:
        List of remediation steps ordered by priority
    """
    steps: List[RemediationStep] = []

    # Step 1: Always rotate the secret first
    rotation_cmd = get_rotation_command(secret_name)
    steps.append(
        RemediationStep(
            order=1,
            title="Rotate the secret IMMEDIATELY",
            description=(
                "The secret is compromised and must be replaced. "
                "Generate a new secret and update all systems using it."
            ),
            urgency="CRITICAL",
            command=rotation_cmd,
            warning="Do not skip this step - the secret is exposed!",
        )
    )

    # Step 2: Remove from git history if found in commits
    if timeline.commits_affected:
        filter_cmd = generate_filter_branch_command(timeline.files_affected)
        steps.append(
            RemediationStep(
                order=2,
                title="Remove from git history",
                description=(
                    f"Rewrite git history to remove the secret from {len(timeline.commits_affected)} "
                    f"commit(s). This will change commit hashes."
                ),
                urgency="HIGH",
                command=filter_cmd,
                warning="This rewrites history - coordinate with your team first!",
            )
        )

    # Step 3: Force push if needed
    if timeline.is_in_public_repo or len(timeline.branches_affected) > 0:
        steps.append(
            RemediationStep(
                order=3,
                title="Force push to update remote(s)",
                description=(
                    "Update remote repositories to remove the secret from public history. "
                    "All team members will need to rebase their branches."
                ),
                urgency="HIGH" if timeline.is_in_public_repo else "MEDIUM",
                command="git push origin --force --all",
                warning="Coordinate with team - force push affects all developers!",
            )
        )

    # Step 4: Update .gitignore
    steps.append(
        RemediationStep(
            order=4,
            title="Update .gitignore",
            description=(
                "Ensure .env and other secret files are in .gitignore " "to prevent future accidental commits."
            ),
            urgency="MEDIUM",
            command="echo '.env\n.env.local' >> .gitignore",
        )
    )

    # Step 5: Use secret manager
    steps.append(
        RemediationStep(
            order=5,
            title="Use a secret manager (recommended)",
            description=(
                "Move to a proper secret management solution like AWS Secrets Manager, "
                "HashiCorp Vault, or your cloud provider's secret store."
            ),
            urgency="MEDIUM",
            command="# Example: aws secretsmanager create-secret --name MySecret --secret-string ...",
        )
    )

    # Step 6: Install git hooks
    steps.append(
        RemediationStep(
            order=6,
            title="Install pre-commit hooks",
            description="Prevent future leaks by scanning commits before they're pushed.",
            urgency="LOW",
            command="envsync install-hooks  # Coming soon!",
        )
    )

    return steps

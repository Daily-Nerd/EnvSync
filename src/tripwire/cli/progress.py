"""Progress tracking utilities for TripWire CLI operations.

This module provides progress indicators for long-running operations like
git history auditing. It supports both progress bars (when total is known)
and spinners (when total is unknown).

Example:
    >>> with audit_progress(total_commits=100) as tracker:
    ...     for i in range(100):
    ...         tracker.update(commits_processed=i+1, secrets_found=0)
    ...     tracker.finish(total_secrets=5)
"""

from contextlib import contextmanager
from typing import Generator, Optional

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)


class AuditProgressTracker:
    """Tracks progress of git audit operations with live updates.

    Supports two display modes:
    1. Progress bar mode (when total_commits is known)
    2. Spinner mode (when total_commits is unknown)

    The tracker displays:
    - Commits processed (with percentage if total known)
    - Secrets found (highlighted in red when > 0)
    - Time elapsed

    Attributes:
        total_commits: Total commits to scan (None for unknown)
        commits_processed: Number of commits scanned so far
        secrets_found: Number of secrets detected
        _progress: Rich Progress instance for display
        _task_id: Task ID in progress display
        _console: Rich Console for output
    """

    def __init__(
        self,
        total_commits: Optional[int] = None,
        console: Optional[Console] = None,
    ) -> None:
        """Initialize progress tracker.

        Args:
            total_commits: Total commits to scan (None for spinner mode)
            console: Rich Console instance (creates new if not provided)
        """
        from tripwire.cli.utils.console import console as default_console

        self.total_commits = total_commits
        self.commits_processed = 0
        self.secrets_found = 0
        self._console = console or default_console

        # Build progress display based on mode
        if total_commits is not None:
            # Progress bar mode - show percentage and counts
            self._progress = Progress(
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("•"),
                TextColumn("[yellow]Secrets: {task.fields[secrets_found]}"),
                TextColumn("•"),
                TimeElapsedColumn(),
                console=self._console,
                transient=True,  # Disappear after completion
            )
        else:
            # Spinner mode - show counts without total
            self._progress = Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                TextColumn("•"),
                TextColumn("Commits: {task.fields[commits_processed]}"),
                TextColumn("•"),
                TextColumn("[yellow]Secrets: {task.fields[secrets_found]}"),
                TextColumn("•"),
                TimeElapsedColumn(),
                console=self._console,
                transient=True,  # Disappear after completion
            )

        self._task_id: Optional[TaskID] = None

    def start(self) -> None:
        """Start the progress display."""
        self._progress.start()

        if self.total_commits is not None:
            # Progress bar mode
            self._task_id = self._progress.add_task(
                "Scanning git history...",
                total=self.total_commits,
                secrets_found=0,
            )
        else:
            # Spinner mode (total=None makes it spin indefinitely)
            self._task_id = self._progress.add_task(
                "Scanning git history...",
                total=None,
                commits_processed=0,
                secrets_found=0,
            )

    def update(
        self,
        commits_processed: Optional[int] = None,
        secrets_found: Optional[int] = None,
    ) -> None:
        """Update progress display.

        Args:
            commits_processed: Current number of commits scanned
            secrets_found: Current number of secrets detected
        """
        if self._task_id is None:
            return

        # Update internal state
        if commits_processed is not None:
            self.commits_processed = commits_processed
        if secrets_found is not None:
            self.secrets_found = secrets_found

        # Update display based on mode
        if self.total_commits is not None:
            # Progress bar mode - update completed count
            self._progress.update(
                self._task_id,
                completed=self.commits_processed,
                secrets_found=self._format_secrets_count(self.secrets_found),
            )
        else:
            # Spinner mode - update field values
            self._progress.update(
                self._task_id,
                commits_processed=self.commits_processed,
                secrets_found=self._format_secrets_count(self.secrets_found),
            )

    def finish(self, total_secrets: int = 0) -> None:
        """Complete the progress display and show final summary.

        Args:
            total_secrets: Final count of secrets found
        """
        if self._task_id is None:
            return

        self.secrets_found = total_secrets

        # Mark task as complete
        if self.total_commits is not None:
            self._progress.update(
                self._task_id,
                completed=self.total_commits,
                secrets_found=self._format_secrets_count(total_secrets),
            )
        else:
            # For spinner mode, just update the final count
            self._progress.update(
                self._task_id,
                commits_processed=self.commits_processed,
                secrets_found=self._format_secrets_count(total_secrets),
            )

        # Stop the progress display (will disappear due to transient=True)
        self._progress.stop()

    def _format_secrets_count(self, count: int) -> str:
        """Format secrets count with color (red if > 0).

        Args:
            count: Number of secrets

        Returns:
            Formatted string with color markup
        """
        if count > 0:
            return f"[red]{count}[/red]"
        return str(count)

    def stop(self) -> None:
        """Stop the progress display (cleanup on error)."""
        if hasattr(self, "_progress"):
            self._progress.stop()


@contextmanager
def audit_progress(
    total_commits: Optional[int] = None,
    console: Optional[Console] = None,
) -> Generator[AuditProgressTracker, None, None]:
    """Context manager for git audit progress tracking.

    Automatically starts and stops progress display, handles cleanup on errors.

    Args:
        total_commits: Total commits to scan (None for spinner mode)
        console: Rich Console instance (optional)

    Yields:
        AuditProgressTracker instance for updating progress

    Example:
        >>> with audit_progress(total_commits=100) as tracker:
        ...     for i in range(100):
        ...         # Scan git history...
        ...         tracker.update(commits_processed=i+1, secrets_found=0)
        ...     tracker.finish(total_secrets=5)
    """
    tracker = AuditProgressTracker(total_commits=total_commits, console=console)
    tracker.start()

    try:
        yield tracker
    except Exception:
        # Ensure progress display is stopped on error
        tracker.stop()
        raise
    finally:
        # Clean up if finish() wasn't called
        if hasattr(tracker, "_progress") and tracker._progress.live.is_started:
            tracker.stop()


__all__ = ["AuditProgressTracker", "audit_progress"]

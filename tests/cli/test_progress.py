"""Tests for CLI progress tracking utilities."""

import time
from io import StringIO
from unittest.mock import MagicMock, Mock, patch

import pytest
from rich.console import Console

from tripwire.cli.progress import AuditProgressTracker, audit_progress


class TestAuditProgressTracker:
    """Test suite for AuditProgressTracker class."""

    def test_init_with_total_commits(self):
        """Test tracker initialization with known total."""
        tracker = AuditProgressTracker(total_commits=100)

        assert tracker.total_commits == 100
        assert tracker.commits_processed == 0
        assert tracker.secrets_found == 0
        assert tracker._task_id is None

    def test_init_without_total_commits(self):
        """Test tracker initialization with unknown total (spinner mode)."""
        tracker = AuditProgressTracker(total_commits=None)

        assert tracker.total_commits is None
        assert tracker.commits_processed == 0
        assert tracker.secrets_found == 0
        assert tracker._task_id is None

    def test_init_with_custom_console(self):
        """Test tracker initialization with custom console."""
        custom_console = Console(file=StringIO())
        tracker = AuditProgressTracker(total_commits=50, console=custom_console)

        assert tracker._console is custom_console

    def test_start_progress_bar_mode(self):
        """Test starting tracker in progress bar mode."""
        tracker = AuditProgressTracker(total_commits=100)
        tracker.start()

        assert tracker._task_id is not None
        assert tracker._progress.live.is_started

        tracker.stop()

    def test_start_spinner_mode(self):
        """Test starting tracker in spinner mode."""
        tracker = AuditProgressTracker(total_commits=None)
        tracker.start()

        assert tracker._task_id is not None
        assert tracker._progress.live.is_started

        tracker.stop()

    def test_update_progress_bar_mode(self):
        """Test updating progress in progress bar mode."""
        tracker = AuditProgressTracker(total_commits=100)
        tracker.start()

        tracker.update(commits_processed=50, secrets_found=2)

        assert tracker.commits_processed == 50
        assert tracker.secrets_found == 2

        tracker.stop()

    def test_update_spinner_mode(self):
        """Test updating progress in spinner mode."""
        tracker = AuditProgressTracker(total_commits=None)
        tracker.start()

        tracker.update(commits_processed=25, secrets_found=1)

        assert tracker.commits_processed == 25
        assert tracker.secrets_found == 1

        tracker.stop()

    def test_update_partial_values(self):
        """Test updating only some values."""
        tracker = AuditProgressTracker(total_commits=100)
        tracker.start()

        # Update only commits
        tracker.update(commits_processed=30)
        assert tracker.commits_processed == 30
        assert tracker.secrets_found == 0

        # Update only secrets
        tracker.update(secrets_found=5)
        assert tracker.commits_processed == 30
        assert tracker.secrets_found == 5

        tracker.stop()

    def test_update_without_start(self):
        """Test that update without start doesn't crash."""
        tracker = AuditProgressTracker(total_commits=100)

        # Should not crash
        tracker.update(commits_processed=10, secrets_found=1)

    def test_finish_progress_bar_mode(self):
        """Test finishing tracker in progress bar mode."""
        tracker = AuditProgressTracker(total_commits=100)
        tracker.start()

        tracker.update(commits_processed=80, secrets_found=3)
        tracker.finish(total_secrets=5)

        assert tracker.secrets_found == 5
        assert not tracker._progress.live.is_started

    def test_finish_spinner_mode(self):
        """Test finishing tracker in spinner mode."""
        tracker = AuditProgressTracker(total_commits=None)
        tracker.start()

        tracker.update(commits_processed=42, secrets_found=2)
        tracker.finish(total_secrets=3)

        assert tracker.secrets_found == 3
        assert not tracker._progress.live.is_started

    def test_finish_without_start(self):
        """Test that finish without start doesn't crash."""
        tracker = AuditProgressTracker(total_commits=100)

        # Should not crash
        tracker.finish(total_secrets=0)

    def test_stop_cleanup(self):
        """Test stop method cleans up properly."""
        tracker = AuditProgressTracker(total_commits=100)
        tracker.start()

        assert tracker._progress.live.is_started

        tracker.stop()

        assert not tracker._progress.live.is_started

    def test_format_secrets_count_zero(self):
        """Test formatting secrets count when zero."""
        tracker = AuditProgressTracker(total_commits=100)

        formatted = tracker._format_secrets_count(0)

        assert formatted == "0"
        assert "[red]" not in formatted

    def test_format_secrets_count_positive(self):
        """Test formatting secrets count when positive."""
        tracker = AuditProgressTracker(total_commits=100)

        formatted = tracker._format_secrets_count(5)

        assert "[red]5[/red]" == formatted

    def test_multiple_updates_accumulate(self):
        """Test multiple updates work correctly."""
        tracker = AuditProgressTracker(total_commits=200)
        tracker.start()

        tracker.update(commits_processed=50, secrets_found=1)
        assert tracker.commits_processed == 50
        assert tracker.secrets_found == 1

        tracker.update(commits_processed=100, secrets_found=3)
        assert tracker.commits_processed == 100
        assert tracker.secrets_found == 3

        tracker.update(commits_processed=150, secrets_found=5)
        assert tracker.commits_processed == 150
        assert tracker.secrets_found == 5

        tracker.stop()

    def test_edge_case_zero_total_commits(self):
        """Test tracker with zero total commits."""
        tracker = AuditProgressTracker(total_commits=0)
        tracker.start()

        tracker.update(commits_processed=0, secrets_found=0)
        tracker.finish(total_secrets=0)

        assert tracker.commits_processed == 0
        assert tracker.secrets_found == 0

    def test_edge_case_negative_values(self):
        """Test tracker handles negative values gracefully."""
        tracker = AuditProgressTracker(total_commits=100)
        tracker.start()

        # Negative values shouldn't crash
        tracker.update(commits_processed=-5, secrets_found=-1)

        # Values are stored as-is (no validation in tracker itself)
        assert tracker.commits_processed == -5
        assert tracker.secrets_found == -1

        tracker.stop()

    def test_large_numbers(self):
        """Test tracker with very large commit counts."""
        tracker = AuditProgressTracker(total_commits=1_000_000)
        tracker.start()

        tracker.update(commits_processed=500_000, secrets_found=100)
        tracker.finish(total_secrets=150)

        assert tracker.commits_processed == 500_000
        assert tracker.secrets_found == 150

        tracker.stop()


class TestAuditProgressContextManager:
    """Test suite for audit_progress context manager."""

    def test_context_manager_basic_usage(self):
        """Test basic context manager usage."""
        with audit_progress(total_commits=100) as tracker:
            assert isinstance(tracker, AuditProgressTracker)
            assert tracker.total_commits == 100
            assert tracker._progress.live.is_started

        # After exiting, progress should be stopped
        assert not tracker._progress.live.is_started

    def test_context_manager_spinner_mode(self):
        """Test context manager in spinner mode."""
        with audit_progress(total_commits=None) as tracker:
            assert tracker.total_commits is None
            assert tracker._progress.live.is_started

        assert not tracker._progress.live.is_started

    def test_context_manager_with_custom_console(self):
        """Test context manager with custom console."""
        custom_console = Console(file=StringIO())

        with audit_progress(total_commits=50, console=custom_console) as tracker:
            assert tracker._console is custom_console

    def test_context_manager_updates(self):
        """Test updating progress inside context manager."""
        with audit_progress(total_commits=100) as tracker:
            tracker.update(commits_processed=25, secrets_found=1)
            assert tracker.commits_processed == 25
            assert tracker.secrets_found == 1

            tracker.update(commits_processed=50, secrets_found=3)
            assert tracker.commits_processed == 50
            assert tracker.secrets_found == 3

            tracker.finish(total_secrets=5)
            assert tracker.secrets_found == 5

    def test_context_manager_exception_handling(self):
        """Test context manager cleans up on exception."""
        tracker = None

        with pytest.raises(ValueError, match="Test error"):
            with audit_progress(total_commits=100) as tracker:
                tracker.update(commits_processed=10)
                raise ValueError("Test error")

        # Tracker should be stopped even after exception
        assert not tracker._progress.live.is_started

    def test_context_manager_cleanup_without_finish(self):
        """Test context manager cleans up even if finish() not called."""
        with audit_progress(total_commits=100) as tracker:
            tracker.update(commits_processed=50, secrets_found=2)
            # Deliberately not calling finish()

        # Should still clean up
        assert not tracker._progress.live.is_started

    def test_context_manager_multiple_sequential(self):
        """Test using context manager multiple times sequentially."""
        # First context
        with audit_progress(total_commits=100) as tracker1:
            tracker1.update(commits_processed=50, secrets_found=1)
            tracker1.finish(total_secrets=1)

        assert not tracker1._progress.live.is_started

        # Second context
        with audit_progress(total_commits=200) as tracker2:
            tracker2.update(commits_processed=100, secrets_found=2)
            tracker2.finish(total_secrets=2)

        assert not tracker2._progress.live.is_started

    def test_context_manager_nested_exception_handling(self):
        """Test nested exception handling."""
        with pytest.raises(RuntimeError, match="Inner error"):
            with audit_progress(total_commits=100) as tracker:
                tracker.update(commits_processed=10)

                try:
                    raise ValueError("Caught error")
                except ValueError:
                    # Caught and handled
                    pass

                # This should propagate
                raise RuntimeError("Inner error")


class TestProgressIntegration:
    """Integration tests for progress tracking with mocked git operations."""

    def test_progress_with_simulated_audit(self):
        """Test progress tracking with simulated audit workflow."""
        total = 100

        with audit_progress(total_commits=total) as tracker:
            secrets_found = 0

            # Simulate scanning commits
            for i in range(1, total + 1):
                # Simulate finding a secret every 20 commits
                if i % 20 == 0:
                    secrets_found += 1

                tracker.update(commits_processed=i, secrets_found=secrets_found)

                # Simulate work
                time.sleep(0.001)

            tracker.finish(total_secrets=secrets_found)

        assert tracker.commits_processed == 100
        assert tracker.secrets_found == 5

    def test_progress_with_spinner_simulated_audit(self):
        """Test spinner mode with simulated audit workflow."""
        with audit_progress(total_commits=None) as tracker:
            secrets_found = 0
            commits = 0

            # Simulate scanning unknown number of commits
            for i in range(1, 43):  # Arbitrary number
                commits = i

                if i % 15 == 0:
                    secrets_found += 1

                tracker.update(commits_processed=commits, secrets_found=secrets_found)
                time.sleep(0.001)

            tracker.finish(total_secrets=secrets_found)

        assert tracker.commits_processed == 42
        assert tracker.secrets_found == 2

    def test_progress_with_early_termination(self):
        """Test progress tracking when audit terminates early."""
        total = 1000

        with audit_progress(total_commits=total) as tracker:
            # Simulate stopping after 100 commits
            for i in range(1, 101):
                tracker.update(commits_processed=i, secrets_found=0)

                if i == 100:
                    break

            # Finish early
            tracker.finish(total_secrets=0)

        # Should have processed only 100, not 1000
        assert tracker.commits_processed == 100

    def test_progress_no_secrets_found(self):
        """Test progress tracking when no secrets are found."""
        with audit_progress(total_commits=50) as tracker:
            for i in range(1, 51):
                tracker.update(commits_processed=i, secrets_found=0)

            tracker.finish(total_secrets=0)

        assert tracker.secrets_found == 0

    def test_progress_many_secrets_found(self):
        """Test progress tracking when many secrets are found."""
        with audit_progress(total_commits=100) as tracker:
            secrets = 0

            for i in range(1, 101):
                # Every 5th commit has a secret
                if i % 5 == 0:
                    secrets += 1

                tracker.update(commits_processed=i, secrets_found=secrets)

            tracker.finish(total_secrets=secrets)

        assert tracker.secrets_found == 20


class TestProgressEdgeCases:
    """Test edge cases and error conditions."""

    def test_tracker_without_console(self):
        """Test tracker uses default console if none provided."""
        tracker = AuditProgressTracker(total_commits=100)

        # Should have a console instance
        assert tracker._console is not None

    def test_finish_updates_secrets_found(self):
        """Test that finish() updates secrets_found correctly."""
        tracker = AuditProgressTracker(total_commits=100)
        tracker.start()

        tracker.update(commits_processed=100, secrets_found=3)

        # Finish with different secret count
        tracker.finish(total_secrets=7)

        assert tracker.secrets_found == 7

        tracker.stop()

    def test_stop_is_idempotent(self):
        """Test that calling stop() multiple times is safe."""
        tracker = AuditProgressTracker(total_commits=100)
        tracker.start()

        tracker.stop()
        tracker.stop()  # Should not crash
        tracker.stop()  # Should not crash

    def test_context_manager_with_zero_commits(self):
        """Test context manager with zero commits."""
        with audit_progress(total_commits=0) as tracker:
            tracker.finish(total_secrets=0)

        assert tracker.commits_processed == 0
        assert tracker.secrets_found == 0

    def test_update_incremental_values(self):
        """Test updating with incremental values."""
        tracker = AuditProgressTracker(total_commits=100)
        tracker.start()

        # Update in increments
        for i in [10, 20, 30, 40, 50]:
            tracker.update(commits_processed=i)

        assert tracker.commits_processed == 50

        tracker.stop()

    def test_secrets_formatting_in_display(self):
        """Test that secrets are formatted correctly in display."""
        tracker = AuditProgressTracker(total_commits=100)

        # Zero secrets - no red
        assert tracker._format_secrets_count(0) == "0"

        # Positive secrets - red color
        assert "[red]" in tracker._format_secrets_count(1)
        assert "[red]" in tracker._format_secrets_count(10)
        assert "[red]" in tracker._format_secrets_count(100)


@pytest.mark.parametrize(
    "total_commits,expected_mode",
    [
        (100, "progress_bar"),
        (None, "spinner"),
        (0, "progress_bar"),
        (1, "progress_bar"),
        (1000000, "progress_bar"),
    ],
)
def test_tracker_mode_selection(total_commits, expected_mode):
    """Test tracker selects correct mode based on total_commits."""
    tracker = AuditProgressTracker(total_commits=total_commits)

    if expected_mode == "progress_bar":
        assert tracker.total_commits is not None or tracker.total_commits == 0
    else:  # spinner
        assert tracker.total_commits is None


@pytest.mark.parametrize(
    "secrets_count,expected_contains_red",
    [
        (0, False),
        (1, True),
        (5, True),
        (100, True),
    ],
)
def test_secrets_formatting(secrets_count, expected_contains_red):
    """Test secrets count formatting with various values."""
    tracker = AuditProgressTracker(total_commits=100)
    formatted = tracker._format_secrets_count(secrets_count)

    if expected_contains_red:
        assert "[red]" in formatted
        assert "[/red]" in formatted
    else:
        assert "[red]" not in formatted

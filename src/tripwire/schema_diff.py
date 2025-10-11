"""
Schema diff and migration functionality for TripWire.

This module provides tools for comparing schema versions and migrating
.env files between schemas safely.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from tripwire.schema import TripWireSchema, VariableSchema


class ChangeType(Enum):
    """Type of change detected in schema diff."""

    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


class BreakingChangeType(Enum):
    """Types of breaking changes."""

    NEW_REQUIRED_VAR = "new_required_var"
    REMOVED_REQUIRED_VAR = "removed_required_var"
    TYPE_CHANGE = "type_change"
    FORMAT_ADDED = "format_added"
    STRICTER_VALIDATION = "stricter_validation"


@dataclass
class VariableChange:
    """Represents a change to a single variable."""

    variable_name: str
    change_type: ChangeType
    old_schema: Optional[VariableSchema] = None
    new_schema: Optional[VariableSchema] = None
    changes: List[str] = field(default_factory=list)
    breaking: bool = False
    breaking_reasons: List[BreakingChangeType] = field(default_factory=list)

    def add_change(self, description: str, breaking: bool = False, reason: Optional[BreakingChangeType] = None) -> None:
        """Add a change description."""
        self.changes.append(description)
        if breaking:
            self.breaking = True
            if reason:
                self.breaking_reasons.append(reason)


@dataclass
class SchemaDiff:
    """Complete diff between two schemas."""

    added_variables: List[VariableChange] = field(default_factory=list)
    removed_variables: List[VariableChange] = field(default_factory=list)
    modified_variables: List[VariableChange] = field(default_factory=list)
    unchanged_variables: List[str] = field(default_factory=list)

    @property
    def has_breaking_changes(self) -> bool:
        """Check if diff contains breaking changes."""
        for change in self.added_variables + self.removed_variables + self.modified_variables:
            if change.breaking:
                return True
        return False

    @property
    def breaking_changes(self) -> List[VariableChange]:
        """Get all breaking changes."""
        changes = []
        for change in self.added_variables + self.removed_variables + self.modified_variables:
            if change.breaking:
                changes.append(change)
        return changes

    def summary(self) -> Dict[str, int]:
        """Get summary statistics."""
        return {
            "added": len(self.added_variables),
            "removed": len(self.removed_variables),
            "modified": len(self.modified_variables),
            "unchanged": len(self.unchanged_variables),
            "breaking": len(self.breaking_changes),
        }


def compare_schemas(old_schema: TripWireSchema, new_schema: TripWireSchema) -> SchemaDiff:
    """
    Compare two schemas and return diff.

    Args:
        old_schema: Original schema
        new_schema: New schema to compare against

    Returns:
        SchemaDiff object containing all changes
    """
    diff = SchemaDiff()

    old_vars = set(old_schema.variables.keys())
    new_vars = set(new_schema.variables.keys())

    # Find added variables
    for var_name in new_vars - old_vars:
        var_schema = new_schema.variables[var_name]
        change = VariableChange(
            variable_name=var_name,
            change_type=ChangeType.ADDED,
            new_schema=var_schema,
        )

        # New required variable is breaking
        if var_schema.required:
            change.add_change(
                "New required variable",
                breaking=True,
                reason=BreakingChangeType.NEW_REQUIRED_VAR,
            )
        else:
            change.add_change("New optional variable")

        diff.added_variables.append(change)

    # Find removed variables
    for var_name in old_vars - new_vars:
        var_schema = old_schema.variables[var_name]
        change = VariableChange(
            variable_name=var_name,
            change_type=ChangeType.REMOVED,
            old_schema=var_schema,
        )

        # Removed required variable is breaking
        if var_schema.required:
            change.add_change(
                "Removed required variable",
                breaking=True,
                reason=BreakingChangeType.REMOVED_REQUIRED_VAR,
            )
        else:
            change.add_change("Removed optional variable")

        diff.removed_variables.append(change)

    # Find modified variables
    for var_name in old_vars & new_vars:
        old_var = old_schema.variables[var_name]
        new_var = new_schema.variables[var_name]

        changes = _compare_variable_schemas(old_var, new_var)

        if changes.changes:
            changes.variable_name = var_name
            changes.change_type = ChangeType.MODIFIED
            diff.modified_variables.append(changes)
        else:
            diff.unchanged_variables.append(var_name)

    return diff


def _compare_variable_schemas(old_var: VariableSchema, new_var: VariableSchema) -> VariableChange:
    """Compare two variable schemas and return changes."""
    change = VariableChange(
        variable_name=old_var.name,
        change_type=ChangeType.UNCHANGED,
        old_schema=old_var,
        new_schema=new_var,
    )

    # Type change
    if old_var.type != new_var.type:
        change.add_change(
            f"Type: {old_var.type} → {new_var.type}",
            breaking=True,
            reason=BreakingChangeType.TYPE_CHANGE,
        )

    # Required status change
    if old_var.required != new_var.required:
        if new_var.required:
            change.add_change(
                "Optional → Required",
                breaking=True,
                reason=BreakingChangeType.NEW_REQUIRED_VAR,
            )
        else:
            change.add_change("Required → Optional")

    # Default value change
    if old_var.default != new_var.default:
        change.add_change(f"Default: {old_var.default} → {new_var.default}")

    # Format validation change
    if old_var.format != new_var.format:
        if old_var.format is None and new_var.format is not None:
            change.add_change(
                f"Format validation added: {new_var.format}",
                breaking=True,
                reason=BreakingChangeType.FORMAT_ADDED,
            )
        elif old_var.format is not None and new_var.format is None:
            change.add_change(f"Format validation removed: {old_var.format}")
        else:
            change.add_change(f"Format: {old_var.format} → {new_var.format}")

    # Pattern change
    if old_var.pattern != new_var.pattern:
        change.add_change(f"Pattern: {old_var.pattern} → {new_var.pattern}")

    # Choices change
    if old_var.choices != new_var.choices:
        change.add_change(f"Choices: {old_var.choices} → {new_var.choices}")

    # Range changes (min/max)
    if old_var.min != new_var.min:
        if new_var.min is not None and (old_var.min is None or new_var.min > old_var.min):
            change.add_change(
                f"Min: {old_var.min} → {new_var.min}",
                breaking=True,
                reason=BreakingChangeType.STRICTER_VALIDATION,
            )
        else:
            change.add_change(f"Min: {old_var.min} → {new_var.min}")

    if old_var.max != new_var.max:
        if new_var.max is not None and (old_var.max is None or new_var.max < old_var.max):
            change.add_change(
                f"Max: {old_var.max} → {new_var.max}",
                breaking=True,
                reason=BreakingChangeType.STRICTER_VALIDATION,
            )
        else:
            change.add_change(f"Max: {old_var.max} → {new_var.max}")

    # Length changes
    if old_var.min_length != new_var.min_length:
        if new_var.min_length is not None and (old_var.min_length is None or new_var.min_length > old_var.min_length):
            change.add_change(
                f"Min length: {old_var.min_length} → {new_var.min_length}",
                breaking=True,
                reason=BreakingChangeType.STRICTER_VALIDATION,
            )
        else:
            change.add_change(f"Min length: {old_var.min_length} → {new_var.min_length}")

    if old_var.max_length != new_var.max_length:
        if new_var.max_length is not None and (old_var.max_length is None or new_var.max_length < old_var.max_length):
            change.add_change(
                f"Max length: {old_var.max_length} → {new_var.max_length}",
                breaking=True,
                reason=BreakingChangeType.STRICTER_VALIDATION,
            )
        else:
            change.add_change(f"Max length: {old_var.max_length} → {new_var.max_length}")

    # Description change (non-breaking)
    if old_var.description != new_var.description:
        change.add_change("Description updated")

    # Secret status change
    if old_var.secret != new_var.secret:
        change.add_change(f"Secret: {old_var.secret} → {new_var.secret}")

    return change


@dataclass
class MigrationPlan:
    """Plan for migrating .env file between schemas."""

    old_schema: TripWireSchema
    new_schema: TripWireSchema
    diff: SchemaDiff
    env_file: Path
    backup_file: Optional[Path] = None

    def execute(
        self, dry_run: bool = False, interactive: bool = False, create_backup: bool = True
    ) -> Tuple[bool, List[str]]:
        """
        Execute migration plan.

        Args:
            dry_run: If True, don't actually modify files
            interactive: If True, confirm each change
            create_backup: If True, create backup before migration

        Returns:
            (success, list_of_messages)
        """
        messages = []

        # Read existing .env file
        if not self.env_file.exists():
            return False, ["Error: .env file not found"]

        env_content = self.env_file.read_text()
        env_vars = self._parse_env_file(env_content)

        # Create backup if not dry run and backup requested
        if not dry_run and create_backup:
            backup_path = (
                self.env_file.parent / f"{self.env_file.name}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            backup_path.write_text(env_content)
            self.backup_file = backup_path
            messages.append(f"Created backup: {backup_path}")

        # Process changes
        changes_applied = 0

        # Add new variables
        for change in self.diff.added_variables:
            var_name = change.variable_name
            var_schema = change.new_schema

            if var_schema is None:
                continue

            if var_schema.default is not None:
                env_vars[var_name] = str(var_schema.default)
                changes_applied += 1
                messages.append(f"+ {var_name} (added with default: {var_schema.default})")
            elif var_schema.required:
                env_vars[var_name] = "CHANGE_ME"
                changes_applied += 1
                messages.append(f"+ {var_name} (added with placeholder - REQUIRES VALUE)")

        # Remove deprecated variables
        for change in self.diff.removed_variables:
            var_name = change.variable_name
            if var_name in env_vars:
                old_value = env_vars.pop(var_name)
                changes_applied += 1
                messages.append(f"- {var_name} (removed, old value: {old_value[:20]}...)")

        # Handle modified variables (type conversions)
        for change in self.diff.modified_variables:
            var_name = change.variable_name
            if var_name not in env_vars:
                continue

            old_value = env_vars[var_name]

            # Type conversion
            if "Type:" in " ".join(change.changes) and change.new_schema is not None:
                try:
                    # Attempt to convert value to new type
                    new_type = change.new_schema.type
                    if new_type == "int":
                        env_vars[var_name] = str(int(float(old_value)))
                    elif new_type == "float":
                        env_vars[var_name] = str(float(old_value))
                    elif new_type == "bool":
                        env_vars[var_name] = "true" if old_value.lower() in ["true", "1", "yes"] else "false"

                    changes_applied += 1
                    messages.append(f"~ {var_name}: Converted to {new_type}")
                except (ValueError, AttributeError):
                    messages.append(f"! {var_name}: Could not convert to {new_type}, manual update needed")

        # Write updated file if not dry run
        if not dry_run:
            new_content = self._format_env_file(env_vars)
            self.env_file.write_text(new_content)
            messages.append(f"\nMigrated {self.env_file}")
            messages.append(f"Applied {changes_applied} change(s)")

        return True, messages

    def _parse_env_file(self, content: str) -> Dict[str, str]:
        """Parse .env file content into dict."""
        env_vars = {}
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()
        return env_vars

    def _format_env_file(self, env_vars: Dict[str, str]) -> str:
        """Format env vars dict back to .env file format."""
        lines = [
            "# Environment Variables",
            f"# Migrated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        for key, value in sorted(env_vars.items()):
            lines.append(f"{key}={value}")

        return "\n".join(lines)


def create_migration_plan(
    old_schema_path: Path,
    new_schema_path: Path,
    env_file_path: Path,
) -> MigrationPlan:
    """
    Create migration plan from schema files.

    Args:
        old_schema_path: Path to old schema
        new_schema_path: Path to new schema
        env_file_path: Path to .env file to migrate

    Returns:
        MigrationPlan object
    """
    old_schema = TripWireSchema.from_toml(old_schema_path)
    new_schema = TripWireSchema.from_toml(new_schema_path)

    diff = compare_schemas(old_schema, new_schema)

    return MigrationPlan(
        old_schema=old_schema,
        new_schema=new_schema,
        diff=diff,
        env_file=env_file_path,
    )

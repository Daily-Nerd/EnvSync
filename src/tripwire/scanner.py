"""Code scanner for discovering environment variable usage.

This module uses AST parsing to find env.require() and env.optional() calls
in Python source files, extracting metadata about environment variables.
"""

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set

from tripwire.constants import SKIP_DIRS

# Resource limits to prevent DOS attacks and memory exhaustion
MAX_FILE_SIZE = 1_000_000  # 1MB maximum file size to scan


@dataclass
class EnvVarInfo:
    """Information about a discovered environment variable.

    Attributes:
        name: Variable name
        required: Whether the variable is required
        var_type: Python type (str, int, bool, etc.)
        default: Default value (None for required vars)
        description: Human-readable description
        format: Built-in format validator (email, url, etc.)
        pattern: Custom regex pattern
        choices: List of allowed values
        min_val: Minimum value for numeric types
        max_val: Maximum value for numeric types
        secret: Whether variable contains sensitive data
        file_path: Path to source file where discovered
        line_number: Line number in source file
    """

    name: str
    required: bool
    var_type: str
    default: Any
    description: Optional[str]
    format: Optional[str]
    pattern: Optional[str]
    choices: Optional[List[str]]
    min_val: Optional[float]
    max_val: Optional[float]
    secret: bool
    file_path: Path
    line_number: int


class EnvVarScanner(ast.NodeVisitor):
    """AST visitor for scanning environment variable declarations."""

    def __init__(self, file_path: Path) -> None:
        """Initialize scanner for a specific file.

        Args:
            file_path: Path to Python file being scanned
        """
        self.file_path = file_path
        self.variables: List[EnvVarInfo] = []
        self.env_names: Set[str] = set()

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function call nodes to find env.require() and env.optional().

        Args:
            node: AST Call node
        """
        # Check if this is env.require() or env.optional()
        is_require = False
        is_optional = False

        if isinstance(node.func, ast.Attribute):
            # env.require() or env.optional()
            if isinstance(node.func.value, ast.Name):
                obj_name = node.func.value.id
                method_name = node.func.attr

                if obj_name in ("env", "TripWire"):
                    if method_name == "require":
                        is_require = True
                    elif method_name == "optional":
                        is_optional = True

        if is_require or is_optional:
            var_info = self._extract_var_info(node, is_require)
            if var_info:
                self.variables.append(var_info)

        # Continue visiting child nodes
        self.generic_visit(node)

    def _extract_var_info(self, node: ast.Call, is_require: bool) -> Optional[EnvVarInfo]:
        """Extract environment variable information from a call node.

        Args:
            node: AST Call node for env.require() or env.optional()
            is_require: True if require(), False if optional()

        Returns:
            EnvVarInfo object or None if parsing fails
        """
        # First argument must be the variable name (string literal)
        if not node.args or not isinstance(node.args[0], ast.Constant):
            return None

        var_name = node.args[0].value
        if not isinstance(var_name, str):
            return None

        # Extract keyword arguments
        kwargs = {}
        for keyword in node.keywords:
            if keyword.arg:
                kwargs[keyword.arg] = self._extract_value(keyword.value)

        # Determine if required (require() without default, or optional() has default)
        required = is_require and "default" not in kwargs
        default = kwargs.get("default")

        # Extract type (defaults to str)
        var_type_raw = kwargs.get("type", "str")
        var_type = self._extract_type_name(var_type_raw)

        # Extract validation parameters
        description = kwargs.get("description")
        format_val = kwargs.get("format")
        pattern = kwargs.get("pattern")
        choices = kwargs.get("choices")
        min_val = kwargs.get("min_val")
        max_val = kwargs.get("max_val")
        secret = kwargs.get("secret", False)

        return EnvVarInfo(
            name=var_name,
            required=required,
            var_type=var_type,
            default=default,
            description=description,
            format=format_val,
            pattern=pattern,
            choices=choices,
            min_val=min_val,
            max_val=max_val,
            secret=bool(secret),
            file_path=self.file_path,
            line_number=node.lineno,
        )

    def _extract_value(self, node: ast.expr) -> Any:
        """Extract a Python value from an AST node.

        Args:
            node: AST expression node

        Returns:
            Python value or None if extraction fails
        """
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            # For type references like 'int', 'str', etc.
            return node.id
        elif isinstance(node, ast.List):
            return [self._extract_value(elt) for elt in node.elts]
        elif isinstance(node, ast.Dict):
            # Dict keys can be None in some cases (e.g., **dict unpacking)
            result = {}
            for k, v in zip(node.keys, node.values):
                if k is not None:
                    key = self._extract_value(k)
                    value = self._extract_value(v)
                    if key is not None:
                        result[key] = value
            return result
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            # Handle negative numbers
            if isinstance(node.operand, ast.Constant):
                val = node.operand.value
                # Only negate numeric types
                if isinstance(val, (int, float)):
                    return -val
        return None

    def _extract_type_name(self, type_value: Any) -> str:
        """Extract type name from various representations.

        Args:
            type_value: Type value (could be string, type name, etc.)

        Returns:
            Type name as string
        """
        if isinstance(type_value, str):
            return type_value
        elif type_value in ("int", "float", "bool", "str", "list", "dict"):
            return str(type_value)
        else:
            return "str"


def scan_file(file_path: Path) -> List[EnvVarInfo]:
    """Scan a single Python file for environment variable usage.

    Args:
        file_path: Path to Python file

    Returns:
        List of discovered environment variables

    Raises:
        SyntaxError: If file contains invalid Python syntax
    """
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))

        scanner = EnvVarScanner(file_path)
        scanner.visit(tree)

        return scanner.variables
    except SyntaxError as e:
        # Re-raise with more context
        raise SyntaxError(f"Syntax error in {file_path}: {e}") from e


def scan_directory(
    directory: Path,
    exclude_patterns: Optional[List[str]] = None,
    max_depth: Optional[int] = None,
) -> List[EnvVarInfo]:
    """Scan a directory recursively for environment variable usage.

    Uses efficient directory-level filtering to skip entire trees
    (like .venv/, __pycache__/) instead of checking every file.

    Args:
        directory: Root directory to scan
        exclude_patterns: Patterns to exclude (e.g., ['tests/*', '.venv/*'])
        max_depth: Maximum directory depth (None for unlimited)

    Returns:
        List of all discovered environment variables
    """
    if exclude_patterns is None:
        exclude_patterns = [
            "tests/*",
            "tests/**/*",
            ".venv/*",
            "venv/*",
            ".git/*",
            "__pycache__/*",
            "*.pyc",
        ]

    def should_skip_dir(dir_path: Path) -> bool:
        """Check if directory should be skipped entirely."""
        dir_name = dir_path.name

        # Skip known directories
        if dir_name in SKIP_DIRS:
            return True

        # Skip hidden directories (except project root)
        if dir_name.startswith(".") and dir_path != directory:
            return True

        # Skip egg-info directories
        if dir_name.endswith(".egg-info"):
            return True

        return False

    def should_exclude_file(file_path: Path) -> bool:
        """Check if file should be excluded by pattern matching."""
        try:
            relative_path = file_path.relative_to(directory)
        except ValueError:
            return True

        # Check against exclude patterns
        for pattern in exclude_patterns:
            if relative_path.match(pattern):
                return True

        return False

    def walk_python_files(current_dir: Path, depth: int = 0) -> Iterator[Path]:
        """Recursively walk directory tree, skipping unwanted dirs."""
        # Check depth limit
        if max_depth is not None and depth > max_depth:
            return

        try:
            for item in current_dir.iterdir():
                # Skip if not accessible
                if not item.exists():
                    continue

                if item.is_dir():
                    # Directory-level filtering - skip entire trees
                    if should_skip_dir(item):
                        continue
                    # Recurse into allowed directories
                    yield from walk_python_files(item, depth + 1)

                elif item.is_file() and item.suffix == ".py":
                    # File-level filtering
                    if not should_exclude_file(item):
                        yield item

        except PermissionError:
            # Skip directories we can't access
            pass

    all_variables: List[EnvVarInfo] = []

    # Scan all discovered Python files
    for py_file in walk_python_files(directory):
        # Security: Check file size before reading to prevent memory exhaustion
        try:
            file_size = py_file.stat().st_size
            if file_size > MAX_FILE_SIZE:
                # Skip excessively large files
                continue
        except OSError:
            # Skip files we can't stat
            continue

        # Scan file
        try:
            variables = scan_file(py_file)
            all_variables.extend(variables)
        except (SyntaxError, UnicodeDecodeError):
            # Skip files with syntax errors or encoding issues
            continue

    return all_variables


def deduplicate_variables(variables: List[EnvVarInfo]) -> Dict[str, EnvVarInfo]:
    """Deduplicate variables by name, keeping first occurrence.

    Args:
        variables: List of discovered variables (may contain duplicates)

    Returns:
        Dictionary mapping variable name to info (deduplicated)
    """
    seen: Dict[str, EnvVarInfo] = {}

    for var in variables:
        if var.name not in seen:
            seen[var.name] = var

    return seen


def format_var_for_env_example(var: EnvVarInfo, include_comments: bool = True) -> str:
    """Format a variable for .env.example file.

    Args:
        var: Variable information
        include_comments: Whether to include descriptive comments

    Returns:
        Formatted string for .env.example
    """
    lines = []

    if include_comments and var.description:
        lines.append(f"# {var.description}")

    if include_comments:
        # Add type and requirement info
        type_info = f"Type: {var.var_type}"
        required_info = "Required" if var.required else "Optional"
        lines.append(f"# {required_info} | {type_info}")

        # Add validation info
        if var.format:
            lines.append(f"# Format: {var.format}")
        if var.choices:
            lines.append(f"# Choices: {', '.join(str(c) for c in var.choices)}")
        if var.min_val is not None or var.max_val is not None:
            range_parts = []
            if var.min_val is not None:
                range_parts.append(f"min={var.min_val}")
            if var.max_val is not None:
                range_parts.append(f"max={var.max_val}")
            lines.append(f"# Range: {', '.join(range_parts)}")

    # Add the actual variable line
    if var.required:
        # Required variables have no default
        if var.secret:
            lines.append(f"{var.name}=<YOUR_SECRET_HERE>")
        else:
            lines.append(f"{var.name}=")
    else:
        # Optional variables show their default
        default_str = format_default_value(var.default)
        lines.append(f"{var.name}={default_str}")

    return "\n".join(lines)


def format_default_value(value: Any) -> str:
    """Format a default value for .env file.

    Args:
        value: Default value

    Returns:
        String representation suitable for .env file
    """
    if value is None:
        return ""
    elif isinstance(value, bool):
        return str(value).lower()
    elif isinstance(value, (list, dict)):
        import json

        return json.dumps(value)
    else:
        return str(value)

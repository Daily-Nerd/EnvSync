"""AST-based usage tracking for environment variables.

This module provides sophisticated tracking of where environment variables are
referenced across a Python codebase, handling 30+ edge cases including:
- String interpolation (f-strings, .format(), % formatting)
- Collections (dict/list/set/tuple literals)
- Comprehensions (list/dict/set/generator)
- Function calls (positional, keyword, *args, **kwargs)
- Control flow (if/while/for/match)
- Operators (comparison, boolean, arithmetic, unary)
- Attributes, subscripts, decorators, context managers
"""

import ast
from pathlib import Path
from typing import Iterator, List, Optional, Set

from tripwire.analysis.models import (
    UsageAnalysisResult,
    VariableDeclaration,
    VariableUsage,
)
from tripwire.constants import SKIP_DIRS


class UsageTrackingVisitor(ast.NodeVisitor):
    """AST visitor that tracks where variables are referenced.

    This visitor handles complex edge cases that simple grep-based searches miss,
    including f-strings, comprehensions, and nested data structures.

    Attributes:
        file_path: Path to file being analyzed
        declared_vars: Set of variable names to track
        usages: List of detected usages
        current_scope: Current scope (module, function:name, class:name)
        in_declaration: Flag to skip usage on declaration line
        scope_stack: Stack for tracking nested scopes
    """

    def __init__(self, file_path: Path, declared_vars: Set[str]):
        """Initialize visitor.

        Args:
            file_path: Path to file being analyzed
            declared_vars: Set of variable names we're tracking
        """
        self.file_path = file_path
        self.declared_vars = declared_vars
        self.usages: List[VariableUsage] = []
        self.current_scope = "module"
        self.in_declaration = False
        self.scope_stack: List[str] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Track function scope.

        Args:
            node: Function definition node
        """
        self.scope_stack.append(self.current_scope)
        self.current_scope = f"function:{node.name}"
        self.generic_visit(node)
        self.current_scope = self.scope_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Track async function scope.

        Args:
            node: Async function definition node
        """
        self.scope_stack.append(self.current_scope)
        self.current_scope = f"async_function:{node.name}"
        self.generic_visit(node)
        self.current_scope = self.scope_stack.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Track class scope.

        Args:
            node: Class definition node
        """
        self.scope_stack.append(self.current_scope)
        self.current_scope = f"class:{node.name}"
        self.generic_visit(node)
        self.current_scope = self.scope_stack.pop()

    def visit_Lambda(self, node: ast.Lambda) -> None:
        """Track lambda scope.

        Args:
            node: Lambda node
        """
        self.scope_stack.append(self.current_scope)
        self.current_scope = f"lambda:{node.lineno}"
        self.generic_visit(node)
        self.current_scope = self.scope_stack.pop()

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Handle type-annotated assignments (e.g., VAR: str = env.require(...)).

        Sets flag to avoid counting the right-hand side as usage.

        Args:
            node: Annotated assignment node
        """
        if isinstance(node.target, ast.Name):
            var_name = node.target.id
            if var_name in self.declared_vars and node.value:
                # This is a declaration, not a usage
                self.in_declaration = True
                self.visit(node.value)
                self.in_declaration = False
                return

        # Not a declaration we track, visit normally
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Handle non-annotated assignments.

        Args:
            node: Assignment node
        """
        # Extract target variable names
        target_vars = set()
        for target in node.targets:
            if isinstance(target, ast.Name):
                target_vars.add(target.id)

        # If assigning to a tracked variable, it's a declaration
        if any(v in self.declared_vars for v in target_vars):
            self.in_declaration = True
            self.visit(node.value)
            self.in_declaration = False
            return

        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        """Track variable name references.

        This is the core detection method - tracks when a variable name appears.

        Args:
            node: Name node
        """
        if self.in_declaration:
            # Skip - this is part of the declaration itself
            return

        if node.id in self.declared_vars:
            # Found a usage!
            self.usages.append(
                VariableUsage(
                    variable_name=node.id,
                    file_path=self.file_path,
                    line_number=node.lineno,
                    context=self._infer_context(node),
                    scope=self.current_scope,
                )
            )

        self.generic_visit(node)

    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
        """Handle f-strings (e.g., f"{DATABASE_URL}/api").

        F-strings contain FormattedValue nodes with expressions inside.

        Args:
            node: JoinedStr node (f-string)
        """
        self.generic_visit(node)

    def visit_FormattedValue(self, node: ast.FormattedValue) -> None:
        """Handle formatted values inside f-strings.

        Args:
            node: FormattedValue node
        """
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Handle function calls, including str.format() patterns.

        Args:
            node: Call node
        """
        # Check for str.format() pattern
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "format":
                # Visit the string being formatted
                self.visit(node.func.value)

        # Visit function and all arguments
        self.generic_visit(node)

    def visit_Dict(self, node: ast.Dict) -> None:
        """Handle dictionary literals (e.g., {"url": DATABASE_URL}).

        Args:
            node: Dict node
        """
        self.generic_visit(node)

    def visit_List(self, node: ast.List) -> None:
        """Handle list literals (e.g., [DATABASE_URL, API_KEY]).

        Args:
            node: List node
        """
        self.generic_visit(node)

    def visit_Set(self, node: ast.Set) -> None:
        """Handle set literals (e.g., {DATABASE_URL, API_KEY}).

        Args:
            node: Set node
        """
        self.generic_visit(node)

    def visit_Tuple(self, node: ast.Tuple) -> None:
        """Handle tuple literals (e.g., (DATABASE_URL, API_KEY)).

        Args:
            node: Tuple node
        """
        self.generic_visit(node)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        """Handle list comprehensions (e.g., [x for x in range(MAX_ITEMS)]).

        Args:
            node: List comprehension node
        """
        self.generic_visit(node)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        """Handle dict comprehensions (e.g., {k: VAR for k in keys}).

        Args:
            node: Dict comprehension node
        """
        self.generic_visit(node)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        """Handle set comprehensions (e.g., {VAR for _ in range(5)}).

        Args:
            node: Set comprehension node
        """
        self.generic_visit(node)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        """Handle generator expressions (e.g., (x for x in range(MAX))).

        Args:
            node: Generator expression node
        """
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        """Handle if statements (e.g., if DEBUG: ...).

        Args:
            node: If node
        """
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        """Handle while loops (e.g., while VAR: ...).

        Args:
            node: While node
        """
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        """Handle for loops (e.g., for x in VAR: ...).

        Args:
            node: For node
        """
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        """Handle async for loops.

        Args:
            node: AsyncFor node
        """
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        """Handle context managers (e.g., with DatabaseConnection(VAR): ...).

        Args:
            node: With node
        """
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        """Handle async context managers.

        Args:
            node: AsyncWith node
        """
        self.generic_visit(node)

    def visit_Match(self, node: ast.Match) -> None:
        """Handle match statements (Python 3.10+) (e.g., match VAR: ...).

        Args:
            node: Match node
        """
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        """Handle comparison operators (e.g., VAR > 10).

        Args:
            node: Compare node
        """
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        """Handle boolean operators (e.g., VAR and True).

        Args:
            node: BoolOp node
        """
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp) -> None:
        """Handle binary operators (e.g., VAR + 10, "%s" % VAR).

        Args:
            node: BinOp node
        """
        self.generic_visit(node)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> None:
        """Handle unary operators (e.g., not VAR, -VAR).

        Args:
            node: UnaryOp node
        """
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Handle attribute access (e.g., VAR.method()).

        Args:
            node: Attribute node
        """
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        """Handle subscript access (e.g., VAR[0], VAR[1:5]).

        Args:
            node: Subscript node
        """
        self.generic_visit(node)

    def visit_Starred(self, node: ast.Starred) -> None:
        """Handle starred expressions (e.g., *VAR in function calls).

        Args:
            node: Starred node
        """
        self.generic_visit(node)

    def visit_Raise(self, node: ast.Raise) -> None:
        """Handle raise statements (e.g., raise VAR).

        Args:
            node: Raise node
        """
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:
        """Handle return statements (e.g., return VAR).

        Args:
            node: Return node
        """
        self.generic_visit(node)

    def visit_Yield(self, node: ast.Yield) -> None:
        """Handle yield expressions (e.g., yield VAR).

        Args:
            node: Yield node
        """
        self.generic_visit(node)

    def visit_YieldFrom(self, node: ast.YieldFrom) -> None:
        """Handle yield from expressions (e.g., yield from VAR).

        Args:
            node: YieldFrom node
        """
        self.generic_visit(node)

    def visit_Await(self, node: ast.Await) -> None:
        """Handle await expressions (e.g., await VAR).

        Args:
            node: Await node
        """
        self.generic_visit(node)

    def _infer_context(self, node: ast.Name) -> str:
        """Infer usage context from AST structure.

        For Phase 1, this returns a generic "reference" context.
        Future enhancements could walk parent nodes for precise context.

        Args:
            node: Name node

        Returns:
            Context string (e.g., "reference", "function_arg", "fstring")
        """
        # Simplified version for Phase 1
        # TODO: Enhance with parent tracking for precise context inference
        return "reference"


class UsageAnalyzer:
    """Orchestrates usage analysis across multiple files.

    This class coordinates the two-phase analysis:
    1. Scan for declarations (using existing EnvVarScanner)
    2. Track usages of declared variables

    Attributes:
        project_root: Root directory of project to analyze
        result: Analysis result object
        exclude_patterns: File patterns to skip during analysis
    """

    def __init__(
        self,
        project_root: Path,
        exclude_patterns: Optional[List[str]] = None,
    ):
        """Initialize analyzer.

        Args:
            project_root: Root directory of project
            exclude_patterns: Optional list of glob patterns to exclude
        """
        self.project_root = project_root
        self.result = UsageAnalysisResult()

        if exclude_patterns is None:
            self.exclude_patterns = [
                "test_*",
                "tests/**/*",
                "*/tests/*",
                "*_test.py",
                "migrations/*",
                "*/migrations/*",
                ".venv/*",
                "venv/*",
                ".git/*",
                "__pycache__/*",
                "build/*",
                "dist/*",
                ".eggs/*",
                "*.egg-info/*",
            ]
        else:
            self.exclude_patterns = exclude_patterns

    def analyze(self) -> UsageAnalysisResult:
        """Run full analysis: declarations -> usages -> results.

        Returns:
            Complete usage analysis result
        """
        # Phase 1: Find all env var declarations
        self._scan_declarations()

        # Phase 2: Track usages of declared variables
        self._scan_usages()

        return self.result

    def _scan_declarations(self) -> None:
        """Phase 1: Find all env.require/optional declarations.

        Uses the existing scanner infrastructure to detect declarations.
        Extracts Python variable names from the AST context.
        """
        from tripwire.scanner import scan_directory

        # Use existing scanner to find declarations
        env_vars = scan_directory(self.project_root, exclude_patterns=self.exclude_patterns)

        # Convert to VariableDeclaration objects
        # We need to extract the Python variable name from the declaration context
        for env_var_info in env_vars:
            # The EnvVarInfo.name is the ENV_VAR name
            # We need to find the Python variable name from the declaration line
            var_name = self._extract_python_variable_name(env_var_info.file_path, env_var_info.line_number)

            if var_name:
                self.result.declarations[var_name] = VariableDeclaration(
                    name=var_name,
                    env_var=env_var_info.name,
                    file_path=env_var_info.file_path,
                    line_number=env_var_info.line_number,
                    is_required=env_var_info.required,
                    type_annotation=env_var_info.var_type,
                    validator=env_var_info.format,
                )

    def _extract_python_variable_name(self, file_path: Path, line_number: int) -> Optional[str]:
        """Extract Python variable name from declaration line.

        Parses the line to find the variable being assigned.

        Args:
            file_path: Path to source file
            line_number: Line number (1-indexed)

        Returns:
            Variable name or None if not found
        """
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
            if line_number > len(lines):
                return None

            line = lines[line_number - 1].strip()

            # Parse line to extract variable name
            # Pattern: VAR_NAME: type = env.require(...) or VAR_NAME = env.require(...)
            if "=" in line:
                left_side = line.split("=")[0].strip()

                # Handle type annotation (VAR: str = ...)
                if ":" in left_side:
                    var_name = left_side.split(":")[0].strip()
                else:
                    var_name = left_side

                # Clean up any whitespace
                var_name = var_name.strip()

                # Validate it's a valid identifier
                if var_name.isidentifier():
                    return var_name

            return None

        except (OSError, UnicodeDecodeError):
            return None

    def _scan_usages(self) -> None:
        """Phase 2: Track where declared variables are used.

        Scans all Python files, using UsageTrackingVisitor to detect
        variable references.
        """
        declared_var_names = set(self.result.declarations.keys())

        if not declared_var_names:
            # No declarations found, nothing to track
            return

        # Scan all Python files in project with directory-level filtering
        for py_file in self._iter_python_files(self.project_root):
            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(py_file))

                visitor = UsageTrackingVisitor(py_file, declared_var_names)
                visitor.visit(tree)

                # Aggregate usages
                for usage in visitor.usages:
                    var_name = usage.variable_name
                    if var_name not in self.result.usages:
                        self.result.usages[var_name] = []
                    self.result.usages[var_name].append(usage)

            except (SyntaxError, UnicodeDecodeError):
                # Skip files with syntax errors or encoding issues
                continue

    def _iter_python_files(self, root: Path) -> Iterator[Path]:
        """Recursively iterate Python files with directory-level filtering.

        This method skips entire directories (like .venv/, __pycache__/)
        instead of checking every file individually, dramatically improving
        performance on large codebases.

        Args:
            root: Root directory to search

        Yields:
            Path objects for Python files that pass filtering
        """
        # File extensions to skip
        SKIP_EXTENSIONS = {".pyc", ".pyo", ".pyd", ".so", ".dll"}

        def should_skip_dir(dir_path: Path) -> bool:
            """Check if directory should be skipped entirely."""
            dir_name = dir_path.name

            # Skip known directories
            if dir_name in SKIP_DIRS:
                return True

            # Skip hidden directories (except project root)
            if dir_name.startswith(".") and dir_path != root:
                return True

            # Skip egg-info directories
            if dir_name.endswith(".egg-info"):
                return True

            return False

        def walk_python_files(directory: Path) -> Iterator[Path]:
            """Recursively walk directory tree, skipping unwanted dirs."""
            try:
                for item in directory.iterdir():
                    # Skip if not accessible
                    if not item.exists():
                        continue

                    if item.is_dir():
                        # Directory-level filtering - skip entire trees
                        if should_skip_dir(item):
                            continue
                        # Recurse into allowed directories
                        yield from walk_python_files(item)

                    elif item.is_file():
                        # File-level filtering
                        if item.suffix not in SKIP_EXTENSIONS and item.suffix == ".py":
                            if not self._should_skip_file(item):
                                yield item

            except PermissionError:
                # Skip directories we can't access
                pass

        yield from walk_python_files(root)

    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped during analysis.

        Args:
            file_path: Path to check

        Returns:
            True if file should be skipped
        """
        try:
            relative_path = file_path.relative_to(self.project_root)
        except ValueError:
            # File is outside project root
            return True

        # Check against exclude patterns
        for pattern in self.exclude_patterns:
            if relative_path.match(pattern):
                return True

        # Check file name patterns
        file_name = file_path.name
        if file_name.startswith("test_") or file_name.endswith("_test.py"):
            return True

        return False

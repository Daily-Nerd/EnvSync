"""Comprehensive test suite for usage tracking functionality.

Tests cover 30+ edge cases including:
- Declaration detection
- Basic usage patterns (function args, print, return, assignment)
- String interpolation (f-strings, .format(), % formatting)
- Collections (dict, list, set, tuple literals)
- Comprehensions (list, dict, set, generator)
- Control flow (if, while, for, match)
- Cross-file tracking
- Dead code detection
"""

from pathlib import Path

import pytest

from tripwire.analysis.models import UsageAnalysisResult
from tripwire.analysis.usage_tracker import UsageAnalyzer, UsageTrackingVisitor

# Declaration Detection Tests


def test_detects_env_require_declaration(tmp_path):
    """Should detect env.require() declarations."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
DATABASE_URL: str = env.require("DATABASE_URL")
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert "DATABASE_URL" in result.declarations
    assert result.declarations["DATABASE_URL"].is_required is True
    assert result.declarations["DATABASE_URL"].env_var == "DATABASE_URL"


def test_detects_env_optional_declaration(tmp_path):
    """Should detect env.optional() declarations."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
DEBUG: bool = env.optional("DEBUG", default=False)
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert "DEBUG" in result.declarations
    assert result.declarations["DEBUG"].is_required is False


def test_ignores_declaration_as_usage(tmp_path):
    """Declaration line should NOT count as usage."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
UNUSED_VAR: str = env.require("UNUSED_VAR")
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert "UNUSED_VAR" in result.declarations
    assert "UNUSED_VAR" not in result.usages
    assert "UNUSED_VAR" in result.dead_variables


def test_detects_non_annotated_declaration(tmp_path):
    """Should detect declarations without type annotations."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
API_KEY = env.require("API_KEY")
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert "API_KEY" in result.declarations


# Basic Usage Pattern Tests


def test_detects_function_argument_usage(tmp_path):
    """Variable passed to function should be detected."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
DATABASE_URL: str = env.require("DATABASE_URL")
"""
    )

    app_file = tmp_path / "app.py"
    app_file.write_text(
        """
from config import DATABASE_URL
import sqlalchemy

engine = sqlalchemy.create_engine(DATABASE_URL)
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert "DATABASE_URL" in result.declarations
    assert "DATABASE_URL" in result.usages
    assert len(result.usages["DATABASE_URL"]) == 1
    assert result.usages["DATABASE_URL"][0].file_path.name == "app.py"


def test_detects_print_usage(tmp_path):
    """Variable in print() should be detected."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
SECRET_KEY: str = env.require("SECRET_KEY")
"""
    )

    app_file = tmp_path / "app.py"
    app_file.write_text(
        """
from config import SECRET_KEY
print(SECRET_KEY)
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert len(result.usages["SECRET_KEY"]) == 1


def test_detects_return_usage(tmp_path):
    """Variable in return statement should be detected."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
API_URL: str = env.require("API_URL")
"""
    )

    app_file = tmp_path / "app.py"
    app_file.write_text(
        """
from config import API_URL

def get_api_url():
    return API_URL
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert len(result.usages["API_URL"]) == 1


def test_detects_assignment_usage(tmp_path):
    """Variable in assignment should be detected."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
PORT: int = env.require("PORT")
"""
    )

    app_file = tmp_path / "app.py"
    app_file.write_text(
        """
from config import PORT
server_port = PORT
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert len(result.usages["PORT"]) == 1


# String Interpolation Tests


def test_detects_fstring_usage(tmp_path):
    """Variable in f-string should be detected."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
API_URL: str = env.require("API_URL")
"""
    )

    app_file = tmp_path / "app.py"
    app_file.write_text(
        """
from config import API_URL

endpoint = f"{API_URL}/users"
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert len(result.usages["API_URL"]) == 1


def test_detects_str_format_usage(tmp_path):
    """Variable in str.format() should be detected."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
BASE_URL: str = env.require("BASE_URL")
"""
    )

    app_file = tmp_path / "app.py"
    app_file.write_text(
        """
from config import BASE_URL

url = "{}/api".format(BASE_URL)
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert len(result.usages["BASE_URL"]) == 1


def test_detects_percent_formatting_usage(tmp_path):
    """Variable in % formatting should be detected."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
HOST: str = env.require("HOST")
"""
    )

    app_file = tmp_path / "app.py"
    app_file.write_text(
        """
from config import HOST

url = "%s/api" % HOST
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert len(result.usages["HOST"]) == 1


# Collection Tests


def test_detects_dict_literal_usage(tmp_path):
    """Variable in dict literal should be detected."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
DATABASE_URL: str = env.require("DATABASE_URL")
"""
    )

    app_file = tmp_path / "app.py"
    app_file.write_text(
        """
from config import DATABASE_URL

config = {"database": DATABASE_URL}
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert len(result.usages["DATABASE_URL"]) == 1


def test_detects_list_literal_usage(tmp_path):
    """Variable in list literal should be detected."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
API_KEY: str = env.require("API_KEY")
"""
    )

    app_file = tmp_path / "app.py"
    app_file.write_text(
        """
from config import API_KEY

keys = [API_KEY, "other_key"]
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert len(result.usages["API_KEY"]) == 1


def test_detects_tuple_literal_usage(tmp_path):
    """Variable in tuple literal should be detected."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
HOST: str = env.require("HOST")
PORT: int = env.require("PORT")
"""
    )

    app_file = tmp_path / "app.py"
    app_file.write_text(
        """
from config import HOST, PORT

server = (HOST, PORT)
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert len(result.usages["HOST"]) == 1
    assert len(result.usages["PORT"]) == 1


def test_detects_set_literal_usage(tmp_path):
    """Variable in set literal should be detected."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
ADMIN_EMAIL: str = env.require("ADMIN_EMAIL")
"""
    )

    app_file = tmp_path / "app.py"
    app_file.write_text(
        """
from config import ADMIN_EMAIL

admins = {ADMIN_EMAIL, "other@example.com"}
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert len(result.usages["ADMIN_EMAIL"]) == 1


# Comprehension Tests


def test_detects_list_comprehension_usage(tmp_path):
    """Variable in list comprehension should be detected."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
MAX_ITEMS: int = env.require("MAX_ITEMS")
"""
    )

    app_file = tmp_path / "app.py"
    app_file.write_text(
        """
from config import MAX_ITEMS

items = [x for x in range(MAX_ITEMS)]
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert len(result.usages["MAX_ITEMS"]) == 1


def test_detects_dict_comprehension_usage(tmp_path):
    """Variable in dict comprehension should be detected."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
DEFAULT_VALUE: str = env.require("DEFAULT_VALUE")
"""
    )

    app_file = tmp_path / "app.py"
    app_file.write_text(
        """
from config import DEFAULT_VALUE

data = {k: DEFAULT_VALUE for k in ["a", "b", "c"]}
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert len(result.usages["DEFAULT_VALUE"]) == 1


def test_detects_set_comprehension_usage(tmp_path):
    """Variable in set comprehension should be detected."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
MAGIC_NUMBER: int = env.require("MAGIC_NUMBER")
"""
    )

    app_file = tmp_path / "app.py"
    app_file.write_text(
        """
from config import MAGIC_NUMBER

numbers = {x + MAGIC_NUMBER for x in range(10)}
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert len(result.usages["MAGIC_NUMBER"]) == 1


def test_detects_generator_expression_usage(tmp_path):
    """Variable in generator expression should be detected."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
MULTIPLIER: int = env.require("MULTIPLIER")
"""
    )

    app_file = tmp_path / "app.py"
    app_file.write_text(
        """
from config import MULTIPLIER

gen = (x * MULTIPLIER for x in range(10))
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert len(result.usages["MULTIPLIER"]) == 1


# Control Flow Tests


def test_detects_conditional_usage(tmp_path):
    """Variable used in conditional should be detected."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
DEBUG: bool = env.require("DEBUG")
"""
    )

    app_file = tmp_path / "app.py"
    app_file.write_text(
        """
from config import DEBUG

if DEBUG:
    print("Debug mode")
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert len(result.usages["DEBUG"]) >= 1


def test_detects_while_loop_usage(tmp_path):
    """Variable in while condition should be detected."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
RETRY_ENABLED: bool = env.require("RETRY_ENABLED")
"""
    )

    app_file = tmp_path / "app.py"
    app_file.write_text(
        """
from config import RETRY_ENABLED

while RETRY_ENABLED:
    break
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert len(result.usages["RETRY_ENABLED"]) >= 1


def test_detects_for_loop_usage(tmp_path):
    """Variable in for loop iterator should be detected."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
ITEMS: list = env.require("ITEMS")
"""
    )

    app_file = tmp_path / "app.py"
    app_file.write_text(
        """
from config import ITEMS

for item in ITEMS:
    print(item)
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert len(result.usages["ITEMS"]) >= 1


# Advanced Pattern Tests


def test_detects_decorator_usage(tmp_path):
    """Variable in decorator should be detected."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
CACHE_TTL: int = env.require("CACHE_TTL")
"""
    )

    app_file = tmp_path / "app.py"
    app_file.write_text(
        """
from config import CACHE_TTL

@cache(timeout=CACHE_TTL)
def expensive_function():
    pass
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert len(result.usages["CACHE_TTL"]) >= 1


def test_detects_context_manager_usage(tmp_path):
    """Variable in context manager should be detected."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
DATABASE_URL: str = env.require("DATABASE_URL")
"""
    )

    app_file = tmp_path / "app.py"
    app_file.write_text(
        """
from config import DATABASE_URL

with DatabaseConnection(DATABASE_URL) as conn:
    pass
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert len(result.usages["DATABASE_URL"]) >= 1


def test_detects_attribute_access_usage(tmp_path):
    """Variable with attribute access should be detected."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
CONFIG_OBJ: object = env.require("CONFIG_OBJ")
"""
    )

    app_file = tmp_path / "app.py"
    app_file.write_text(
        """
from config import CONFIG_OBJ

value = CONFIG_OBJ.property
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert len(result.usages["CONFIG_OBJ"]) >= 1


def test_detects_subscript_usage(tmp_path):
    """Variable with subscript access should be detected."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
DATA: list = env.require("DATA")
"""
    )

    app_file = tmp_path / "app.py"
    app_file.write_text(
        """
from config import DATA

first = DATA[0]
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert len(result.usages["DATA"]) >= 1


def test_detects_comparison_usage(tmp_path):
    """Variable in comparison should be detected."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
MAX_SIZE: int = env.require("MAX_SIZE")
"""
    )

    app_file = tmp_path / "app.py"
    app_file.write_text(
        """
from config import MAX_SIZE

if size > MAX_SIZE:
    pass
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert len(result.usages["MAX_SIZE"]) >= 1


def test_detects_boolean_operation_usage(tmp_path):
    """Variable in boolean operation should be detected."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
ENABLED: bool = env.require("ENABLED")
"""
    )

    app_file = tmp_path / "app.py"
    app_file.write_text(
        """
from config import ENABLED

if ENABLED and True:
    pass
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert len(result.usages["ENABLED"]) >= 1


# Cross-File Tracking Tests


def test_tracks_usage_across_multiple_files(tmp_path):
    """Should track usages across different files."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
SECRET_KEY: str = env.require("SECRET_KEY")
"""
    )

    auth_file = tmp_path / "auth.py"
    auth_file.write_text(
        """
from config import SECRET_KEY
token = encode(SECRET_KEY)
"""
    )

    middleware_file = tmp_path / "middleware.py"
    middleware_file.write_text(
        """
from config import SECRET_KEY
validate(SECRET_KEY)
"""
    )

    tasks_file = tmp_path / "tasks.py"
    tasks_file.write_text(
        """
from config import SECRET_KEY
sign(SECRET_KEY)
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert len(result.usages["SECRET_KEY"]) == 3
    file_names = {u.file_path.name for u in result.usages["SECRET_KEY"]}
    assert file_names == {"auth.py", "middleware.py", "tasks.py"}


def test_counts_usage_frequency(tmp_path):
    """Should count multiple usages in same file."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
API_KEY: str = env.require("API_KEY")
"""
    )

    app_file = tmp_path / "app.py"
    app_file.write_text(
        """
from config import API_KEY

client1 = connect(API_KEY)
client2 = authenticate(API_KEY)
client3 = verify(API_KEY)
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert len(result.usages["API_KEY"]) == 3


# Dead Code Detection Tests


def test_identifies_dead_variable(tmp_path):
    """Should identify variable declared but never used."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
DEAD_VAR: str = env.require("DEAD_VAR")
USED_VAR: str = env.require("USED_VAR")
"""
    )

    app_file = tmp_path / "app.py"
    app_file.write_text(
        """
from config import USED_VAR

print(USED_VAR)
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert "DEAD_VAR" in result.dead_variables
    assert "USED_VAR" not in result.dead_variables


def test_no_false_positives_for_used_variable(tmp_path):
    """Should not mark used variables as dead."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
ACTIVE_VAR: str = env.require("ACTIVE_VAR")
"""
    )

    app_file = tmp_path / "app.py"
    app_file.write_text(
        """
from config import ACTIVE_VAR

result = process(ACTIVE_VAR)
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert "ACTIVE_VAR" not in result.dead_variables
    assert "ACTIVE_VAR" in result.used_variables


# File Filtering Tests


def test_skips_test_files(tmp_path):
    """Should skip test files during analysis."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
TEST_VAR: str = env.require("TEST_VAR")
"""
    )

    test_file = tmp_path / "test_app.py"
    test_file.write_text(
        """
from config import TEST_VAR

def test_something():
    assert TEST_VAR
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    # Usage in test file should be ignored
    assert "TEST_VAR" in result.declarations
    # If usages dict doesn't have TEST_VAR or has 0 usages, it's dead
    usage_count = len(result.usages.get("TEST_VAR", []))
    assert usage_count == 0


def test_skips_migration_files(tmp_path):
    """Should skip migration files during analysis."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
DB_VAR: str = env.require("DB_VAR")
"""
    )

    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()

    migration_file = migrations_dir / "0001_initial.py"
    migration_file.write_text(
        """
from config import DB_VAR

# Migration code using DB_VAR
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    # Usage in migration should be ignored
    usage_count = len(result.usages.get("DB_VAR", []))
    assert usage_count == 0


# Edge Case: Multiple Variables in One File


def test_tracks_multiple_variables(tmp_path):
    """Should track multiple variables declared in same file."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
VAR1: str = env.require("VAR1")
VAR2: str = env.require("VAR2")
VAR3: str = env.require("VAR3")
"""
    )

    app_file = tmp_path / "app.py"
    app_file.write_text(
        """
from config import VAR1, VAR2

print(VAR1)
print(VAR2)
# VAR3 is not used
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert len(result.declarations) == 3
    assert "VAR1" in result.used_variables
    assert "VAR2" in result.used_variables
    assert "VAR3" in result.dead_variables


# Edge Case: Import-Time Usage


def test_detects_import_time_usage(tmp_path):
    """Should detect usage at module import time."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
INIT_VAR: str = env.require("INIT_VAR")
"""
    )

    app_file = tmp_path / "app.py"
    app_file.write_text(
        """
from config import INIT_VAR

# Used at import time
app = create_app(INIT_VAR)
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert "INIT_VAR" in result.used_variables


# Result Property Tests


def test_coverage_percentage_calculation(tmp_path):
    """Should correctly calculate coverage percentage."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
USED1: str = env.require("USED1")
USED2: str = env.require("USED2")
DEAD1: str = env.require("DEAD1")
DEAD2: str = env.require("DEAD2")
"""
    )

    app_file = tmp_path / "app.py"
    app_file.write_text(
        """
from config import USED1, USED2

print(USED1)
print(USED2)
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert result.total_variables == 4
    assert len(result.used_variables) == 2
    assert len(result.dead_variables) == 2
    assert result.coverage_percentage == 50.0


def test_get_usage_count(tmp_path):
    """Should correctly count usages per variable."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
POPULAR_VAR: str = env.require("POPULAR_VAR")
"""
    )

    app_file = tmp_path / "app.py"
    app_file.write_text(
        """
from config import POPULAR_VAR

a = POPULAR_VAR
b = POPULAR_VAR
c = POPULAR_VAR
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    assert result.get_usage_count("POPULAR_VAR") == 3
    assert result.get_usage_count("NONEXISTENT") == 0


def test_get_usage_files(tmp_path):
    """Should return unique files where variable is used."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from tripwire import env
SHARED_VAR: str = env.require("SHARED_VAR")
"""
    )

    app_file = tmp_path / "app.py"
    app_file.write_text(
        """
from config import SHARED_VAR

print(SHARED_VAR)
print(SHARED_VAR)  # Used twice in same file
"""
    )

    api_file = tmp_path / "api.py"
    api_file.write_text(
        """
from config import SHARED_VAR

send(SHARED_VAR)
"""
    )

    analyzer = UsageAnalyzer(tmp_path)
    result = analyzer.analyze()

    usage_files = result.get_usage_files("SHARED_VAR")
    assert len(usage_files) == 2
    file_names = {f.name for f in usage_files}
    assert file_names == {"app.py", "api.py"}

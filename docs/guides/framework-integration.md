[Home](../README.md) / [Guides](README.md) / Framework Integration

# Framework Integration Guide

Learn how to integrate TripWire with popular Python frameworks.

---

## Table of Contents

- [FastAPI](#fastapi)
- [Django](#django)
- [Flask](#flask)
- [Starlette](#starlette)
- [Quart](#quart)
- [Best Practices](#best-practices)

---

## FastAPI

### Basic Setup

```python
# config.py
from tripwire import env

# Database
DATABASE_URL: str = env.require("DATABASE_URL", format="postgresql", secret=True)
REDIS_URL: str = env.optional("REDIS_URL", default="redis://localhost:6379")

# Security
SECRET_KEY: str = env.require("SECRET_KEY", secret=True, min_length=32)
ALGORITHM: str = env.optional("ALGORITHM", default="HS256")

# Application
DEBUG: bool = env.optional("DEBUG", default=False)
HOST: str = env.optional("HOST", default="0.0.0.0")
PORT: int = env.optional("PORT", default=8000, min_val=1024, max_val=65535)

# API Keys
OPENAI_API_KEY: str = env.require("OPENAI_API_KEY", secret=True)
```

```python
# main.py
from fastapi import FastAPI
from config import DATABASE_URL, SECRET_KEY, DEBUG, HOST, PORT

app = FastAPI(debug=DEBUG)

@app.on_event("startup")
async def startup():
    # Config already validated at import time
    print(f"Connecting to database: {DATABASE_URL[:20]}...")
    print(f"Server starting on {HOST}:{PORT}")

@app.get("/")
async def root():
    return {"message": "TripWire + FastAPI"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
```

### With Pydantic Settings

Combine TripWire validation with Pydantic:

```python
# config.py
from pydantic import BaseSettings
from tripwire import env

# Validate critical variables with TripWire first
DATABASE_URL: str = env.require("DATABASE_URL", format="postgresql")
SECRET_KEY: str = env.require("SECRET_KEY", min_length=32)

class Settings(BaseSettings):
    # Already validated by TripWire
    database_url: str = DATABASE_URL
    secret_key: str = SECRET_KEY

    # Pydantic handles these
    allowed_hosts: list[str] = []
    cors_origins: list[str] = []

    class Config:
        env_file = ".env"

settings = Settings()
```

### Dependency Injection

```python
from fastapi import Depends
from config import OPENAI_API_KEY

async def get_openai_client():
    from openai import AsyncOpenAI
    return AsyncOpenAI(api_key=OPENAI_API_KEY)

@app.get("/completion")
async def get_completion(client = Depends(get_openai_client)):
    response = await client.chat.completions.create(...)
    return response
```

---

## Django

### Settings Configuration

Replace `os.getenv()` with `env.require()` / `env.optional()`:

```python
# settings.py
from tripwire import env
from pathlib import Path

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Security
SECRET_KEY: str = env.require("DJANGO_SECRET_KEY", secret=True, min_length=50)
DEBUG: bool = env.optional("DEBUG", default=False)
ALLOWED_HOSTS: list = env.optional("ALLOWED_HOSTS", default=["localhost"], type=list)

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env.require("DB_NAME"),
        'USER': env.require("DB_USER"),
        'PASSWORD': env.require("DB_PASSWORD", secret=True),
        'HOST': env.optional("DB_HOST", default="localhost"),
        'PORT': env.optional("DB_PORT", default=5432, type=int),
    }
}

# Cache
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': env.optional("REDIS_URL", default="redis://localhost:6379/0"),
    }
}

# Email
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST: str = env.optional("EMAIL_HOST", default="localhost")
EMAIL_PORT: int = env.optional("EMAIL_PORT", default=587, type=int)
EMAIL_USE_TLS: bool = env.optional("EMAIL_USE_TLS", default=True, type=bool)
EMAIL_HOST_USER: str = env.optional("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD: str = env.optional("EMAIL_HOST_PASSWORD", default="", secret=True)

# AWS S3
AWS_ACCESS_KEY_ID: str = env.optional("AWS_ACCESS_KEY_ID", default="", secret=True)
AWS_SECRET_ACCESS_KEY: str = env.optional("AWS_SECRET_ACCESS_KEY", default="", secret=True)
AWS_STORAGE_BUCKET_NAME: str = env.optional("AWS_STORAGE_BUCKET_NAME", default="")
```

### Django-Environ Migration

Replace `django-environ` with TripWire:

**Before (django-environ):**
```python
import environ

env = environ.Env(
    DEBUG=(bool, False)
)
environ.Env.read_env()

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
DATABASE_URL = env('DATABASE_URL')
```

**After (TripWire):**
```python
from tripwire import env

SECRET_KEY: str = env.require('DJANGO_SECRET_KEY', secret=True)
DEBUG: bool = env.optional('DEBUG', default=False)
DATABASE_URL: str = env.require('DATABASE_URL', format='postgresql')
```

### Management Commands

```python
# management/commands/check_env.py
from django.core.management.base import BaseCommand
from tripwire import env

class Command(BaseCommand):
    help = 'Validate environment configuration'

    def handle(self, *args, **options):
        try:
            # Trigger validation
            from django.conf import settings
            self.stdout.write(self.style.SUCCESS('✓ All environment variables valid'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Validation failed: {e}'))
```

---

## Flask

### Application Factory Pattern

```python
# config.py
from tripwire import env

class Config:
    """Base configuration."""
    # Already validated by TripWire at import time
    SECRET_KEY: str = env.require("SECRET_KEY", secret=True, min_length=32)
    DEBUG: bool = env.optional("DEBUG", default=False)

    # Database
    SQLALCHEMY_DATABASE_URI: str = env.require("DATABASE_URL", format="postgresql")
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # Redis
    REDIS_URL: str = env.optional("REDIS_URL", default="redis://localhost:6379/0")

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False

class TestConfig(Config):
    """Test configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
```

```python
# app.py
from flask import Flask
from config import DevelopmentConfig, ProductionConfig
import os

def create_app(config_name=None):
    """Application factory."""
    app = Flask(__name__)

    # Load config
    if config_name == 'production':
        app.config.from_object(ProductionConfig)
    else:
        app.config.from_object(DevelopmentConfig)

    # Initialize extensions
    from extensions import db, redis_client
    db.init_app(app)
    redis_client.init_app(app)

    # Register blueprints
    from routes import main_bp
    app.register_blueprint(main_bp)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run()
```

### Flask-SQLAlchemy Integration

```python
# extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_redis import FlaskRedis

db = SQLAlchemy()
redis_client = FlaskRedis()
```

```python
# models.py
from extensions import db
from datetime import datetime

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

---

## Starlette

```python
# config.py
from tripwire import env

DATABASE_URL: str = env.require("DATABASE_URL", format="postgresql")
SECRET_KEY: str = env.require("SECRET_KEY", secret=True)
DEBUG: bool = env.optional("DEBUG", default=False)
```

```python
# app.py
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse
from config import DATABASE_URL, DEBUG

async def homepage(request):
    return JSONResponse({'message': 'TripWire + Starlette'})

app = Starlette(
    debug=DEBUG,
    routes=[
        Route('/', homepage),
    ]
)
```

---

## Quart

Async Flask alternative:

```python
# config.py
from tripwire import env

SECRET_KEY: str = env.require("SECRET_KEY", secret=True)
DATABASE_URL: str = env.require("DATABASE_URL", format="postgresql")
REDIS_URL: str = env.optional("REDIS_URL", default="redis://localhost:6379/0")
```

```python
# app.py
from quart import Quart
from config import SECRET_KEY, DATABASE_URL

app = Quart(__name__)
app.config['SECRET_KEY'] = SECRET_KEY

@app.before_serving
async def startup():
    print(f"Connecting to {DATABASE_URL[:20]}...")

@app.route('/')
async def index():
    return {'message': 'TripWire + Quart'}

if __name__ == '__main__':
    app.run()
```

---

## Best Practices

### 1. Module-Level Validation

**✅ DO:** Validate at module level (import time)
```python
# config.py
from tripwire import env

DATABASE_URL: str = env.require("DATABASE_URL")  # Fails at import
```

**❌ DON'T:** Validate at function level
```python
# config.py
def get_database_url():
    from tripwire import env
    return env.require("DATABASE_URL")  # Fails at runtime
```

### 2. Centralize Configuration

**✅ DO:** Single config module
```python
# config.py - single source of truth
from tripwire import env

DATABASE_URL: str = env.require("DATABASE_URL")
SECRET_KEY: str = env.require("SECRET_KEY")
```

```python
# app.py
from config import DATABASE_URL, SECRET_KEY
```

**❌ DON'T:** Scatter env vars across files
```python
# models.py
from tripwire import env
db_url = env.require("DATABASE_URL")

# views.py
from tripwire import env
db_url = env.require("DATABASE_URL")  # Duplicate
```

### 3. Type Annotations

**✅ DO:** Use type annotations for inference
```python
PORT: int = env.require("PORT", min_val=1024)  # Type inferred
```

**❌ DON'T:** Omit annotations
```python
PORT = env.require("PORT", type=int)  # Works but verbose
```

### 4. Mark Secrets

**✅ DO:** Mark sensitive variables
```python
API_KEY: str = env.require("API_KEY", secret=True)
PASSWORD: str = env.require("PASSWORD", secret=True)
```

**❌ DON'T:** Leave secrets unmarked
```python
API_KEY: str = env.require("API_KEY")  # Will appear in logs
```

### 5. Environment-Specific Configs

**✅ DO:** Use environment-specific files
```python
# config.py
from tripwire import env
import os

# Load base config
env.load(".env")

# Load environment-specific overrides
environment = os.getenv("ENVIRONMENT", "development")
env.load(f".env.{environment}", override=True)
```

**File structure:**
```
.env                    # Base (committed)
.env.development        # Dev overrides (committed)
.env.production         # Prod (gitignored)
.env.local              # Local overrides (gitignored)
```

### 6. CI/CD Validation

Add to CI pipeline:

```yaml
# .github/workflows/test.yml
- name: Validate environment
  run: |
    tripwire generate --check
    tripwire scan --strict
```

---

## Common Patterns

### Database Connection Pooling

```python
from tripwire import env
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

DATABASE_URL: str = env.require("DATABASE_URL", format="postgresql")
DB_POOL_SIZE: int = env.optional("DB_POOL_SIZE", default=5, min_val=1, max_val=50)
DB_MAX_OVERFLOW: int = env.optional("DB_MAX_OVERFLOW", default=10, min_val=0)

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW
)
```

### Feature Flags

```python
from tripwire import env

# Feature flags as dict
FEATURE_FLAGS: dict = env.optional(
    "FEATURE_FLAGS",
    default={"new_ui": False, "beta_api": False},
    type=dict
)

# Or individual flags
ENABLE_NEW_UI: bool = env.optional("ENABLE_NEW_UI", default=False, type=bool)
ENABLE_BETA_API: bool = env.optional("ENABLE_BETA_API", default=False, type=bool)
```

### API Rate Limiting

```python
from tripwire import env

RATE_LIMIT_ENABLED: bool = env.optional("RATE_LIMIT_ENABLED", default=True)
RATE_LIMIT_PER_HOUR: int = env.optional(
    "RATE_LIMIT_PER_HOUR",
    default=1000,
    min_val=1,
    max_val=100000
)
```

---

## Framework-Specific Tips

### FastAPI
- Use TripWire for critical config validation
- Pydantic Settings for complex nested configs
- Dependency injection for service configs

### Django
- Replace all `os.getenv()` with TripWire
- Validate in `settings.py` (imported by all apps)
- Use management commands to test validation

### Flask
- Validate in `Config` class
- Use application factory pattern
- Load environment-specific configs

---

## Migration Guides

### From python-decouple

**Before:**
```python
from decouple import config

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
```

**After:**
```python
from tripwire import env

SECRET_KEY: str = env.require('SECRET_KEY', secret=True)
DEBUG: bool = env.optional('DEBUG', default=False)
```

### From python-dotenv

**Before:**
```python
from dotenv import load_dotenv
import os

load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG') == 'true'
```

**After:**
```python
from tripwire import env

SECRET_KEY: str = env.require('SECRET_KEY', secret=True)
DEBUG: bool = env.optional('DEBUG', default=False)
```

---

**[Back to Guides](README.md)**

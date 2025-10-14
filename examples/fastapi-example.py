from fastapi import FastAPI

from tripwire import env

# Validation happens HERE at import time - app won't start if invalid
DATABASE_URL: str = env.require("DATABASE_URL", format="postgresql")
PORT: int = env.require("PORT", min_val=1, max_val=65535)
SECRET_KEY: str = env.require("SECRET_KEY", min_length=32, secret=True)
DEBUG: bool = env.optional("DEBUG", default=False)

app = FastAPI(debug=DEBUG)


@app.on_event("startup")
async def startup():
    # By this point, we KNOW config is valid
    print(f"Connecting to {DATABASE_URL[:20]}...")

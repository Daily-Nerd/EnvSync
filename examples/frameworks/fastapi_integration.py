"""Example: FastAPI integration

This example demonstrates how to integrate TripWire with a FastAPI application
for robust configuration management.

README Reference: Framework Integration section

Expected behavior:
- Configuration validated at application startup (before accepting requests)
- FastAPI won't start if configuration is invalid
- Type-safe configuration with IDE autocomplete

Run this example:
    export DATABASE_URL="postgresql://localhost/mydb"
    export API_KEY="your_api_key"
    export DEBUG="false"
    export PORT="8000"
    python examples/frameworks/fastapi_integration.py

Or use demo mode:
    python examples/frameworks/fastapi_integration.py --demo

Requirements:
    pip install fastapi uvicorn
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Set demo mode BEFORE importing TripWire if --demo flag is present
if "--demo" in sys.argv:
    os.environ["DATABASE_URL"] = "postgresql://localhost/demo_db"
    os.environ["API_KEY"] = "demo_api_key_12345"
    os.environ["DEBUG"] = "true"
    os.environ["PORT"] = "8000"
    print("Running in DEMO mode with mock environment variables\n")

from tripwire import TripWire

# Initialize configuration at module level (before FastAPI app)
# This ensures validation happens at import time
# Use fail-fast mode to prevent app from starting with invalid config
env = TripWire(collect_errors=False)

# All configuration validated before FastAPI app starts
DATABASE_URL: str = env.require("DATABASE_URL", format="postgresql")
API_KEY: str = env.require("API_KEY", min_length=10)
DEBUG: bool = env.optional("DEBUG", default=False)
PORT: int = env.optional("PORT", default=8000, min_val=1, max_val=65535)

try:
    import uvicorn
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse

    # Create FastAPI app - only reaches here if config is valid!
    app = FastAPI(title="TripWire + FastAPI Example", debug=DEBUG)

    @app.get("/")
    async def root():
        """Root endpoint showing configuration status."""
        return {
            "message": "TripWire + FastAPI Integration",
            "database": "connected" if DATABASE_URL else "not configured",
            "debug_mode": DEBUG,
            "validation": "passed",
        }

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "healthy", "config_validated": True}

    @app.get("/config")
    async def config_info():
        """Show configuration info (without sensitive data)."""
        return {
            "database_configured": bool(DATABASE_URL),
            "api_key_configured": bool(API_KEY),
            "debug": DEBUG,
            "port": PORT,
        }

    def main():
        """Run the FastAPI application."""
        print("✅ Configuration validated successfully!")
        print(f"   DATABASE_URL: {DATABASE_URL[:20]}...")
        print(f"   API_KEY: {API_KEY[:10]}...")
        print(f"   DEBUG: {DEBUG}")
        print(f"   PORT: {PORT}")
        print(f"\n🚀 Starting FastAPI server on http://localhost:{PORT}")
        print("   Try: curl http://localhost:8000/")
        print("   Try: curl http://localhost:8000/health")
        print("   Try: curl http://localhost:8000/config")

        uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")  # nosec B104 - Demo server only

except ImportError:

    def main():
        """Fallback if FastAPI not installed."""
        print("✅ Configuration validated successfully!")
        print(f"   DATABASE_URL: {DATABASE_URL}")
        print(f"   API_KEY: {API_KEY}")
        print(f"   DEBUG: {DEBUG}")
        print(f"   PORT: {PORT}")
        print("\n💡 To run the FastAPI server:")
        print("   pip install fastapi uvicorn")
        print("   python examples/frameworks/fastapi_integration.py")


if __name__ == "__main__":
    main()

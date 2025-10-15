"""Example: Flask integration

This example demonstrates how to integrate TripWire with a Flask application
for type-safe configuration management.

README Reference: Framework Integration section

Expected behavior:
- Configuration validated before Flask app initialization
- App won't start if configuration is invalid
- Clean separation of concerns

Run this example:
    export SECRET_KEY="your-secret-key-here"
    export DATABASE_URL="postgresql://localhost/mydb"
    export DEBUG="false"
    python examples/frameworks/flask_integration.py

Or use demo mode:
    python examples/frameworks/flask_integration.py --demo

Requirements:
    pip install flask
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Set demo mode BEFORE importing TripWire if --demo flag is present
if "--demo" in sys.argv:
    os.environ["SECRET_KEY"] = "demo-secret-key-1234567890"  # nosec B105 - Demo value only
    os.environ["DATABASE_URL"] = "postgresql://localhost/demo_db"
    os.environ["DEBUG"] = "true"
    os.environ["PORT"] = "5000"
    print("Running in DEMO mode with mock environment variables\n")

from tripwire import TripWire

# Load and validate configuration at module level
# Use fail-fast mode to prevent app from starting with invalid config
env = TripWire(collect_errors=False)

SECRET_KEY: str = env.require("SECRET_KEY", min_length=16)
DATABASE_URL: str = env.require("DATABASE_URL")
DEBUG: bool = env.optional("DEBUG", default=False)
PORT: int = env.optional("PORT", default=5000, min_val=1, max_val=65535)

try:
    from flask import Flask, jsonify

    # Create Flask app - only if config is valid
    app = Flask(__name__)

    # Configure Flask with validated environment variables
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    app.config["DEBUG"] = DEBUG

    @app.route("/")
    def index():
        """Root endpoint."""
        return jsonify({"message": "TripWire + Flask Integration", "framework": "Flask", "validation": "passed"})

    @app.route("/health")
    def health():
        """Health check endpoint."""
        return jsonify({"status": "healthy", "config_validated": True})

    @app.route("/config")
    def config_info():
        """Show configuration info (without secrets)."""
        return jsonify(
            {
                "database_configured": bool(DATABASE_URL),
                "secret_key_configured": bool(SECRET_KEY),
                "debug": DEBUG,
                "port": PORT,
            }
        )

    def main():
        """Run the Flask application."""
        print("✅ Configuration validated successfully!")
        print(f"   SECRET_KEY: {SECRET_KEY[:10]}...")
        print(f"   DATABASE_URL: {DATABASE_URL[:20]}...")
        print(f"   DEBUG: {DEBUG}")
        print(f"   PORT: {PORT}")
        print(f"\n🚀 Starting Flask server on http://localhost:{PORT}")
        print("   Try: curl http://localhost:5000/")
        print("   Try: curl http://localhost:5000/health")

        app.run(host="0.0.0.0", port=PORT, debug=DEBUG)  # nosec B104 - Demo server only

except ImportError:

    def main():
        """Fallback if Flask not installed."""
        print("✅ Configuration validated successfully!")
        print(f"   SECRET_KEY: {SECRET_KEY[:10]}...")
        print(f"   DATABASE_URL: {DATABASE_URL}")
        print(f"   DEBUG: {DEBUG}")
        print(f"   PORT: {PORT}")
        print("\n💡 To run the Flask server:")
        print("   pip install flask")
        print("   python examples/frameworks/flask_integration.py")


if __name__ == "__main__":
    main()

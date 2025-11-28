import os
from dotenv import load_dotenv

# Try to load .secrets and .env if present
for fname in [".secrets", ".env", "local_config.env"]:
    if os.path.exists(fname):
        load_dotenv(fname)

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)

.PHONY: backend-venv backend-install backend-dev backend-test \
        mobile-get mobile-run-android format lint

BACKEND_DIR := backend
MOBILE_DIR := mobile

# Create a Python virtual environment for the backend.
backend-venv:
	cd $(BACKEND_DIR) && (python3 -m venv .venv || python -m venv .venv)

# Install backend dependencies into the virtual environment.
backend-install: backend-venv
	cd $(BACKEND_DIR) && . .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

# Run the backend in development mode with auto-reload on port 8000.
backend-dev: backend-venv
	cd $(BACKEND_DIR) && . .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run backend tests.
backend-test: backend-venv
	cd $(BACKEND_DIR) && . .venv/bin/activate && pytest

# Fetch Flutter dependencies for the mobile app.
mobile-get:
	cd $(MOBILE_DIR) && flutter pub get

# Run the Flutter app on an Android emulator (or default device if not specified).
mobile-run-android: mobile-get
	cd $(MOBILE_DIR) && flutter run

# Format backend Python code using ruff.
format: backend-venv
	cd $(BACKEND_DIR) && . .venv/bin/activate && ruff format .

# Lint backend Python code and run Flutter analyze.
lint: backend-venv
	cd $(BACKEND_DIR) && . .venv/bin/activate && ruff check .
	cd $(MOBILE_DIR) && flutter analyze
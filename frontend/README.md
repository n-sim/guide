# GUIDE frontend

The Dash dashboard reads PostgreSQL directly to show project activity, commit history, contributor comparisons, and heuristic indicators.

## Run

Follow the [quick start](../README.md#quick-start) guide, then open <http://localhost:8050>. Compose waits for the backend to initialize the database.

## Configuration

Edit [config/indicators.toml](config/indicators.toml); all settings are required and apply application-wide. For Docker, rebuild with `docker compose up -d --build frontend`
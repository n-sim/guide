# GUIDE backend

The Flask receiver accepts `POST /webhook`, fetches new commits and their ancestors from GitLab, and stores metadata and diffs in PostgreSQL. Each push uses one transaction.

## Run

Follow the [quick start](../README.md#quick-start) guide
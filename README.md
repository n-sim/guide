# GUIDE: A Groupwork Understanding and Insight Dashboard for Educators

GUIDE is a prototype for exploring students' collaboration and Git usage.
It displays GitLab commit activity and heuristic indicators in a dashboard.
It was developed as part of my bachelor thesis at TU Wien.

- [Quick start](#quick-start)
  - [1. Prepare the configuration](#1-prepare-the-config)
  - [2. Choose GitLab setup](#2-choose-gitlab-setup)
  - [3. Verify GUIDE is running](#3-verify-guide-is-running)
  - [4. Add a project webhook](#4-add-a-project-webhook)
- [Demo](#demo)
- [Limitations](#limitations)

## Quick start

You need:

- Docker (with Compose)
- Maintainer or Owner access to the GitLab projects you want to monitor

### 1. Prepare the config

Copy the example configuration to get an `.env` file:

```sh
cp .env.example .env
```

Set these values in `.env` for either setup:

| Variable | Value                                                                     |
| --- |---------------------------------------------------------------------------|
| `DB_PASSWORD` | Oassword for GUIDE's database                                         |
| `GITLAB_WEBHOOK_SECRET` | A separate random secret; use the same value in GitLab's webhook settings |

Keep the other values as defaults for now. 

### 2. Choose GitLab setup

Follow one of the options below, then continue with step 3.

#### Option A: Use a separate GitLab

Use this option for an existing GitLab instance.

1. Create a [personal access token](https://docs.gitlab.com/user/profile/personal_access_tokens/) with the **`read_api`** scope and choose an expiry. Its account must have read access to every monitored project.
2. Set `GITLAB_PRIVATE_TOKEN` in `.env` to that token.
3. Set `GITLAB_API_URL` to the full API base, including any port/subpath and `/api/v4`, for example `https://gitlab.example.com/api/v4`.
4. Check the network addresses below and adjust `BACKEND_BIND_ADDRESS` if needed.

##### Network addresses

Each address must be reachable by its caller:

| GitLab location | `GITLAB_API_URL` (called by GUIDE) | Webhook URL (called by GitLab) |
| --- | --- | --- |
| Remote server | `https://gitlab.example.com/api/v4` | A GUIDE address reachable from that server, e.g. `https://guide.example.com/webhook` through a proxy to the backend |
| Docker Desktop container, published on the host's port 80 | `http://host.docker.internal/api/v4` | `http://host.docker.internal:5001/webhook` |
| Directly on the Docker Desktop host, port 80 | `http://host.docker.internal/api/v4` | `http://localhost:5001/webhook` |

The `host.docker.internal` examples require [Docker Desktop networking](https://docs.docker.com/desktop/features/networking/). Adjust ports and subpaths to match your GitLab instance.

For container or remote connections to GUIDE through the host network, set `BACKEND_BIND_ADDRESS=0.0.0.0` in `.env` and allow the backend port through the firewall. Remote GitLab needs a reachable hostname/IP or an HTTPS proxy to the backend; its webhook URL cannot point to your computer's `localhost`.

If GitLab blocks the webhook URL, allowlist its hostname/IP under **Admin → Settings → Network → Outbound requests**. 
For example, allow `host.docker.internal`. See [outbound request filtering](https://docs.gitlab.com/security/webhooks/). 

Once configured, start GUIDE:

```sh
docker compose config --quiet
docker compose up -d --build --wait
```

Continue with step 3.

#### Option B: Use the bundled GitLab

Use this option to start a local GitLab instance alongside GUIDE. The additional Compose file configures GUIDE to call `http://gitlab/api/v4` and allows GitLab webhooks to reach `http://backend:5000/webhook`. No backend binding change is needed.

1. In `.env`, keep the nonempty `GITLAB_API_URL` and `GITLAB_PRIVATE_TOKEN` placeholders for now. 

   GitLab uses ports 8080 and 2222. If either is already in use, change `GITLAB_HTTP_PORT` or `GITLAB_SSH_PORT` in `.env`. `GITLAB_IMAGE` selects the GitLab image version.

2. Start GitLab and the database:

   ```sh
   docker compose -f compose.yaml -f compose.gitlab.yaml config --quiet
   docker compose -f compose.yaml -f compose.gitlab.yaml up -d gitlab db
   ```

   Wait for the sign-in page at <http://localhost:8080>.

3. Read the initial root password:

   ```sh
   docker compose -f compose.yaml -f compose.gitlab.yaml exec gitlab cat /etc/gitlab/initial_root_password
   ```

   Sign in as `root`, change the password, and create a [personal access token](https://docs.gitlab.com/user/profile/personal_access_tokens/) with **`read_api`** and an expiry. Replace `GITLAB_PRIVATE_TOKEN` in `.env` with it. The token's account needs read access to every monitored project.

4. Start GUIDE:

   ```sh
   docker compose -f compose.yaml -f compose.gitlab.yaml up -d --build --wait db backend frontend
   ```

### 3. Verify GUIDE is running

Open the [dashboard](http://localhost:8050), which is initially empty. The [backend health check](http://localhost:5001/) should say `DB connection successful`. Database tables are created automatically.

If you changed `FRONTEND_PUBLISHED_PORT` or `BACKEND_PUBLISHED_PORT`, use those ports in the URLs instead.

### 4. Add a project webhook

With Maintainer or Owner access, open the GitLab project and go to Settings → Webhooks → Add new webhook:

1. Enter the URL: for separate GitLab, use the webhook URL for your [network setup](#network-addresses); for bundled GitLab, use `http://backend:5000/webhook`. The bundled configuration already allows requests to `backend`
2. Set the Secret token to the exact `GITLAB_WEBHOOK_SECRET` value from `.env`
3. Enable Push events for all branches you want to monitor. Leave other events disabled and use the default payload template
4. Save, then select Test → Push events. The project needs at least one commit for this test; for an empty project, push its first commit in the next step

## Demo

After starting GUIDE with either GitLab option, create an **empty** private GitLab project named `guide-demo`. Then run these commands in a directory where you keep your programming projects:

```sh
mkdir guide-demo
cd guide-demo
git init -b main
git -c user.name="Demo Student" -c user.email="student@example.invalid" commit --allow-empty -m "Initial demo commit"
git remote add origin <empty-gitlab-project-url>
git push -u origin main
```

Replace `<empty-gitlab-project-url>` with the project's clone URL and use your Git credentials. GUIDE's `read_api` token cannot push commits.

Add the webhook, then push again:

```sh
git -c user.name="Demo Student" -c user.email="student@example.invalid" commit --allow-empty -m "Trigger GUIDE history ingestion"
git push origin main
```

Refresh the dashboard. GUIDE should show one project with one author, two commits, and their parent relationship. Use unique history when repeating the demo in the same database.

## Limitations

- One GitLab instance per database: Forks/projects sharing commit hashes cannot be tracked separately.
- Only reachable ancestry: GUIDE follows parents even when GitLab limits the payload to 20 commits. It does not discover unrelated branches. Empty payloads add metadata only; tags are unsupported.
- Large histories may fail: Synchronous, recursive ingestion can exceed GitLab's delivery timeout or Python's recursion limit. `GITLAB_REQUEST_TIMEOUT` limits each API call. There is no worker or automatic retry.
- Check logs before retrying: A timed-out import may still be running. API/database errors roll back the request. Fix the cause, then resend the webhook or push a new commit. Stored commits are skipped; replay cannot repair incomplete records.

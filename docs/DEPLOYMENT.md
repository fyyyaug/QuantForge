# Deploying the bounded synthetic demo

The repository includes a Render Blueprint in `render.yaml`. It is a deployment configuration, not evidence that a public service has been deployed. This service serves the frontend and Python API together.

## Local preview

From the repository root, with the pinned Python environment installed:

```sh
export QUANTFORGE_PUBLIC_DEMO=true
export QUANTFORGE_COOKIE_SECURE=false
export QUANTFORGE_DATA_DIR=.quantforge
python -m backend
```

Open `http://127.0.0.1:8000/` and select **Try the live demo**. No model key, market-data key, or shared bearer token is needed. A malformed nonempty `QUANTFORGE_API_TOKEN` is still a configuration error; unset it or supply a valid private token.

The application does not load `.env` automatically. Set variables in the process environment or hosting dashboard. Local private mode remains available with `QUANTFORGE_PUBLIC_DEMO=false` and a random `QUANTFORGE_API_TOKEN` of at least 32 characters.

## Render configuration

Review the selected account/workspace and Render's cost estimate before creating resources. The Blueprint uses a **paid 0.5 CPU / 512 MB web service (`0.5c-512mb`) and a 1 GB persistent disk**. Persistent disks require a paid service; a free service's ephemeral filesystem does not provide the saved-history behavior described here. Published rates checked October 24, 2026 imply a base of about USD 7.25/month for compute and disk, excluding taxes, workspace subscriptions and metered overages; the dashboard estimate controls.

1. Push the reviewed source to a branch accessible to your Render Git provider connection.
2. In Render, create a Blueprint from that repository and branch. Use the repository root containing `render.yaml`; the outer folder holding the whitepaper is not the Git repository.
3. Review the resources and cost, then apply the Blueprint.
4. Verify that the service is healthy and perform the external-device checks below.

| Setting | Value |
| --- | --- |
| Runtime | Python 3.12.14 |
| Build command | `pip install -r requirements.lock` |
| Start command | `python -m backend` |
| Health check | `/health` |
| Instances / Python workers | Exactly 1 / 1 |
| `QUANTFORGE_HOST` | `0.0.0.0` |
| `PORT` | Provided by Render |
| `QUANTFORGE_PUBLIC_DEMO` | `true` |
| `QUANTFORGE_COOKIE_SECURE` | `true` |
| `QUANTFORGE_DATA_DIR` | `/var/data/quantforge` |
| Persistent disk mount | `/var/data`, 1 GB |
| Automatic deployments | Off; deploy reviewed revisions explicitly |

The Python process must have write access to the mounted path. Keep the Git checkout, `frontend/`, `fixtures/`, and `requirements.lock` together; installing only the Python package does not package the static assets or datasets. No separate Node build/server is required.

The Render connector can create web services, but its current create-service arguments do not attach a persistent disk or apply a Blueprint. Use the Blueprint dashboard flow for the complete disk-backed configuration. Do not describe a connector-created ephemeral service as durable.

## Demo isolation and quotas

Public mode is opt-in. Each new visitor receives a unique anonymous workspace through a same-origin session request. An HttpOnly, SameSite=Strict cookie carries a random credential; production uses a Secure `__Host-` cookie. SQLite stores only its SHA-256 hash. Session JSON never includes a credential or workspace identifier. Private bearer authentication has precedence, and an invalid supplied bearer never falls back to a demo cookie.

| Bound | Default |
| --- | --- |
| Session lifetime | 120 minutes |
| New sessions | 30 per fixed UTC hour for the whole service |
| Authenticated demo requests | 120 per fixed minute, 600 per session |
| Runs, including corrections and diagnostics | 12 per session |
| Plans / correction proposals | 24 / 24 per session |
| Data access | Six allowlisted synthetic fixtures; no uploads or generated code |

Run, plan, and correction creation limits are checked inside SQLite transactions. A repeated idempotency key can retrieve its original run even after the creation limit is reached. Request counters and session expiry survive process restarts. These application limits are for a small demonstration; an Internet-facing service also needs platform/edge abuse protection. They do not implement distributed rate limiting or hard CPU isolation.

Cookie-authenticated mutations require a custom same-origin request header and reject a mismatched Origin. Cross-origin CORS permission is not granted. Ending a demo revokes the cookie. Reloading the page resumes an unexpired session, including its history. Sessions are browser-scoped, so tabs in the same browser share a demo workspace.

Expired demo workspaces are purged at startup and before new-session issuance. Their runs, plans, approvals, corrections, events, and unreferenced scientific artifacts are removed. Private workspaces and still-referenced artifacts are preserved. Expiry is enforced immediately on access; physical cleanup occurs at the next sweep. Workspaces with in-flight runs wait for a terminal state before cleanup. Download reports before ending the session or waiting for expiry. Disk snapshots may retain older deleted data until their own retention ends; use only synthetic content in this demo.

## External acceptance gate

Use a fresh browser on a second device and record the actual public URL and source revision:

- Open the landing page over HTTPS and enter the demo without private configuration.
- Create and approve a normal plan; inspect real computed trades and NAV.
- Run the guided timing trap; verify Blocked status and the source/decision/fill timeline.
- Approve the timing correction; inspect the changed entry decisions and both saved results.
- Reload and reopen the child from history; its comparison must restore.
- Open a separate browser profile; it must have empty history and no access to the first profile's run IDs.
- Download the report, including its synthetic/invalid labels where appropriate.
- Restart the service without replacing its disk; the active session and saved experiments must remain accessible.
- Verify that limits produce controlled errors and ending a demo revokes access.

The local HTTP smoke script covers private and cookie-authenticated execution. It does not establish that the public URL, HTTPS cookie behavior, cloud disk, DNS, or platform settings are correct. Those checks require the deployed service.

## Operations

Back up SQLite with its online backup mechanism or a coherent disk snapshot, including WAL state. Do not copy only a live database file while ignoring its WAL. Keep one process and one service instance; startup marks interrupted jobs failed and must not run while another worker is using the same database. Disk-backed deploys can briefly interrupt the service, so perform final acceptance after the last deploy.

For larger workloads, replace the process lock and synchronous execution with a durable queue, workers, and a production identity/database design before increasing concurrency. The demo does not call a language model or place real trades.

## Official references

- [Render web services and port binding](https://render.com/docs/web-services)
- [Blueprint specification](https://render.com/docs/blueprint-spec)
- [Persistent disk requirements and limitations](https://render.com/docs/disks)
- [Render pricing](https://render.com/pricing)

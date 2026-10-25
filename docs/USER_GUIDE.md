# QuantForge User Guide

QuantForge lets you review a simple strategy, run a reproducible synthetic backtest, inspect audit evidence, and approve a separate corrected experiment. All included prices are fictional. The current planner uses a fixed strategy template; it does not call a language model or place trades.

## 1. Start on Windows

Open PowerShell and run:

```powershell
cd E:\QuantForge
# First-time setup only, if .venv does not exist:
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock

# Generate a private token in this PowerShell window:
$env:QUANTFORGE_PUBLIC_DEMO = "false"
$env:QUANTFORGE_API_TOKEN = .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(40))"
$env:QUANTFORGE_API_TOKEN
.\.venv\Scripts\python.exe -u -m backend
```

Copy your generated token before starting the server. Wait for `Application startup complete` and the Uvicorn listening address. Keep PowerShell open. Visit [the local workspace](http://127.0.0.1:8000/), paste the token into **Workspace token**, and select **Connect workspace**. The token is a secret configured for this server, not a GitHub token or an OpenAI API key.

The browser keeps private tokens in tab memory. Reconnect after refreshing. Experiments remain saved in the server's SQLite database, normally `.quantforge/research.sqlite3` relative to the directory where you started the server. Start from the same project directory to keep using the same history. Stop the server with Ctrl+C.

### Optional anonymous demo

To run the demo locally, stop the server, then use:

```powershell
$env:QUANTFORGE_PUBLIC_DEMO = "true"
$env:QUANTFORGE_COOKIE_SECURE = "false"
.\.venv\Scripts\python.exe -u -m backend
```

Select **Try the live demo**. No token is required for this path. Tabs in the same browser share the demo cookie and workspace; a separate browser profile gets a separate workspace. Refreshing resumes an active demo. Default limits are 120 minutes, 12 runs, 24 plans, 24 correction proposals, 120 authenticated requests per minute, and 600 authenticated requests per session. New sessions are limited to 30 per service per UTC hour.

**End demo** revokes access to that session. Download reports you need before ending it. If a reload fails because the session allowance is exhausted, use **End existing demo session** on the access page, then try a new demo. New-session capacity limits still apply. Temporary rate limits require waiting for the next limit window; retrying does not reset quotas. For HTTPS hosting, use Secure cookies and follow [Deployment](DEPLOYMENT.md).

## 2. Create your first experiment

1. Select **New research** and the `clean_momentum` dataset.
2. Keep the initial example: lookback 5 sessions, threshold 2%, starting capital USD 10,000, allocation fraction 1, commission 5 bps per side, and slippage 5 bps per side.
3. Select **Review plan**. Check the dates, signal, costs, and timing before accepting the acknowledgment and selecting **Approve & run experiment**.
4. Inspect results, the NAV chart, trade ledger, and skipped sessions. With the shipped full-sample default fixture, the displayed ending NAV is USD 11,378.25, total return 13.78%, maximum drawdown approximately -1.99%, and trade count 14.

Allocation fraction `1` means 100% of NAV; `0.5` means 50%. One basis point (bp) is 0.01%, so 5 bps is 0.05% per side. The signal requires a return strictly greater than the threshold. It uses the selected session's close and available history, enters at the next explicit session's open, and exits at that session's close. Initial flat sessions are expected while history accumulates. These are simplified synthetic sessions, not a real exchange calendar.

## 3. Read the audit

Select **Inspect the audit**. Expand evidence records to inspect source rows, fields, and timestamps.

| Status | Meaning |
| --- | --- |
| Passed | This implemented rule passed for the recorded evidence. |
| Warning | A disclosed issue needs attention, such as zero modeled trading costs. |
| Blocked | A blocking data or methodology problem was found. |
| Unverified | The application has not established this property. |
| Not applicable | The check does not apply to this experiment. |

`COMPLETED` in history means processing finished; it does not mean the strategy passed its audit. A clean audit does not establish profitability or realistic market execution. Unsupported coverage remains Unverified.

## 4. Try the timing diagnostic and correction

1. On New research, select **Review diagnostic example**.
2. Read the intentionally invalid timing assumptions and approve the diagnostic.
3. Open its audit. The timeline shows a decision and entry occurring before the required future close became available.
4. Request the timing correction, review the proposed change, and approve the new experiment.
5. Compare both runs and inspect the changed entry decisions. Different sessions can be selected even when trade counts match.

The original diagnostic remains invalid and is preserved. A correction creates a separate child run. The synthetic timing-trap example is designed to expose a timing error, not to demonstrate a profitable strategy.

For a normal run, the audit also offers a **Cost sensitivity experiment**. Its inputs are proposed costs for a new run. Review and approve the change to recompute; editing those fields does not change the original experiment.

## 5. Reopen and export

Use **Experiments** to view the latest 50 runs in the connected workspace. Select **Open** to inspect a saved run. Opening a correction child restores its comparison with the original. Use the report and JSON download controls to save the recorded evidence. Demo history expires; private history persists on the server's configured data directory. Localhost is accessible on your computer only; teammates need their own local setup or a separately verified hosted service.

## 6. Troubleshooting

| Symptom | Action |
| --- | --- |
| Connection refused | Confirm the backend is still running and open the exact HTTP address and port printed by Uvicorn. |
| Windows error 10048 | Port 8000 is occupied. Use the existing QuantForge process if appropriate, or set `$env:PORT = "8001"` before starting and open the printed address. |
| Invalid Workspace token | Use the token configured in the same PowerShell session that started this server. Generating a token in another window does not update a running server. |
| Demo request allowance exhausted | End the current demo using the available end-session control. A new demo requires remaining service capacity. |
| Demo rate limit | Wait for the indicated minute or hourly window to reset, then retry. |
| Dataset blocked | Inspect row/field evidence. Malformed fixtures intentionally exercise validation; choose `clean_momentum` for the normal example. |
| No trades / flat NAV | Check the threshold, lookback, sample, and skipped-session evidence. Zero trades can be a valid result. |
| Request timed out | Check history before creating another experiment; server execution may have completed. |
| Missing history | Check the access mode, server data directory, and whether the demo expired or ended. |

The application does not automatically read `.env`. Set environment variables in PowerShell or your hosting configuration. Changes to backend code or environment variables require restarting the server; refresh the browser to load updated frontend assets.

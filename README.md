# Stark Bank Challenge

Python Sandbox integration for the Stark Bank Back End Developer Trial.

## Current status

- Deployed on AWS EC2 with Ubuntu 24.04.
- FastAPI webhook receiver exposed over HTTPS through ngrok.
- Invoice batches and webhook events persisted in SQLite.
- Eight batches scheduled three hours apart, each containing 8–12 invoices.
- Continuous workers for invoice issuance and credited-event processing.
- Transfer lookup before creation, using a stable external ID per Invoice.
- Failed transfers recorded for review.
- Batch reconciliation against the API without automatic resending
  when the original request outcome is uncertain.
- 167 automated tests passed locally and on the AWS server.

## Integration validation

A manually triggered Sandbox test completed the full flow:
Invoice payment, authenticated webhook receipt, event persistence,
and a successful transfer of 1,000 cents with zero fees.

The automatic run started on September 30, 2026, at 06:13 UTC
(03:13 Brasília time), and is scheduled to end on October 1, 2026,
at 06:13 UTC.

At the latest verification:

- Batch 1 was completed.
- Batches 2–8 were pending.
- Nine webhook requests were acknowledged with HTTP 200.
- The event worker processed nine notifications as ignored.
- A successful transfer from an automatically issued batch had
  not yet been confirmed.

The full 24-hour execution is still in progress.

## Local setup

Developed using Python 3.14.

Create a virtual environment:

```powershell
py -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Start the development server:

```powershell
python -m uvicorn main:app --reload
```

## Endpoints

- Health check: http://127.0.0.1:8000/health
- Interactive API documentation: http://127.0.0.1:8000/docs

The health endpoint returns:

```json
{"status": "ok"}
```

This endpoint only checks whether the application responds.
It does not check connectivity with Stark Bank.

## Credentials

Local environment files and PEM keys are excluded through `.gitignore`.
Never commit private keys or other credentials.

## Tests

After installing the dependencies, run:

```powershell
python -m pytest -v
```

Tests cover health checks, scheduling, batch persistence and reservation,
invoice preparation, webhook validation, event processing, transfer reuse,
reconciliation, recovery, and worker execution.

API interactions are mocked. Tests use temporary SQLite databases and do
not create Sandbox operations. The latest verified suite has 167 passing tests.

## Sandbox connection check

Create a Sandbox Project and register its public key.
Store the corresponding private key locally at `.keys/private-key.pem`.

In PowerShell, set the Project ID for the current terminal:

```powershell
$env:STARKBANK_PROJECT_ID = "YOUR_SANDBOX_PROJECT_ID"
```

Run the read-only connection check:

```powershell
python check_connection.py
```

The script queries the Sandbox balance without creating invoices or transfers.
The balance amount is expressed in cents.

The Project must allow the public outbound IP used by your connection.
Never commit the private key.

## Manual Sandbox invoices

These scripts require the same credentials as the connection check.

Create one test invoice for R$ 10.00:

```powershell
python create_invoice.py
```

Each successful execution creates a new invoice.
If a request times out, check the Sandbox before retrying.

Retrieve an existing invoice, replacing INVOICE_ID with its ID:

```powershell
python get_invoice.py INVOICE_ID
```

Retrieval displays the status, amount, fee, and linked transaction IDs.
Amounts and fees are expressed in cents.

These scripts are manual integration checks, not the automatic 24-hour run.

## Webhook receiver

Endpoint: POST /webhook/starkbank

The receiver validates the original request body and Digital-Signature
header using the Stark Bank SDK.

Verified events are stored in data/events.db with pending status before
a successful response is returned. Repeated event IDs do not overwrite
existing records.

Responses:

- 200: event stored or already present.
- 400: missing or invalid signature, or invalid UTF-8.
- 503: event storage failed.

The data directory is excluded from Git. Preserve the database between
application restarts.

The event worker processes invoice `credited` notifications and transfers
the invoice amount minus its fee, in integer cents. Other notification
types are ignored. An event is marked `processed` after transfer success;
failed or canceled transfers are recorded as `needs_review`.

## Sandbox validation

A manual integration test confirmed the following flow:

1. An Invoice was created and paid in the Sandbox.
2. The signed webhook was validated and persisted locally.
3. The credited event was processed.
4. A transfer of 1,000 cents completed successfully, with zero fees.
5. Processing the event again reused the existing transfer and marked
   the event as processed.

An earlier transfer failed with `Duplicated transfer`. Following Stark
Bank support guidance, the external ID prefix was changed to
`maria-eduarda-{invoice_id}`. The previous failure was preserved in the
local review history.

The continuous 24-hour batch run is in progress, as detailed above.

## Running the workers

On Linux, create a separate virtual environment and configure the same
Sandbox credentials described above:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export STARKBANK_PROJECT_ID="YOUR_SANDBOX_PROJECT_ID"
```

Preview a schedule using a future start time with an explicit timezone.
Replace the placeholder below with an actual date and time:

```bash
python plan_batches.py --start-at "YYYY-MM-DDTHH:MM:SS-03:00"
```

Add `--save` to persist that schedule. An existing different schedule is
rejected. Do not recreate the schedule or delete the database to restart
an ongoing run.

Preview pending batches and events without creating operations:

```bash
python run_batches.py
python process_pending.py
```

With the API and public webhook endpoint running, start the workers in
separate processes:

```bash
python run_batches.py --execute --watch
python watch_events.py --execute
```

These commands create Sandbox operations. The batch worker checks for due
batches every 30 seconds. The event worker should remain running after the
issuance window ends to handle later payments. Do not run a manual event
execution alongside the continuous event worker.

Inspect the saved batch states:

```bash
python batch_status.py
```

`completed` means invoice creation was confirmed and the returned IDs were
saved; it does not mean the invoices have been paid or their transfers
have succeeded.

## AWS deployment

The current deployment uses one EC2 instance running Ubuntu 24.04, with
SQLite stored at `/home/ubuntu/stark-bank-challenge/data/events.db` on its
EBS disk. The repository is checked out at `/home/ubuntu/stark-bank-challenge`.

Four systemd services were configured on the server:

| Service | Command / responsibility |
| --- | --- |
| `stark-api` | Uvicorn serving `main:app` on `127.0.0.1:8000` |
| `stark-tunnel` | ngrok exposing the API over HTTPS |
| `stark-events` | `watch_events.py --execute` |
| `stark-batches` | `run_batches.py --execute --watch` |

These unit files are configured on the server, not installed automatically
by cloning this repository. Services run as `ubuntu`, use the project
working directory and virtual environment, and restart on failure.

The Python services load `STARKBANK_PROJECT_ID` from
`/etc/stark-challenge.env`. The Stark Bank private key is stored in
`.keys/private-key.pem` with mode `600`. The ngrok credential is stored in
the user's ngrok configuration, outside the repository.

Configure the Sandbox Project to allow the server's public outbound IP.
Register the public `/webhook/starkbank` URL with an Invoice subscription.
SSH access is restricted to the administrator's IP; ngrok connects
outbound and forwards requests to the loopback-only API.

Public health endpoint:
[Health check](https://applaud-encourage-pushover.ngrok-free.dev/health).
This reports HTTP availability only, not worker or payment status.

Check services and logs over SSH:

```bash
systemctl is-active stark-api stark-tunnel stark-events stark-batches
sudo journalctl -u stark-batches -n 50 --no-pager
sudo journalctl -u stark-events -n 50 --no-pager
sudo journalctl -u stark-api -n 50 --no-pager
```

Closing SSH does not stop these services. The batch service exits normally
when its issuance window ends. Keep the API, tunnel, and event worker
running for late payments. Preserve the database and back it up before
terminating the EC2 instance.

## Operational limitations

- Run only one event processor at a time. Event processing does not use a
  distributed lock; transfer lookup is not an exactly-once guarantee.
- Keep `data/events.db` between restarts. It contains processing history,
  planned invoice data, and creation confirmations.
- A pending batch that is checked after its three-hour start window is
  marked `missed`. A missed batch means the full schedule was not fulfilled.
- Interrupted batches are not automatically resent. Recovery functions
  in `app/batch_recovery.py` require deliberate invocation after checking
  that no process is still executing the batch. Inconclusive reconciliation
  requires review; a query failure is not evidence that creation failed.
- Batch tags identify this single planned run. Independent future runs
  need distinct identifiers to avoid reconciliation collisions.
- Generated customer data is intended only for Sandbox testing.
- This is a single-instance deployment that requires monitoring, not a
  highly available production setup. Credits, ngrok limits, and server
  availability must be monitored during execution.

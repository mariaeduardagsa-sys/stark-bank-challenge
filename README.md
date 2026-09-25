# Stark Bank Challenge

Python application being developed for the Stark Bank Back End Developer Trial.

## Current status

- FastAPI application with a health endpoint.
- Batch schedule calculation and random invoice draft generation.
- Automated tests for the health endpoint, schedule, and draft generation.
- Sandbox authentication and balance query verified.
- Manual Sandbox invoice creation and retrieval verified.
- Webhook signature validation and SQLite event storage implemented.
- Webhook delivery from the Sandbox has not been verified yet.
- Automatic batch execution, stored-event processing, and transfers are pending.

## Planned features

- Issue 8 to 12 invoices every 3 hours for 24 hours.
- Validate invoice credit webhooks.
- Transfer the credited amount minus applicable fees.
- Prevent duplicate transfers when webhook events are retried.
- Include automated tests.

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

Tests cover the health endpoint, batch schedule calculation, and invoice
draft generation. They run locally without accessing Stark Bank.

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

Stored events are not processed into transfers yet.
Automated tests simulate SDK validation and use temporary SQLite databases.
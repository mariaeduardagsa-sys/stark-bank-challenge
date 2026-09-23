# Stark Bank Challenge

Python application being developed for the Stark Bank Back End Developer Trial.

## Current status

- FastAPI application with a health endpoint.
- Invoice scheduling, webhook processing, and transfers are not implemented yet.
- Sandbox integration is pending account access.

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

The current test checks that `/health` returns HTTP 200 and the expected JSON.
It runs locally without starting Uvicorn or accessing Stark Bank.
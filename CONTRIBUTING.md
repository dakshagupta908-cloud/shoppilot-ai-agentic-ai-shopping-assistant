# Contributing

Thanks for helping improve ShopPilot AI. This is a hackathon MVP; keep changes focused, preserve explicit buyer approval for payments, and do not claim unverified provider behavior.

## Local setup

Follow the backend and frontend setup in [README.md](./README.md). Keep your real `backend/.env` and `frontend/.env` local. Do not replace an existing environment file when copying an example.

## Before opening a change

Run the backend tests and frontend checks from their respective directories:

```powershell
cd backend
py -3.11 -m pytest -q
cd ..\frontend
npm run typecheck
npm run build
```

Backend tests must mock AI and payment providers; they must not send real prompts, use real payment credentials, or capture a Sandbox order. Add focused regression tests for behavior changes. For UI work, manually check the relevant user journey and keyboard/mobile behavior; the frontend does not currently have an automated test runner.

## Security and payment rules

- Never commit `.env`, API keys, PayPal Client Secrets, buyer credentials, local database files, or logs containing sensitive data.
- Keep the Gemini API key and PayPal Secret on the backend. `VITE_` variables are public browser code.
- Use only PayPal Sandbox credentials and the Sandbox API host.
- Never automate buyer approval, simulate successful payment, or mark an order paid without a verified completed capture.
- Do not paste credentials or unredacted payment diagnostics into issues or pull requests.

## Pull requests

Use a descriptive branch and commit message. Explain the behavior change, tests run, and any manual verification still required. Include screenshots for visual changes only when they show the actual application; never invent screenshots or imply an unverified payment succeeded.

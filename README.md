# ShopPilot AI

**Tell us what you need. Let AI find it. You decide. PayPal makes it happen.**

ShopPilot AI is a catalogue-backed shopping assistant: describe a product in natural language, get ranked recommendations from a seeded product catalogue, compare real specifications, keep a browser-scoped cart, and complete an explicitly approved PayPal Sandbox checkout.

> **Payment honesty:** this project does not simulate successful payments. PayPal checkout stays unavailable until valid Sandbox credentials are configured. The sample product catalogue and ratings are demo data. The displayed INR→USD rate is configurable and disclosed before checkout.

## What it does

- Responsive React/Vite storefront with product discovery, category/price/search/sort filters, product details and comparison of up to three products.
- Natural-language recommendation endpoint with server-side database search, budget and RAM constraints, ranking, grounded explanations, optional OpenAI/Gemini requirements extraction, and deterministic fallback.
- Guest cart and order history persisted in SQLite and scoped to a browser-generated session ID.
- Server-calculated cart totals and USD checkout quotes. The browser never supplies trusted payment prices.
- PayPal Orders v2 Sandbox integration: backend OAuth, backend order creation, customer approval through the official PayPal JS SDK, and backend capture status/amount/currency verification.
- FastAPI OpenAPI documentation and pytest API coverage.

## Architecture

```text
frontend/ (React, Vite, TypeScript, Axios, React Router, Tailwind, Lucide, PayPal JS SDK)
       │ JSON API + browser-scoped X-Session-ID
       ▼
backend/app/ (FastAPI, Pydantic, SQLAlchemy, optional LLM extraction, PayPal service)
       │
       └── SQLite (products, guest carts, verified orders and item snapshots)
```

The recommendation agent can only return product records from the database. The LLM, when enabled, extracts structured shopping constraints; catalogue filtering, price checks, ranking and product details stay server-side. The fallback runs without an AI key. It is not a generative chatbot and does not invent products.

## Requirements

- Node.js 18+ and npm
- Python 3.11+
- PayPal Developer Sandbox credentials for an actual Sandbox transaction (optional to run the rest)
- OpenAI or Gemini API key for LLM-assisted requirement extraction (optional)

## Setup

Open two terminals from the project root.

### 1. Backend

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload --port 8000
```

The database and sample catalogue are initialized automatically at startup. API docs: <http://localhost:8000/docs>. Health check: <http://localhost:8000/api/health>.

### 2. Frontend

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open <http://localhost:5173>. `VITE_API_BASE_URL` defaults to `http://localhost:8000`.

## Optional AI configuration

Edit `backend/.env`:

```dotenv
AI_PROVIDER=openai
AI_API_KEY=your-server-side-key
AI_MODEL=gpt-4o-mini
```

Or use Gemini:

```dotenv
AI_PROVIDER=gemini
AI_API_KEY=your-server-side-key
AI_MODEL=gemini-2.0-flash
```

Only the backend uses the key. If the provider is unset, unreachable, or returns an invalid response, requirements extraction falls back to deterministic parsing and catalogue-based recommendations. AI output never supplies catalogue product details or checkout amounts.

Create a key in the provider's developer console (OpenAI: <https://platform.openai.com/api-keys>; Gemini: <https://aistudio.google.com/app/apikey>). Do not paste the key into chat, source code, `frontend/.env`, or either example file. Keep it only in the ignored `backend/.env`, then restart FastAPI. The assistant response's `mode` is `llm_requirements+database` when extraction succeeds, and `database_fallback` otherwise. This validates behavior locally; a successful real API request still depends on a valid key, account access, and provider quota.

## PayPal Sandbox configuration

1. Sign in at [developer.paypal.com](https://developer.paypal.com/) and create a Sandbox REST app.
2. Put its Sandbox **Client ID and Secret** in `backend/.env`:

   ```dotenv
   PAYPAL_CLIENT_ID=your-sandbox-client-id
   PAYPAL_CLIENT_SECRET=your-sandbox-secret
   PAYPAL_BASE_URL=https://api-m.sandbox.paypal.com
   PAYPAL_INR_TO_USD_RATE=0.012
   ```

3. Set the same app’s public Sandbox client ID in `frontend/.env`:

   ```dotenv
   VITE_PAYPAL_CLIENT_ID=your-sandbox-client-id
   ```

4. Restart both dev servers and use a Sandbox personal/buyer account to approve the payment.

The backend validates `PAYPAL_BASE_URL` and refuses anything other than `https://api-m.sandbox.paypal.com`; live PayPal is not supported by this application. The client secret belongs only in `backend/.env`. The browser receives only the public `VITE_PAYPAL_CLIENT_ID`; it is passed to the official JavaScript SDK and never used as a secret.

The backend converts the server-calculated INR subtotal using `PAYPAL_INR_TO_USD_RATE`, rounds to cents, and returns both the INR source amount and USD amount. Checkout displays that rate and amount. A buyer must approve with PayPal; the backend captures only after approval and marks an order `COMPLETED` only when PayPal returns a completed capture with the expected USD amount and currency. Automated tests mock PayPal responses; they do not represent a real Sandbox transaction.

### PayPal Sandbox approval troubleshooting

Use ShopPilot in a regular Chrome or Edge window for Sandbox approval. Embedded browsers (including some IDE previews) may block PayPal's login popup and fall back to a sandboxed iframe; browser storage-access restrictions can then prevent buyer login even though the PayPal button and backend-created order are valid. Allow the PayPal popup and required site storage/cookies for the test session. If the approval page still fails in a regular browser, verify the personal Sandbox buyer is active and belongs to the same PayPal Developer account/environment as the Sandbox REST app. Never use Live credentials for this project.

## API overview

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Service and PayPal configuration status |
| GET | `/api/products` | Catalogue, optional `category`, `search`, `min_price`, `max_price`, `sort` |
| GET | `/api/products/{product_id}` | Product detail |
| GET | `/api/categories` | Available categories |
| POST | `/api/agent/recommend` or `/api/agent/chat` | Catalogue-grounded recommendations |
| POST | `/api/agent/compare` | Compare 2–3 product IDs |
| GET/POST | `/api/cart`, `/api/cart/items` | Read or replace a guest cart |
| PATCH/DELETE | `/api/cart/items/{item_id}` | Update or remove a cart line |
| POST | `/api/paypal/quote` | Server-calculated INR→USD checkout quote |
| POST | `/api/paypal/create-order` | Create PayPal Sandbox order on the server |
| POST | `/api/paypal/capture-order` | Capture and verify approved order on the server |
| POST | `/api/paypal/cancel-order` | Mark an unapproved local order cancelled |
| GET | `/api/orders` | Current guest session’s order history |
| GET | `/api/orders/{order_id}` | Current guest session’s order |

Cart and order calls use an `X-Session-ID` guest header. The frontend creates and stores a random ID in local storage. This is a demo guest-session mechanism, **not user authentication**. Never use this as a substitute for account authentication in a production store.

## Testing

```powershell
cd backend
py -3.11 -m pytest -q
cd ..\frontend
npm run typecheck
npm run build
```

Automated tests cover seeded product APIs, filtering, recommendation constraints, comparison, cart totals and updates, quote conversion, and mocked PayPal creation, capture verification, duplicate capture, cancellation, declined/pending outcomes, and uncertain capture transport errors. Tests use an isolated in-memory SQLite database so they do not add sample orders to the developer's local order history. Ambiguous captures remain `PENDING` and cannot be captured again automatically. A manual Sandbox checkout must be verified separately in the buyer flow and the backend order history; mocked tests do not represent a completed Sandbox transaction.

The frontend does not currently have an automated test-runner script. Validate it with `npm run typecheck`, `npm run build`, and browser testing of the customer journey and responsive layouts.

## Project layout

```text
backend/
  app/
    config.py database.py main.py models.py schemas.py seed.py services.py
  tests/test_api.py
  requirements.txt
frontend/
  src/
    components/ context/ pages/ services/ types.ts
    App.tsx main.tsx index.css pages.css
  tsconfig*.json
  package.json
```

## Known MVP limitations

- The optional LLM extracts requirements only; recommendation filtering and ranking are deterministic and catalogue-grounded.
- Sample catalogue and ratings are demonstration data, not live inventory or verified reviews.
- Guest cart/order history is scoped by a browser-generated ID and does not provide authenticated identity.
- The checkout conversion rate is an explicitly configured demo rate, not a live FX quote.
- Webhooks, shipping, tax, inventory reservation and production account security are not implemented.

## GitHub

Initialize a repository at this directory and push it using your normal GitHub workflow. `.gitignore` excludes environment files, local databases, virtual environments, caches, `node_modules`, and build output. Never commit `.env` files or real credentials.

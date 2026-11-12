# ShopPilot AI: three-minute demo guide

This guide demonstrates the current catalogue and shopping workflow without overstating AI or payment behavior. Use a fresh local database if you want a clean order history; see the database instructions in [README.md](./README.md). Do not delete a database that contains work you need.

## Before the demo

- Start the backend and frontend using the README instructions.
- Confirm `/api/health` responds and the product catalogue loads.
- Keep the optional AI provider disabled for a predictable, no-network fallback demo, or confirm your own provider configuration beforehand. The deterministic catalogue flow does not require an AI key.
- Use only PayPal Sandbox credentials and buyer accounts. The buyer login/approval issue is currently unresolved; do not promise a successful payment.

## Run of show

| Time | Show | Suggested narration |
|---|---|---|
| 0:00–0:20 | Home page and shopping prompt | “ShopPilot turns a natural-language need into a shortlist grounded in its product catalogue.” |
| 0:20–1:05 | Assistant prompt: “Laptop under ₹60,000 with 16GB RAM for Python and college work.” | Explain that the server extracts constraints, filters actual in-stock catalogue records, and provides deterministic ranked recommendations. If the response reports `database_fallback`, that is expected when AI is not configured. |
| 1:05–1:35 | Recommendation cards and product comparison | Open product details, select two or three products, and compare their stored prices/specifications. Do not describe sample ratings or inventory as real-world data. |
| 1:35–2:00 | Add a product and open the cart | Show the guest cart, quantity controls, and backend-calculated INR total. |
| 2:00–2:35 | Checkout summary | Show the USD quote, disclosed INR conversion rate, and Sandbox badge. Explain that order creation does not itself charge or capture the buyer. |
| 2:35–3:00 | Sandbox approval status and order result | The buyer must approve in PayPal before the frontend asks the backend to capture. Only present a paid confirmation if the backend order is `COMPLETED` with a PayPal capture ID. The approval flow has not been verified successfully for this project; if it fails, stop and report that honestly rather than simulating a success. |

## Payment demonstration safety

An actual successful Sandbox capture is not currently verified. Do not use a mock response, manually edit a database row, or visit an order-success URL to imply that payment succeeded. If you independently complete a legitimate Sandbox buyer approval, verify the returned order in the application and backend before presenting the result. Never use Live credentials or real payment details.

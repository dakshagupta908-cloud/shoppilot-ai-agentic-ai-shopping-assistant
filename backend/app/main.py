import uuid
from decimal import Decimal, ROUND_HALF_UP

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, engine, get_db, SessionLocal
from app.models import Cart, CartItem, Order, Product
from app.schemas import CartInput, CartQuantityInput, CaptureInput, CompareInput, RecommendInput
from app.seed import seed_products
from app.services import (
    amount_matches, get_cart, order_dict, paypal_token, product_dict, recommend,
    create_order_record, update_cart,
)

Base.metadata.create_all(bind=engine)
startup_db = SessionLocal()
try:
    seed_products(startup_db)
finally:
    startup_db.close()

app = FastAPI(title="ShopPilot AI API", version="1.0.0", description="Agentic shopping and PayPal Sandbox APIs")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def guest_session(x_session_id: str | None = Header(default=None)) -> str:
    if x_session_id is None:
        raise HTTPException(status_code=400, detail="A guest session ID is required.")
    if len(x_session_id) > 80 or not x_session_id.strip():
        raise HTTPException(status_code=400, detail="Invalid guest session identifier.")
    return x_session_id


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "shoppilot-ai", "paypal_configured": bool(settings.paypal_client_id and settings.paypal_client_secret)}


@app.get("/api/products")
def list_products(
    category: str | None = None, search: str | None = None,
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    sort: str = "featured", db: Session = Depends(get_db),
):
    query = db.query(Product).filter(Product.is_active.is_(True))
    if category and category.lower() != "all":
        query = query.filter(Product.category.ilike(category))
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(Product.name.ilike(term) | Product.brand.ilike(term) | Product.description.ilike(term))
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    products = query.all()
    if sort == "price_asc":
        products.sort(key=lambda p: p.price)
    elif sort == "price_desc":
        products.sort(key=lambda p: p.price, reverse=True)
    elif sort == "rating":
        products.sort(key=lambda p: p.rating, reverse=True)
    return {"products": [product_dict(product) for product in products], "categories": sorted({p.category for p in db.query(Product.category).all()})}


@app.get("/api/categories")
def categories(db: Session = Depends(get_db)):
    return {"categories": sorted({row[0] for row in db.query(Product.category).distinct().all()})}


@app.get("/api/products/{product_id}")
def product_details(product_id: str, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="Product not found.")
    return product_dict(product)


@app.post("/api/agent/recommend")
@app.post("/api/agent/chat")
def agent_recommend(payload: RecommendInput, db: Session = Depends(get_db)):
    result = recommend(db, payload.message, payload.product_ids)
    return result


@app.post("/api/agent/compare")
def compare(payload: CompareInput, db: Session = Depends(get_db)):
    products = [db.get(Product, pid) for pid in payload.product_ids]
    if any(product is None for product in products):
        raise HTTPException(status_code=404, detail="One or more products were not found.")
    return {"products": [product_dict(p) for p in products]}


@app.get("/api/cart")
def cart_get(session_id: str = Depends(guest_session), db: Session = Depends(get_db)):
    return get_cart(db, session_id)


@app.post("/api/cart")
@app.post("/api/cart/items")
def cart_set(payload: CartInput, session_id: str = Depends(guest_session), db: Session = Depends(get_db)):
    return update_cart(db, session_id, [item.model_dump() for item in payload.items])


@app.patch("/api/cart/items/{item_id}")
def cart_update(item_id: int, payload: CartQuantityInput, session_id: str = Depends(guest_session), db: Session = Depends(get_db)):
    item = db.query(CartItem).join(Cart).filter(Cart.id == session_id, CartItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found.")
    product = db.get(Product, item.product_id)
    if product.stock_quantity < payload.quantity:
        raise HTTPException(status_code=409, detail="Requested quantity exceeds available stock.")
    item.quantity = payload.quantity
    db.commit()
    return get_cart(db, session_id)


@app.delete("/api/cart/items/{item_id}")
def cart_remove(item_id: int, session_id: str = Depends(guest_session), db: Session = Depends(get_db)):
    item = db.query(CartItem).join(Cart).filter(Cart.id == session_id, CartItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found.")
    db.delete(item)
    db.commit()
    return get_cart(db, session_id)


def calculate_checkout(payload: CartInput, db: Session):
    if not payload.items:
        raise HTTPException(status_code=400, detail="Cannot check out an empty cart.")
    products = []
    for line in payload.items:
        product = db.get(Product, line.product_id)
        if not product or not product.is_active:
            raise HTTPException(status_code=404, detail=f"Product not found: {line.product_id}")
        if product.stock_quantity < line.quantity:
            raise HTTPException(status_code=409, detail=f"Insufficient stock for {product.name}")
        products.append({"product": product, "quantity": line.quantity})
    inr_total = sum(Decimal(str(line["product"].price)) * line["quantity"] for line in products)
    rate = Decimal(str(settings.paypal_inr_to_usd_rate))
    if rate <= 0:
        raise HTTPException(status_code=500, detail="PAYPAL_INR_TO_USD_RATE must be greater than zero.")
    usd = (inr_total * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return products, inr_total, rate, usd


@app.post("/api/paypal/quote")
def paypal_quote(payload: CartInput, db: Session = Depends(get_db)):
    _, inr_total, rate, usd = calculate_checkout(payload, db)
    return {
        "amount": f"{usd:.2f}", "currency": "USD",
        "source_amount": f"{inr_total:.2f}", "source_currency": "INR",
        "conversion_rate": float(rate),
    }


@app.post("/api/paypal/create-order")
async def paypal_create(payload: CartInput, session_id: str = Depends(guest_session), db: Session = Depends(get_db)):
    products, inr_total, rate, usd = calculate_checkout(payload, db)
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            token = await paypal_token(client)
            response = await client.post(
                f"{settings.paypal_base_url.rstrip('/')}/v2/checkout/orders",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={
                    "intent": "CAPTURE",
                    "purchase_units": [{
                        "reference_id": str(uuid.uuid4()),
                        "amount": {"currency_code": "USD", "value": f"{usd:.2f}"},
                        "description": "ShopPilot AI guest checkout",
                    }],
                },
            )
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail="Could not connect to PayPal Sandbox to create the order.") from error
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail="PayPal Sandbox could not create the order.")
    try:
        provider_order = response.json()
    except ValueError as error:
        raise HTTPException(status_code=502, detail="PayPal returned an invalid order response.") from error
    if not isinstance(provider_order, dict) or not provider_order.get("id"):
        raise HTTPException(status_code=502, detail="PayPal returned an invalid order response.")
    create_order_record(db, session_id, provider_order["id"], products, usd)
    return {
        "id": provider_order["id"], "currency": "USD", "amount": f"{usd:.2f}",
        "source_amount": f"{inr_total:.2f}", "source_currency": "INR",
        "conversion_rate": float(rate),
    }


@app.post("/api/paypal/capture-order")
async def paypal_capture(payload: CaptureInput, session_id: str = Depends(guest_session), db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.paypal_order_id == payload.order_id, Order.session_id == session_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="PayPal order not found for this guest session.")
    if order.status == "COMPLETED":
        return order_dict(order)
    if order.status != "CREATED":
        if order.status == "PENDING":
            raise HTTPException(status_code=409, detail="PayPal is still processing this capture. Check order history before retrying.")
        if order.status == "CANCELLED":
            raise HTTPException(status_code=409, detail="This checkout was cancelled and cannot be captured.")
        if order.status == "FAILED":
            raise HTTPException(status_code=409, detail="This payment attempt failed. Start a new checkout to try again.")
        raise HTTPException(status_code=409, detail="This order is already being processed.")

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            token = await paypal_token(client)
            claim = db.execute(
                update(Order)
                .where(Order.id == order.id, Order.status == "CREATED")
                .values(status="CAPTURING")
            )
            if claim.rowcount != 1:
                db.rollback()
                db.refresh(order)
                if order.status == "COMPLETED":
                    return order_dict(order)
                raise HTTPException(status_code=409, detail="This order is already being processed.")
            db.commit()
            db.refresh(order)
            response = await client.post(
                f"{settings.paypal_base_url.rstrip('/')}/v2/checkout/orders/{payload.order_id}/capture",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            )
    except httpx.HTTPError as error:
        order.status = "PENDING"
        db.commit()
        raise HTTPException(status_code=502, detail="Could not connect to PayPal Sandbox to verify the capture.") from error
    if response.status_code >= 400:
        if response.status_code >= 500:
            order.status = "PENDING"
        else:
            order.status = "FAILED"
        db.commit()
        raise HTTPException(status_code=502, detail="PayPal capture failed. No successful payment was recorded.")
    try:
        capture_result = response.json()
    except ValueError as error:
        order.status = "PENDING"
        db.commit()
        raise HTTPException(status_code=502, detail="PayPal returned an invalid capture response.") from error
    if not isinstance(capture_result, dict):
        order.status = "PENDING"
        db.commit()
        raise HTTPException(status_code=502, detail="PayPal returned an invalid capture response.")
    if capture_result.get("id") != payload.order_id:
        order.status = "PENDING"
        db.commit()
        raise HTTPException(status_code=409, detail="PayPal returned a different order than the requested capture.")
    captures = [
        capture for unit in capture_result.get("purchase_units", [])
        for capture in unit.get("payments", {}).get("captures", [])
    ]
    completed = next((capture for capture in captures if capture.get("status") == "COMPLETED"), None)
    failed = next((capture for capture in captures if capture.get("status") in {"DENIED", "DECLINED"}), None)
    if failed:
        order.status = "FAILED"
        order.paypal_capture_id = failed.get("id")
        db.commit()
        raise HTTPException(status_code=409, detail="PayPal declined this payment. Start a new checkout to try again.")
    if not completed or not completed.get("id") or capture_result.get("status") != "COMPLETED":
        pending = next((capture for capture in captures if capture.get("status") == "PENDING"), None)
        order.status = "PENDING"
        order.paypal_capture_id = pending.get("id") if pending else None
        db.commit()
        db.refresh(order)
        return order_dict(order)
    amount = completed.get("amount", {})
    if amount.get("currency_code") != order.currency or not amount_matches(amount.get("value", ""), order.total_amount):
        order.status = "FAILED"
        order.paypal_capture_id = completed.get("id")
        db.commit()
        raise HTTPException(status_code=409, detail="Captured amount or currency did not match the server order.")
    order.status = "COMPLETED"
    order.paypal_capture_id = completed.get("id")
    db.commit()
    db.refresh(order)
    cart = db.get(Cart, session_id)
    if cart:
        for item in list(cart.items):
            db.delete(item)
        db.commit()
    return order_dict(order)


@app.post("/api/paypal/cancel-order")
def paypal_cancel(payload: CaptureInput, session_id: str = Depends(guest_session), db: Session = Depends(get_db)):
    order = db.query(Order).filter(
        Order.paypal_order_id == payload.order_id,
        Order.session_id == session_id,
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="PayPal order not found for this guest session.")
    if order.status == "CANCELLED":
        return order_dict(order)
    if order.status != "CREATED":
        raise HTTPException(status_code=409, detail="This order can no longer be cancelled.")
    claim = db.execute(
        update(Order)
        .where(Order.id == order.id, Order.status == "CREATED")
        .values(status="CANCELLED")
    )
    if claim.rowcount != 1:
        db.rollback()
        db.refresh(order)
        if order.status == "CANCELLED":
            return order_dict(order)
        raise HTTPException(status_code=409, detail="This order can no longer be cancelled.")
    db.commit()
    db.refresh(order)
    return order_dict(order)


@app.get("/api/orders")
def orders_list(session_id: str = Depends(guest_session), db: Session = Depends(get_db)):
    orders = db.query(Order).filter(Order.session_id == session_id).order_by(Order.created_at.desc()).all()
    return {"orders": [order_dict(order) for order in orders]}


@app.get("/api/orders/{order_id}")
def order_get(order_id: str, session_id: str = Depends(guest_session), db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id, Order.session_id == session_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    return order_dict(order)

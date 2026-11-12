import logging
import re
import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

import httpx
import httpx2
from fastapi import HTTPException
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Cart, CartItem, Order, OrderItem, Product

logger = logging.getLogger(__name__)
ProductCategory = Literal[
    "Laptops", "Smartphones", "Headphones", "Keyboards", "Monitors", "Accessories",
]


class ShoppingRequirements(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: ProductCategory | None = None
    max_budget_inr: float | None = Field(default=None, gt=0, le=10_000_000, allow_inf_nan=False)
    minimum_ram_gb: int | None = Field(default=None, ge=1, le=512)
    keywords: list[str] = Field(default_factory=list, max_length=12)


CATEGORY_ALIASES = {
    "laptop": "Laptops", "notebook": "Laptops", "computer": "Laptops",
    "phone": "Smartphones", "smartphone": "Smartphones",
    "headphone": "Headphones", "earphone": "Headphones",
    "keyboard": "Keyboards", "monitor": "Monitors",
    "charger": "Accessories", "mouse": "Accessories", "accessory": "Accessories",
}


def product_dict(product: Product) -> dict:
    return {
        "id": product.id, "name": product.name, "brand": product.brand,
        "category": product.category, "description": product.description,
        "price": product.price, "currency": product.currency,
        "specifications": product.specifications, "image_url": product.image_url,
        "rating": product.rating, "rating_is_demo": True,
        "stock_quantity": product.stock_quantity,
        "in_stock": product.stock_quantity > 0,
    }


def parse_budget(message: str) -> float | None:
    candidates = re.findall(
        r"(?:₹|rs\.?\s*|inr\s*)\s*([\d,]+(?:\.\d+)?)\s*(k|thousand)?\b",
        message,
        re.I,
    )
    if candidates:
        amount, suffix = candidates[-1]
        return float(amount.replace(",", "")) * (1000 if suffix else 1)
    candidates = re.findall(r"([\d,]+(?:\.\d+)?)\s*(k|thousand)\b", message, re.I)
    if candidates:
        amount, _ = candidates[-1]
        return float(amount.replace(",", "")) * 1000
    return None


def extract_category(message: str) -> str | None:
    lowered = message.lower()
    matches = [
        (match.start(), category)
        for alias, category in CATEGORY_ALIASES.items()
        for match in re.finditer(rf"\b{re.escape(alias)}s?\b", lowered)
    ]
    return max(matches, default=(0, None))[1]


def extract_with_ai(message: str) -> tuple[dict | None, str | None]:
    provider = settings.ai_provider.strip().lower()
    if not provider:
        return None, None
    if provider != "gemini":
        return None, "Unsupported AI provider. Set AI_PROVIDER=gemini or leave it blank; using catalogue-based recommendations."
    if not settings.ai_api_key.strip():
        logger.warning("Gemini is enabled without an API key; using deterministic catalogue fallback.")
        return None, "Gemini is enabled, but AI_API_KEY is missing. Configure it in backend/.env; using catalogue-based recommendations."
    instruction = (
        "Extract only explicitly stated shopping requirements. Do not recommend products or invent product facts. "
        "Use category from the supplied schema, budget in INR, minimum RAM in GB, and concise search keywords. "
        "Set unknown values to null and keywords to an empty array."
    )
    try:
        with genai.Client(
            api_key=settings.ai_api_key,
            http_options=types.HttpOptions(timeout=12_000),
        ) as client:
            response = client.interactions.create(
                model=settings.ai_model,
                input=f"{instruction}\n\nCustomer request:\n{message[-5000:]}",
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": ShoppingRequirements.model_json_schema(),
                },
            )
        requirements = ShoppingRequirements.model_validate_json(response.output_text)
        return requirements.model_dump(), None
    except genai_errors.APIError as error:
        code = error.code
        logger.warning("Gemini API request failed with HTTP %s; using deterministic catalogue fallback.", code)
        if code in {401, 403}:
            warning = "Gemini authentication failed. Verify AI_API_KEY and API access; using catalogue-based recommendations."
        elif code == 400:
            warning = "Gemini rejected the request. Check the structured output and model configuration; using catalogue-based recommendations."
        elif code == 404:
            warning = "The configured Gemini model is unavailable. Check AI_MODEL and model access; using catalogue-based recommendations."
        elif code == 429:
            warning = "Gemini rate limit or quota was reached; using catalogue-based recommendations."
        else:
            warning = f"Gemini returned HTTP {code}; using catalogue-based recommendations."
        return None, warning
    except httpx2.HTTPError as error:
        logger.warning("Gemini transport request failed (%s); using deterministic catalogue fallback.", type(error).__name__)
        return None, "Could not connect to Gemini. Check network connectivity; using catalogue-based recommendations."
    except (ValidationError, ValueError, TypeError, AttributeError) as error:
        logger.warning("Gemini returned unusable structured requirements (%s); using deterministic catalogue fallback.", type(error).__name__)
        return None, "Gemini returned an invalid requirements response; using catalogue-based recommendations."


def recommend(db: Session, message: str, prior_ids: list[str] | None = None) -> dict:
    category = extract_category(message)
    budget = parse_budget(message)
    minimum_ram = None
    ai_requirements, ai_warning = extract_with_ai(message)
    if ai_requirements:
        allowed = {product.category for product in db.query(Product.category).distinct().all()}
        if ai_requirements.get("category") in allowed:
            category = ai_requirements["category"]
        ai_budget = ai_requirements.get("max_budget_inr")
        if isinstance(ai_budget, (int, float)) and 0 < ai_budget <= 10_000_000:
            budget = float(ai_budget)
        ai_ram = ai_requirements.get("minimum_ram_gb")
        if isinstance(ai_ram, (int, float)) and 1 <= ai_ram <= 512:
            minimum_ram = int(ai_ram)
    if minimum_ram is None:
        ram_match = re.search(r"\b(\d{1,3})\s*gb\s*(?:ram|memory)\b", message, re.I)
        if ram_match:
            minimum_ram = int(ram_match.group(1))
    if not category and prior_ids:
        prior = db.query(Product).filter(Product.id.in_(prior_ids)).first()
        category = prior.category if prior else None
    ai_keywords = ai_requirements.get("keywords", []) if ai_requirements else []
    words = {w for w in re.findall(r"[a-z0-9]+", message.lower()) if len(w) > 3}
    words.update(str(word).lower() for word in ai_keywords if isinstance(word, str) and len(word) > 2)
    requirements = {
        "category": category,
        "max_budget": budget,
        "minimum_ram_gb": minimum_ram,
        "keywords": sorted(words),
        "currency": "INR",
    }
    query = db.query(Product).filter(Product.is_active.is_(True), Product.stock_quantity > 0)
    if category:
        query = query.filter(Product.category == category)
    if budget is not None:
        query = query.filter(Product.price <= budget)
    products = query.all()
    if minimum_ram is not None:
        products = [
            product for product in products
            if re.search(r"(\d+)\s*gb", str(product.specifications.get("RAM", "")), re.I)
            and int(re.search(r"(\d+)\s*gb", str(product.specifications.get("RAM", "")), re.I).group(1)) >= minimum_ram
        ]
    ranked = []
    for product in products:
        searchable = " ".join(
            [product.name, product.brand, product.description, *product.specifications.values()]
        ).lower()
        matched = [word for word in words if word in searchable]
        score = round((product.rating * 12) + (len(matched) * 5), 1)
        reasons = []
        if category:
            reasons.append(f"Matches the {category.lower()} category")
        if budget is not None:
            reasons.append(f"Costs ₹{product.price:,.0f}, within your ₹{budget:,.0f} budget")
        if matched:
            reasons.append("Relevant details: " + ", ".join(matched[:3]))
        if not reasons:
            reasons.append("A highly rated in-stock option from the catalogue")
        ranked.append({
            "product": product_dict(product), "score": score,
            "explanation": ". ".join(reasons) + ".",
        })
    ranked.sort(key=lambda item: (-item["score"], item["product"]["price"]))
    ranked = ranked[:5]
    if not ranked:
        response = "I couldn't find an in-stock match for those constraints in the catalogue. Try a higher budget or a broader category."
    else:
        response = f"I found {len(ranked)} in-stock option{'s' if len(ranked) != 1 else ''} in the catalogue. Here are the closest matches based on your request."
    mode = "llm_requirements+database" if ai_requirements else "database_fallback"
    result = {"requirements": requirements, "recommendations": ranked, "response": response, "mode": mode}
    if ai_warning:
        result["ai_warning"] = ai_warning
    return result


def get_cart(db: Session, session_id: str) -> dict:
    cart = db.get(Cart, session_id)
    lines = []
    if cart:
        for item in cart.items:
            product = db.get(Product, item.product_id)
            if product:
                lines.append({
                    "item_id": item.id, "product": product_dict(product),
                    "quantity": item.quantity, "line_total": round(product.price * item.quantity, 2),
                })
    subtotal = round(sum(line["line_total"] for line in lines), 2)
    return {"session_id": session_id, "items": lines, "subtotal": subtotal, "total": subtotal, "currency": "INR"}


def update_cart(db: Session, session_id: str, lines: list[dict]) -> dict:
    cart = db.get(Cart, session_id)
    if not cart:
        cart = Cart(id=session_id)
        db.add(cart)
        db.flush()
    for item in list(cart.items):
        db.delete(item)
    for line in lines:
        product = db.get(Product, line["product_id"])
        if not product or not product.is_active:
            raise HTTPException(status_code=404, detail=f"Product not found: {line['product_id']}")
        if product.stock_quantity < line["quantity"]:
            raise HTTPException(status_code=409, detail=f"Insufficient stock for {product.name}")
        db.add(CartItem(cart_id=session_id, product_id=product.id, quantity=line["quantity"]))
    db.commit()
    return get_cart(db, session_id)


async def paypal_token(client: httpx.AsyncClient) -> str:
    if not settings.paypal_client_id or not settings.paypal_client_secret:
        raise HTTPException(status_code=503, detail="PayPal Sandbox is not configured. Set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET in backend/.env.")
    response = await client.post(
        f"{settings.paypal_base_url.rstrip('/')}/v1/oauth2/token",
        data={"grant_type": "client_credentials"},
        auth=(settings.paypal_client_id, settings.paypal_client_secret),
        headers={"Accept": "application/json"},
    )
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail="PayPal authentication failed; check Sandbox credentials.")
    try:
        token_data = response.json()
    except ValueError as error:
        raise HTTPException(status_code=502, detail="PayPal returned an invalid authentication response.") from error
    token = token_data.get("access_token") if isinstance(token_data, dict) else None
    if not token:
        raise HTTPException(status_code=502, detail="PayPal returned an invalid authentication response.")
    return token


def create_order_record(db: Session, session_id: str, paypal_id: str, items: list[dict], usd: Decimal) -> Order:
    order = Order(
        id=str(uuid.uuid4()), session_id=session_id, paypal_order_id=paypal_id,
        subtotal=float(usd), total_amount=float(usd), currency="USD", status="CREATED",
    )
    for line in items:
        product: Product = line["product"]
        order.items.append(OrderItem(
            product_id=product.id, product_name_snapshot=product.name,
            unit_price=float(
                (Decimal(str(product.price)) * Decimal(str(settings.paypal_inr_to_usd_rate)))
                .quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            ),
            quantity=line["quantity"],
        ))
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def order_dict(order: Order) -> dict:
    return {
        "id": order.id, "paypal_order_id": order.paypal_order_id,
        "paypal_capture_id": order.paypal_capture_id, "status": order.status,
        "amount": order.total_amount, "currency": order.currency,
        "created_at": order.created_at.isoformat(),
        "items": [{
            "product_id": item.product_id, "name": item.product_name_snapshot,
            "unit_price": item.unit_price, "quantity": item.quantity,
        } for item in order.items],
    }


def amount_matches(value: str, expected: float) -> bool:
    try:
        return Decimal(value).quantize(Decimal("0.01")) == Decimal(str(expected)).quantize(Decimal("0.01"))
    except Exception:
        return False

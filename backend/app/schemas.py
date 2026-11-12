from pydantic import BaseModel, Field


class CartLineInput(BaseModel):
    product_id: str
    quantity: int = Field(ge=1, le=20)


class CartInput(BaseModel):
    items: list[CartLineInput]


class CartQuantityInput(BaseModel):
    quantity: int = Field(ge=1, le=20)


class RecommendInput(BaseModel):
    message: str = Field(min_length=2, max_length=2000)
    product_ids: list[str] = Field(default_factory=list)


class CompareInput(BaseModel):
    product_ids: list[str] = Field(min_length=2, max_length=3)


class CaptureInput(BaseModel):
    order_id: str = Field(min_length=1, max_length=100)

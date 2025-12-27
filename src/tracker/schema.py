from uuid import UUID

from ninja import Schema


class ProductIn(Schema):
    name: str
    url: str
    target_price: float


class ProductOut(Schema):
    id: UUID
    name: str
    url: str
    target_price: float

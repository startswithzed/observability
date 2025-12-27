from typing import List

import structlog
from django.core.cache import cache
from django.db import connections
from ninja import NinjaAPI, Router

from src.tracker.models import Product
from src.tracker.schema import ProductIn, ProductOut

api = NinjaAPI(title="PriceWatch API")
logger = structlog.get_logger()

v1_router = Router()


@api.get("/healthz/live")
def liveness(request):
    """Is the process alive?"""
    logger.info("liveness_check_triggered")
    return {"status": "ok"}


@api.get("/healthz/ready")
def readiness(request):
    """Are dependencies (DB, Redis) reachable?"""
    logger.info("readiness_check_triggered")

    try:
        db_conn = connections["default"]
        db_conn.cursor()
    except Exception as e:
        logger.error(
            "readiness_check_failed_db",
            error=str(e),
        )
        return api.create_response(
            request,
            {
                "status": "unready",
                "reason": "db",
            },
            status=503,
        )

    try:
        cache.get("healthcheck")
    except Exception as e:
        logger.error(
            "readiness_check_failed_redis",
            error=str(e),
        )
        return api.create_response(
            request,
            {
                "status": "unready",
                "reason": "redis",
            },
            status=503,
        )

    return {"status": "ready"}


@api.get("/health")
def health_alias(request):
    return liveness(request)


@v1_router.post("/products", response=ProductOut)
def create_product(request, data: ProductIn):
    product = Product.objects.create(**data.dict())
    logger.info(
        "product_created",
        product_id=str(product.id),
        product_url=product.url,
    )
    return product


@v1_router.get("/products", response=List[ProductOut])
def list_products(request):
    return Product.objects.all()

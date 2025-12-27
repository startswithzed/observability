import uuid6
from django.db import models


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class BaseModel(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid6.uuid7,
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def soft_delete(self, **kwargs):
        self.is_deleted = True
        self.save()


class Product(BaseModel):
    name = models.CharField(max_length=255)
    url = models.URLField(unique=True)
    target_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["url"],
                name="idx_active_product_url",
                condition=models.Q(is_deleted=False),
            ),
        ]

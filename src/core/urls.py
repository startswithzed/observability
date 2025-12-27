from django.contrib import admin
from django.urls import path

from src.tracker.api import api, v1_router

api.add_router("/api/v1", v1_router)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", api.urls),
]

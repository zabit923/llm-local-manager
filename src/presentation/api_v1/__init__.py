from fastapi import APIRouter

from src.domain.constants import APIV1_PORTAL, APIV1_STAFF, APIV1_PUB
from src.presentation.api_v1.views.healthz import router as health_router

public_router = APIRouter(
    prefix=APIV1_PUB,
)
staff_router = APIRouter(
    prefix=APIV1_STAFF,
)
portal_router = APIRouter(
    prefix=APIV1_PORTAL,
)
setup_router = APIRouter()

# pub
public_router.include_router(router=health_router)

# portal

# admin

# setup

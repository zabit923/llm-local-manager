from fastapi import APIRouter

from src.domain.constants import APIV1_PORTAL, APIV1_STAFF, APIV1_PUB
from src.presentation.api_v1.views.healthz import router as health_router
from src.presentation.api_v1.views.public.agent import router as agent_router
from src.presentation.api_v1.views.public.orders import (
    router as public_orders_router,
)
from src.presentation.api_v1.views.staff.dishes import router as dishes_router
from src.presentation.api_v1.views.staff.drinks import router as drinks_router
from src.presentation.api_v1.views.staff.orders import router as orders_router

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
public_router.include_router(router=agent_router)
public_router.include_router(router=public_orders_router)

# portal

# admin
staff_router.include_router(router=dishes_router)
staff_router.include_router(router=drinks_router)
staff_router.include_router(router=orders_router)

# setup

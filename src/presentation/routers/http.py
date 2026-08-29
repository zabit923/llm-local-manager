from fastapi import APIRouter

from src.domain.constants import API_PREFIX, APIV1_PREFIX
from src.presentation.api_v1 import (
    portal_router,
    public_router,
    staff_router,
    setup_router,
)

router = APIRouter(
    prefix=API_PREFIX + APIV1_PREFIX,
)
router.include_router(public_router)
router.include_router(staff_router)
router.include_router(portal_router)
router.include_router(setup_router)

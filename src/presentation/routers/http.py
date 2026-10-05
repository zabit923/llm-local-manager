from fastapi import APIRouter

from src.presentation.api_v1 import (
    portal_router,
    public_router,
    setup_router,
    staff_router,
)

router = APIRouter(
    prefix="/api/v1",
)
router.include_router(public_router)
router.include_router(staff_router)
router.include_router(portal_router)
router.include_router(setup_router)

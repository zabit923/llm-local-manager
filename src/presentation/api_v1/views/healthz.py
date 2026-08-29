from fastapi import APIRouter
from fastapi.responses import JSONResponse
from dishka.integrations.fastapi import DishkaRoute

router = APIRouter(
    tags=["Health"],
    prefix="/healthcheck",
    route_class=DishkaRoute,
)


@router.get(
    "/",
    summary="Healthcheck",
)
async def healthz() -> JSONResponse:
    return JSONResponse(content={"status": "healthy"})

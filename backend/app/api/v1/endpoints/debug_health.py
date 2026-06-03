from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/debug-headers", tags=["system"])
async def debug_headers(request: Request):
    return dict(request.headers)

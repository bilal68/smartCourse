from fastapi import APIRouter

from app.api.v1.routes import courses, modules, assets, enrollments, auth  # add more later

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(courses.router)
api_router.include_router(modules.router)
api_router.include_router(assets.router)
api_router.include_router(enrollments.router)

from fastapi import APIRouter

# Import routers from new module structure
from app.modules.auth.routes import router as auth_router
from app.modules.courses.routes import router as courses_router
from app.modules.enrollments.routes import router as enrollments_router
from app.modules.progress.routes import router as progress_router

# Keep old routes for modules and assets (can be migrated later)
from app.api.v1.routes import modules, assets, celery_test

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(courses_router)
api_router.include_router(modules.router)
api_router.include_router(assets.router)
api_router.include_router(enrollments_router)
api_router.include_router(progress_router)
api_router.include_router(celery_test.router)

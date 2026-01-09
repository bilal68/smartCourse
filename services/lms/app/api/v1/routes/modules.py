from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.deps import get_current_active_user, get_db
from app.modules.courses.models import Course, Module
from app.schemas.module import ModuleCreate, ModuleRead, ModuleUpdate
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/modules", tags=["modules"],dependencies=[Depends(get_current_active_user)])


@router.post(
    "",
    response_model=ModuleRead,
    status_code=status.HTTP_201_CREATED,
)
def create_module(payload: ModuleCreate, db: Session = Depends(get_db)):
    # ensure course exists
    course = db.query(Course).filter(Course.id == payload.course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    module = Module(
        course_id=payload.course_id,
        title=payload.title,
        description=payload.description,
        order_index=payload.order_index,
    )

    db.add(module)
    db.commit()
    db.refresh(module)
    logger.info("created module", module_id=str(module.id), course_id=str(module.course_id))
    return module


@router.get(
    "/by-course/{course_id}",
    response_model=List[ModuleRead],
)
def list_modules_by_course(course_id: UUID, db: Session = Depends(get_db)):
    modules = (
        db.query(Module)
        .filter(Module.course_id == course_id)
        .order_by(Module.order_index)
        .all()
    )
    return modules


@router.get(
    "/{module_id}",
    response_model=ModuleRead,
)
def get_module(module_id: UUID, db: Session = Depends(get_db)):
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module not found",
        )
    return module


@router.patch(
    "/{module_id}",
    response_model=ModuleRead,
)
def update_module(
    module_id: UUID,
    payload: ModuleUpdate,
    db: Session = Depends(get_db),
):
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module not found",
        )

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(module, field, value)

    db.commit()
    db.refresh(module)
    return module


@router.delete(
    "/{module_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_module(module_id: UUID, db: Session = Depends(get_db)):
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module not found",
        )

    db.delete(module)
    db.commit()
    return None

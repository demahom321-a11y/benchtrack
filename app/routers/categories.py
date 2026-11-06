
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.category import Category
from app.models.item import Item
from app.schemas.category import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
)

router = APIRouter(
    prefix="/categories",
    tags=["Categories"],
)


def _commit_category(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if "UNIQUE constraint failed: categories.name" not in str(exc.orig):
            raise
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A category with this name already exists.",
        ) from exc


@router.post(
    "/",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"description": "A category with this name already exists."},
    },
)
def create_category(
    category: CategoryCreate,
    db: Session = Depends(get_db),
):
    db.execute(text("BEGIN IMMEDIATE"))

    existing_category = (
        db.query(Category)
        .filter(Category.name == category.name)
        .first()
    )

    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A category with this name already exists.",
        )

    new_category = Category(
        name=category.name,
        description=category.description,
    )

    db.add(new_category)
    _commit_category(db)
    db.refresh(new_category)

    return new_category


@router.get(
    "/",
    response_model=list[CategoryResponse],
)
def get_categories(
    db: Session = Depends(get_db),
):
    return db.query(Category).order_by(Category.id).all()


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    responses={
        404: {"description": "Category not found."},
    },
)
def get_category(
    category_id: int,
    db: Session = Depends(get_db),
):
    category = db.query(Category).filter(
        Category.id == category_id
    ).first()

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found.",
        )

    return category


@router.patch(
    "/{category_id}",
    response_model=CategoryResponse,
    responses={
        404: {"description": "Category not found."},
        409: {"description": "A category with this name already exists."},
    },
)
def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    db: Session = Depends(get_db),
):
    update_data = category_data.model_dump(exclude_unset=True)

    if "name" in update_data:
        db.execute(text("BEGIN IMMEDIATE"))

    category = db.query(Category).filter(
        Category.id == category_id
    ).first()

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found.",
        )

    # Category name is required and cannot be null.
    if "name" in update_data and update_data["name"] is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Category name cannot be null.",
        )

    # Check category name uniqueness.
    if "name" in update_data:
        existing_category = (
            db.query(Category)
            .filter(
                Category.name == update_data["name"],
                Category.id != category_id,
            )
            .first()
        )

        if existing_category:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A category with this name already exists.",
            )

    for field, value in update_data.items():
        setattr(category, field, value)

    _commit_category(db)
    db.refresh(category)

    return category


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"description": "Category not found."},
        409: {
            "description": "The category cannot be deleted while equipment is assigned to it."
        },
    },
)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
):
    category = db.query(Category).filter(
        Category.id == category_id
    ).first()

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found.",
        )

    linked_items = (
        db.query(Item.id)
        .filter(Item.category_id == category_id)
        .first()
    )

    if linked_items is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This category cannot be deleted because "
                "it is still assigned to equipment. "
                "Move the equipment to another category first."
            ),
        )

    db.delete(category)
    db.commit()

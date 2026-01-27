from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.modules.auth.models import User, Role, UserRole


class UserRepository:
    """Repository for User entity with CRUD operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(User.email == email).first()

    def create(self, email: str, full_name: str, password_hash: str) -> User:
        """Create a new user."""
        user = User(
            email=email,
            full_name=full_name,
            password_hash=password_hash,
        )
        self.db.add(user)
        self.db.flush()  # flush to get the ID without committing
        return user

    def update(self, user: User) -> User:
        """Update user."""
        self.db.flush()
        return user

    def delete(self, user: User) -> None:
        """Delete user."""
        self.db.delete(user)
        self.db.flush()


class RoleRepository:
    """Repository for Role entity with CRUD operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, role_id: uuid.UUID) -> Optional[Role]:
        """Get role by ID."""
        return self.db.query(Role).filter(Role.id == role_id).first()

    def get_by_name(self, name: str) -> Optional[Role]:
        """Get role by name."""
        return self.db.query(Role).filter(Role.name == name).first()

    def create(self, name: str, description: Optional[str] = None) -> Role:
        """Create a new role."""
        role = Role(name=name, description=description)
        self.db.add(role)
        self.db.flush()
        return role

    def list_all(self) -> list[Role]:
        """List all roles."""
        return self.db.query(Role).all()


class UserRoleRepository:
    """Repository for UserRole entity with CRUD operations."""

    def __init__(self, db: Session):
        self.db = db

    def assign_role(self, user_id: uuid.UUID, role_id: uuid.UUID) -> UserRole:
        """Assign a role to a user."""
        from app.modules.auth.models import UserRole

        user_role = UserRole(user_id=user_id, role_id=role_id)
        self.db.add(user_role)
        self.db.flush()
        return user_role

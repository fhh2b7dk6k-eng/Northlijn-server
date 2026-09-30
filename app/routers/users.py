from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.user import UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_current_user(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    """Required by Apple App Review Guideline 5.1.1(v): any app that
    supports account creation must also offer in-app account deletion,
    reachable without contacting support. Refresh tokens are deleted
    explicitly rather than relying solely on the DB foreign key's
    ON DELETE CASCADE, so this behaves identically on every engine
    (including SQLite in tests, which doesn't enforce FK actions by
    default)."""
    db.query(RefreshToken).filter(RefreshToken.user_id == current_user.id).delete()
    db.delete(current_user)
    db.commit()

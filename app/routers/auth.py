from fastapi import APIRouter, Depends, HTTPException, Request, Security
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth import SignupSchema, LoginSchema, CompleteProfileSchema
from app.models.user import User
from app.services.auth_service import login_user
from app.utils.security import create_access_token, create_refresh_token, hash_password, verify_token
from app.services.google_auth import oauth
import re

router = APIRouter(prefix="/auth", tags=["Auth"])
http_bearer = HTTPBearer()

phone_pattern = r"^\d{9}$"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone": user.phone,
        "role": user.role
    }

def token_response(user: User) -> dict:
    return {
        "tokens": {
            "access_token":  {"token": create_access_token({"user_id": user.id, "role": str(user.role.value) if hasattr(user.role, 'value') else user.role}), "type": "Bearer"},
            "refresh_token": {"token": create_refresh_token({"user_id": user.id}), "type": "Refresh"},
        },
        "user": user_to_dict(user)
    }


# ─── Dependencies ─────────────────────────────────────────────────────────────

def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    credentials = Security(HTTPBearer())
) -> User:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header missing or invalid")

    token = auth_header.split(" ")[1]
    payload = verify_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == payload.get("user_id")).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    role = current_user.role.value if hasattr(current_user.role, 'value') else current_user.role
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return current_user


# ─── Public routes ────────────────────────────────────────────────────────────

@router.post("/signup")
def signup(data: SignupSchema, db: Session = Depends(get_db)):
    if not re.match(phone_pattern, data.phone):
        raise HTTPException(status_code=400, detail="Phone format invalid. Use 9 digits format.")

    if db.query(User).filter(User.phone == data.phone).first():
        raise HTTPException(status_code=400, detail="Phone already registered")

    user = User(
        first_name=data.first_name,
        last_name=data.last_name,
        phone=data.phone,
        password=hash_password(data.password),
        role="admin"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "message": "User created successfully",
        "user": user_to_dict(user)
    }


@router.post("/login")
def login(data: LoginSchema, db: Session = Depends(get_db)):
    try:
        access, refresh = login_user(data, db)
        user = db.query(User).filter(User.phone == data.phone).first()
        return {
            "tokens": {
                "access_token":  {"token": access,  "type": "Bearer"},
                "refresh_token": {"token": refresh, "type": "Refresh"},
            },
            "user": user_to_dict(user)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/google/login")
async def google_login(request: Request):
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(
        request,
        redirect_uri,
        prompt="select_account"
    )


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    user_info = token.get('userinfo')
    if not user_info:
        raise HTTPException(status_code=400, detail="No user info from Google")

    google_id = user_info.get('sub')  # Google unique ID

    # google_id bo'yicha qidirish
    user = db.query(User).filter(User.google_id == google_id).first()

    if not user:
        user = User(
            first_name=user_info.get('given_name', ''),
            last_name=user_info.get('family_name', ''),
            phone=None,          # ← keyinroq complete-profile da olinadi
            password="google_oauth_user",
            google_id=google_id,
            role="user"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Telefon yo'q bo'lsa — temp token qaytaradi
    if not user.phone:
        temp_token = create_access_token({"user_id": user.id, "role": "user", "requires_phone": True})
        return {
            "status": "phone_required",
            "temp_token": {"token": temp_token, "type": "Bearer"},
            "message": "Telefon raqamingizni kiriting"
        }

    return token_response(user)


@router.post("/complete-profile")
def complete_profile(
    data: CompleteProfileSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Google login dan keyin telefon raqam qo'shish"""
    if not re.match(phone_pattern, data.phone):
        raise HTTPException(status_code=400, detail="Phone format invalid. Use 9 digits format.")

    if db.query(User).filter(User.phone == data.phone).first():
        raise HTTPException(status_code=400, detail="Phone already registered")

    current_user.phone = data.phone
    db.commit()
    db.refresh(current_user)

    return token_response(current_user)  # ← to'liq token


# ─── Protected routes ─────────────────────────────────────────────────────────

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {"user": user_to_dict(current_user)}


@router.get("/admin/users")
def get_all_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    return {"users": [user_to_dict(u) for u in db.query(User).all()]}
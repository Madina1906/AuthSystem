from sqlalchemy.orm import Session
from app.models.user import User
from app.utils.security import *
from app.utils.limiter import *


def login_user(data, db: Session):

    if not check_block(data.phone):

        raise Exception("Too many attempts. Try later")

    user = db.query(User).filter(User.phone == data.phone).first() 

    if not user:

        register_fail(data.phone)

        raise Exception("User not found")

    if not verify_password(data.password, user.password):

        register_fail(data.phone)

        raise Exception("Wrong password")

    reset(data.phone)

    access = create_access_token({
        "user_id": user.id,
        "role": user.role
    })

    refresh = create_refresh_token({
        "user_id": user.id
    })

    return access, refresh


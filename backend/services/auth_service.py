import requests 
from fastapi import HTTPException
from sqlalchemy import insert, select
from uuid import uuid4
import re
from utils.helper import Helper
from utils.logger import logger
from schema.schema import users, engine


class AuthService:
    def __init__(self, helper: Helper, engine):
        self.helper = helper
        self.engine = engine
    
    @staticmethod
    def user_exists(conn, email: str) -> bool:
        query = select(users).where(users.c.email == email)
        result = conn.execute(query).first()
        return result is not None 
    
    @staticmethod
    def is_strong_password(password: str) -> bool:
        if len(password) < 8:
            return False
        if not re.search(r"[A-Z]", password):   # uppercase letter
            return False
        if not re.search(r"[a-z]", password):   # lowercase letter
            return False
        if not re.search(r"\d", password):      # digit
            return False
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):  # special char 
            return False
        return True

    def register(self, data: dict[str, str]) -> dict[str, str]:
        email = data.get("email")
        password = data.get("password")

        #ensure password is strong
        if not self.is_strong_password(password):
            raise HTTPException(status_code=400, detail="Password is not strong.")

        if not email or not password:
            logger.warning("Email and password are required")
            raise HTTPException(status_code=400, detail="Email and Password are required")
        
        hashed_password = self.helper.hash_data(password)

        user_id = str(uuid4())
        user_role = "jobSeeker" 
        try:
            with self.engine.connect() as conn:
                if self.user_exists(conn, email):
                    logger.warning("Attempt to register an existing email")
                    raise HTTPException(status_code=400, detail="User already exists")
                    
                conn.execute(
                    insert(users).values(
                        id=user_id,
                        email=email,
                        password_hash=hashed_password,
                        is_active=True,
                        role=user_role,
                    )
                )
                conn.commit()

                access_token = self.helper.generate_jwt_token(user_id, user_role)

                logger.info(f"User {email} registered successfully with id {user_id}")

                return {
                    "access_token": access_token,
                    "token_type": "bearer",
                    "user_id": user_id,
                    "email": email,
                    "role": user_role
                }
        except Exception as e:
            logger.error("Error during Registration: ", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal Server Error")


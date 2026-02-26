from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

# here is RBAC 
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    password = Column(String)
    role = Column(String)  # admin | courier | customer


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    status = Column(String, default="created")  # created | assigned | delivered

    latitude = Column(String)
    longitude = Column(String)
    h3_index = Column(String, index=True)   # resolution-9 H3 cell

    customer_id = Column(Integer, ForeignKey("users.id"))
    courier_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    action = Column(String)
    user_id = Column(Integer)
    detail = Column(String, default="")
    timestamp = Column(DateTime, default=datetime.utcnow)

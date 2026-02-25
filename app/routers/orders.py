from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import h3

from ..models import Order
from ..dependencies import get_db, require_role
from ..events import publish_event
from ..audit import log_action
from ..schemas import CreateOrderRequest

router = APIRouter(tags=["orders"])
H3_RESOLUTION = 9


def safe_json(func):
    """Decorator to catch exceptions and always return JSON."""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs) if callable(func) else func(*args, **kwargs)
        except Exception as e:
            return {"error": str(e)}
    return wrapper


@router.post("/orders")
@safe_json
def create_order(
    body: CreateOrderRequest,
    db: Session = Depends(get_db),
    user=Depends(require_role("customer")),
):
    h3_index = h3.latlng_to_cell(body.latitude, body.longitude, H3_RESOLUTION)

    order = Order(
        latitude=str(body.latitude),
        longitude=str(body.longitude),
        h3_index=h3_index,
        customer_id=user.id,
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    log_action(db, user.id, "order_created", detail=f"order_id={order.id} h3={h3_index}")
    publish_event("order_created", {"order_id": order.id, "h3_index": h3_index})

    return {"order_id": order.id, "h3_index": h3_index, "status": order.status}


@router.post("/orders/{order_id}/assign")
@safe_json
def assign_order(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("courier")),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return {"error": "Order not found"}
    if order.status != "created":
        return {"error": f"Order is already '{order.status}'"}

    order.courier_id = user.id
    order.status = "assigned"
    db.commit()

    log_action(db, user.id, "order_assigned", detail=f"order_id={order_id} courier_id={user.id}")
    publish_event("order_assigned", {"order_id": order_id, "courier_id": user.id})

    return {"order_id": order_id, "status": order.status, "courier_id": user.id}


@router.post("/orders/{order_id}/deliver")
@safe_json
def deliver_order(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("courier")),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return {"error": "Order not found"}
    if order.courier_id != user.id:
        return {"error": "You are not assigned to this order"}
    if order.status != "assigned":
        return {"error": f"Order is '{order.status}', cannot deliver"}

    order.status = "delivered"
    db.commit()

    log_action(db, user.id, "order_delivered", detail=f"order_id={order_id}")
    publish_event("order_delivered", {"order_id": order_id})

    return {"order_id": order_id, "status": order.status}


@router.get("/orders/by-h3/{h3_index}")
@safe_json
def get_orders_by_h3(h3_index: str, db: Session = Depends(get_db)):
    orders = db.query(Order).filter(Order.h3_index == h3_index).all()
    return [
        {
            "order_id": o.id,
            "status": o.status,
            "h3_index": o.h3_index,
            "customer_id": o.customer_id,
            "courier_id": o.courier_id,
        }
        for o in orders
    ]


@router.get("/orders/h3-summary")
@safe_json
def h3_summary(db: Session = Depends(get_db)):
    rows = db.query(Order.h3_index, Order.status).all()
    summary: dict[str, dict] = {}
    for h3_index, status in rows:
        if h3_index not in summary:
            summary[h3_index] = {"h3_index": h3_index, "total": 0, "by_status": {}}
        summary[h3_index]["total"] += 1
        summary[h3_index]["by_status"][status] = summary[h3_index]["by_status"].get(status, 0) + 1
    return list(summary.values())
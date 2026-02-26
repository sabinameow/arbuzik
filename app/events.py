"""
Event bus module — simulates an event-driven architecture using an in-memory
queue and registered handlers. In production this would be replaced by a
message broker (e.g. RabbitMQ, Kafka, Redis Streams).
"""

from collections import defaultdict
from datetime import datetime
from typing import Callable


event_log: list[dict] = []


_handlers: dict[str, list[Callable]] = defaultdict(list)


def subscribe(event_type: str, handler: Callable):
    """Register a handler function for an event type."""
    _handlers[event_type].append(handler)


def publish_event(event_type: str, payload: dict):
    """Publish an event: records it and dispatches to all registered handlers."""
    event = {
        "event_type": event_type,
        "payload": payload,
        "timestamp": datetime.utcnow().isoformat(),
    }
    event_log.append(event)
    print(f"\n[EVENT BUS] Published: {event_type} -> {payload}")

    for handler in _handlers.get(event_type, []):
        handler(payload)


def _on_order_created(payload: dict):
    print(f"  [HANDLER] Notifying customer: order #{payload['order_id']} received, looking for a courier...")


def _on_order_assigned(payload: dict):
    print(f"  [HANDLER] Notifying courier #{payload['courier_id']}: assigned order #{payload['order_id']}.")
    print(f"  [HANDLER] Notifying customer: a courier is on the way for order #{payload['order_id']}.")


def _on_order_delivered(payload: dict):
    print(f"  [HANDLER] Order #{payload['order_id']} delivered. Triggering rating prompt for customer.")


subscribe("order_created", _on_order_created)
subscribe("order_assigned", _on_order_assigned)
subscribe("order_delivered", _on_order_delivered)

"""Simulated delivery partner (FR-SYS-13, FR-BUS-13).

No real courier is called. Handing an order over just gives it a reference number, and
the seller moves it along the steps below (standing in for the courier's status webhook).
"""

import secrets

from app.models import DeliveryStatus

NEXT_STATUS = {
    DeliveryStatus.handed_off: DeliveryStatus.out_for_delivery,
    DeliveryStatus.out_for_delivery: DeliveryStatus.delivered,
}


def hand_off() -> str:
    return f"DLV-{secrets.token_hex(5).upper()}"

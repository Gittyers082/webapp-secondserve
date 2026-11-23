"""Simulated delivery partner (FR-SYS-13, FR-BUS-13).

No real courier is called. A delivery order moves through these steps:

    pending           placed, waiting for the shop
    preparing         the shop marked it ready and handed it to the courier
    out-for-delivery  the courier is on the way
    delivered         it reached the customer; the order is finished

The seller moves it along with POST /api/orders/{id}/delivery, standing in for the
courier's status webhook. Ported from Ethan's backend-updates branch.
"""

from app.models import DeliveryStatus

# Where a delivery can go next from each step. Anything else is refused.
NEXT_STATUS = {
    DeliveryStatus.preparing: DeliveryStatus.out_for_delivery,
    DeliveryStatus.out_for_delivery: DeliveryStatus.delivered,
}

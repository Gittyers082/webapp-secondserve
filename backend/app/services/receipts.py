"""Order receipts (FR-USER-S-11, FR-USER-B-13).

A plain HTML page the buyer or seller can open, print or save as PDF from the browser.
Every value from the database is escaped, since names and addresses are user input.
"""

from decimal import Decimal
from html import escape

from app.models import FulfillmentType, Order, OrderType, User

_TYPE_LABEL = {
    OrderType.sale: "Purchase",
    OrderType.partner_purchase: "Partner purchase",
    OrderType.donation: "Donation claim",
}


def _peso(amount: Decimal | None) -> str:
    return f"₱{(amount or Decimal('0')):,.2f}"


def render(order: Order, customer: User | None) -> str:
    listing = order.listing
    profile = listing.seller.seller_profile if listing.seller else None
    shop = profile.business_name if profile else "SecondServe seller"
    fee = order.delivery_fee or Decimal("0")
    delivery = order.fulfillment_type == FulfillmentType.delivery
    payment = order.payment
    saved = (order.original_unit_price - order.unit_price) * order.quantity

    rows = [
        ("Order code", order.pickup_code),
        ("Type", _TYPE_LABEL.get(order.order_type, "Order")),
        ("Date", order.created_at.strftime("%b %d, %Y %I:%M %p UTC")),
        ("Customer", customer.username if customer else ""),
        ("Shop", shop),
        ("Status", order.status.value.replace("-", " ").title()),
        (
            "Delivery to" if delivery else "Pickup at",
            (order.delivery_address or "") if delivery else listing.pickup_location,
        ),
    ]
    if payment is not None:
        rows.append(("Payment", f"{payment.method.value} ({payment.status.value})"))
        rows.append(("Reference", payment.reference))

    details = "\n".join(
        f"<tr><th>{escape(label)}</th><td>{escape(str(value))}</td></tr>" for label, value in rows
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>SecondServe receipt {escape(order.pickup_code)}</title>
<style>
  body {{ font: 15px/1.5 system-ui, sans-serif; max-width: 560px; margin: 32px auto; color: #222; }}
  h1 {{ font-size: 22px; margin: 0 0 4px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
  th, td {{ text-align: left; padding: 6px 0; border-bottom: 1px solid #eee; }}
  th {{ font-weight: 600; width: 40%; }}
  .num {{ text-align: right; }}
  .total td, .total th {{ font-size: 17px; font-weight: 700; border-bottom: 0; }}
  .note {{ color: #666; font-size: 13px; }}
  @media print {{ .print {{ display: none; }} }}
</style>
</head>
<body>
<h1>SecondServe receipt</h1>
<p class="note">Surplus food, rescued in Baguio.</p>
<table>{details}</table>
<table>
  <tr><th>{escape(listing.name)} × {order.quantity}</th>
      <td class="num">{_peso(order.total)}</td></tr>
  {f'<tr><th>Delivery fee</th><td class="num">{_peso(fee)}</td></tr>' if delivery else ""}
  <tr class="total"><th>Total</th><td class="num">{_peso(order.total + fee)}</td></tr>
</table>
<p class="note">You saved {_peso(saved)} compared with the full price.</p>
<p class="note">Payments in this prototype are simulated. No card details are stored.</p>
<button class="print" onclick="window.print()">Print or save as PDF</button>
</body>
</html>
"""

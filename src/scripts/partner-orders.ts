import { api, errorMessage } from '../api/client';
import { currentAccount } from './account-ui';
import { announce } from './announce';
import { run } from './request';
import { badge, foodCell, td } from './partner-tables';
import { peso } from '../data/types';
import type { Order } from '../data/types';

function received(order: Order): boolean {
  return order.status === 'picked-up' || order.status === 'delivered' || order.deliveryStatus === 'delivered';
}

function progress(order: Order): { label: string; tone: string } {
  if (order.status === 'cancelled') return { label: 'Cancelled', tone: 'pill-danger' };
  if (order.fulfillmentType === 'delivery') {
    switch (order.deliveryStatus) {
      case 'delivered': return { label: 'Delivered', tone: 'pill-ok' };
      case 'out-for-delivery': return { label: 'Out for delivery', tone: 'pill-lime' };
      case 'preparing': return { label: 'Preparing', tone: 'pill-neutral' };
      case 'cancelled': return { label: 'Cancelled', tone: 'pill-danger' };
      default: return { label: 'Waiting for the shop', tone: 'pill-neutral' };
    }
  }
  if (order.status === 'picked-up') return { label: 'Picked up', tone: 'pill-ok' };
  if (order.status === 'ready') return { label: 'Ready for pickup', tone: 'pill-ok' };
  return { label: 'Reserved', tone: 'pill-neutral' };
}

export async function initPartnerOrders(): Promise<void> {
  const tableBody = document.querySelector<HTMLTableSectionElement>('[data-partner-orders-body]');
  const status = document.querySelector<HTMLElement>('[data-orders-loading]');
  const subtitle = document.querySelector<HTMLElement>('.section-sub');
  let orders: Order[] = [];

  function renderRow(order: Order): HTMLTableRowElement {
    const row = document.createElement('tr');
    row.dataset.order = order.id;
    row.append(foodCell(order.foodName, order.art));
    row.append(td('muted', order.shopName));
    row.append(td('num', String(order.quantity)));
    const paid = td('num');
    const sum = order.total + (order.deliveryFee ?? 0);
    if (order.orderType === 'donation' && sum === 0) paid.append(badge('Free', 'pill-lime'));
    else paid.textContent = peso(sum);
    row.append(paid);
    row.append(td('muted small', order.fulfillmentType === 'delivery'
      ? `Delivery to ${order.deliveryAddress ?? 'your address'}`
      : `Pickup at ${order.pickupLocation}`));
    const state = td();
    const p = progress(order);
    state.append(badge(p.label, p.tone));
    row.append(state);
    const actions = td('actions');
    if (order.distributionStatus === 'distributed') actions.append(badge('Distributed', 'pill-ok'));
    else if (received(order)) {
      const button = document.createElement('button');
      button.className = 'btn btn-sm btn-light';
      button.type = 'button';
      button.dataset.distribute = order.id;
      button.textContent = 'Mark distributed';
      button.setAttribute('aria-label', `Mark ${order.foodName} as distributed`);
      actions.append(button);
    } else {
      const info = document.createElement('span');
      info.className = 'small muted';
      info.textContent = 'Not received yet';
      actions.append(info);
    }
    row.append(actions);
    return row;
  }

  async function refreshOrders(): Promise<void> {
    if (!tableBody) return;
    if (status) { status.hidden = false; status.textContent = 'Loading your orders...'; }
    try {
      orders = await api.partner.orders();
      tableBody.replaceChildren(...orders.map(renderRow));
      const pending = orders.filter((order) => order.distributionStatus !== 'distributed' && order.status !== 'cancelled').length;
      if (subtitle) subtitle.textContent = `${pending} orders still to hand out to the people you serve.`;
      if (status) {
        status.textContent = orders.length ? '' : 'No orders yet. Visit the Surplus Board to find food.';
        status.hidden = orders.length > 0;
      }
    } catch (error) {
      if (status) status.textContent = `Could not load orders: ${errorMessage(error)}`;
    }
  }

  tableBody?.addEventListener('click', async (event) => {
    const button = (event.target as HTMLElement).closest<HTMLButtonElement>('[data-distribute]');
    if (!button) return;
    const id = button.dataset.distribute ?? '';
    const result = await run(button, () => api.partner.markDistributed(id));
    if (!result) return;
    const food = orders.find((order) => order.id === id)?.foodName ?? 'Order';
    announce(`${food} marked as distributed.`);
    await refreshOrders();
  });

  try {
    const account = await currentAccount();
    if (account.role === 'partner' && account.status === 'active') await refreshOrders();
  } catch (error) {
    if (status) status.textContent = `Could not load account: ${errorMessage(error)}`;
  }
}

import { api, errorMessage } from '../api/client';
import { currentAccount } from './account-ui';
import { announce } from './announce';
import { closeDialog, openDialog } from './dialog';
import { setupFilters } from './filters';
import { run, showError } from './request';
import { badge, foodCell, td } from './partner-tables';
import { peso } from '../data/types';
import type { Listing, FulfillmentType } from '../data/types';

export async function initPartnerBoard(): Promise<void> {
  const tableBody = document.querySelector<HTMLTableSectionElement>('[data-surplus-body]');
  const loading = document.querySelector<HTMLElement>('[data-surplus-loading]');
  const noResults = document.querySelector<HTMLElement>('[data-no-results]');
  const subtitle = document.querySelector<HTMLElement>('.section-sub');
  const scrim = document.querySelector<HTMLElement>('[data-dialog="take-offer"]');
  const form = scrim?.querySelector<HTMLFormElement>('[data-take-form]');
  const title = scrim?.querySelector<HTMLElement>('[data-dialog-title]');
  const message = scrim?.querySelector<HTMLElement>('[data-dialog-message]');
  const quantityInput = form?.querySelector<HTMLInputElement>('#take-quantity');
  const quantityHint = form?.querySelector<HTMLElement>('[data-quantity-hint]');
  const pickupRadio = form?.querySelector<HTMLInputElement>('input[value="pickup"]');
  const deliveryRadio = form?.querySelector<HTMLInputElement>('input[value="delivery"]');
  const deliveryLabel = form?.querySelector<HTMLElement>('[data-delivery-label]');
  const addressField = form?.querySelector<HTMLElement>('[data-address-field]');
  const addressInput = form?.querySelector<HTMLInputElement>('#take-address');
  const totalLine = form?.querySelector<HTMLElement>('[data-total]');
  const errorLine = form?.querySelector<HTMLElement>('[data-take-error]');
  const confirm = form?.querySelector<HTMLButtonElement>('[data-take-confirm]');
  const rows = () => Array.from(document.querySelectorAll<HTMLElement>('[data-offer]'));
  const filters = setupFilters({
    items: rows,
    noun: 'offer',
    matches: (row, filter, term) => Number(row.dataset.left) > 0 &&
      (filter === 'all' || row.dataset.channel === filter) &&
      (term === '' || (row.dataset.text ?? '').includes(term)),
  });

  let selected: Listing | null = null;
  let listings: Listing[] = [];

  function makeRow(listing: Listing): HTMLTableRowElement {
    const row = document.createElement('tr');
    const donation = listing.channel === 'donation';
    row.dataset.offer = listing.id;
    row.dataset.channel = listing.channel ?? '';
    row.dataset.text = `${listing.name} ${listing.shopName}`.toLowerCase();
    row.dataset.left = String(listing.quantity);
    row.append(foodCell(listing.name, listing.art));
    row.append(td('muted', listing.shopName));
    const remaining = td('num', String(listing.quantity));
    remaining.dataset.leftCell = '';
    row.append(remaining);
    const price = td('num');
    if (donation) price.append(badge('Free', 'pill-lime'));
    else {
      const original = document.createElement('s');
      original.className = 'small muted';
      original.textContent = peso(listing.originalPrice);
      price.append(document.createTextNode(`${peso(listing.discountedPrice)} `), original);
    }
    row.append(price);
    row.append(td('muted', listing.expiryLabel));
    const fulfillment = td();
    const pickup = listing.allowsPickup ?? true;
    const delivery = Boolean(listing.allowsDelivery);
    const kind = document.createElement('span');
    kind.className = 'small';
    kind.textContent = pickup && delivery ? 'Pickup or delivery' : delivery ? 'Delivery only' : 'Pickup only';
    fulfillment.append(kind);
    if (delivery) {
      const fee = document.createElement('span');
      fee.className = 'small muted block';
      fee.textContent = listing.deliveryFee ? `${peso(listing.deliveryFee)} delivery` : 'Free delivery';
      fulfillment.append(fee);
    }
    row.append(fulfillment);
    const action = td('actions');
    const button = document.createElement('button');
    button.className = 'btn btn-sm btn-primary';
    button.type = 'button';
    button.dataset.take = listing.id;
    button.textContent = donation ? 'Claim' : 'Buy';
    button.setAttribute('aria-label', `${button.textContent} ${listing.name}`);
    action.append(button);
    row.append(action);
    return row;
  }

  async function refreshList(): Promise<void> {
    if (!tableBody) return;
    if (loading) { loading.hidden = false; loading.textContent = 'Loading live surplus offers...'; }
    if (noResults) noResults.hidden = true;
    try {
      listings = await api.partner.surplus();
      tableBody.replaceChildren(...listings.map(makeRow));
      const donations = listings.filter((listing) => listing.channel === 'donation').length;
      if (subtitle) subtitle.textContent = `${listings.length} offers from shops, ${donations} free donations.`;
      if (loading) loading.hidden = true;
      filters.apply(false);
    } catch (error) {
      if (loading) loading.textContent = `Could not load offers: ${errorMessage(error)}`;
      if (noResults) noResults.hidden = true;
    }
  }

  const chosen = (): FulfillmentType => deliveryRadio?.checked ? 'delivery' : 'pickup';
  const showFormError = (message: string) => {
    if (!errorLine) return;
    errorLine.textContent = message;
    errorLine.hidden = message.length === 0;
  };
  const updateTotal = () => {
    if (!selected || !totalLine) return;
    const quantity = Number(quantityInput?.value) || 0;
    const deliveryFee = chosen() === 'delivery' ? selected.deliveryFee ?? 0 : 0;
    if (addressField) addressField.hidden = chosen() !== 'delivery';
    totalLine.textContent = selected.channel === 'donation'
      ? deliveryFee > 0 ? `Free food. Delivery fee: ${peso(deliveryFee)}.` : 'Free. Nothing to pay.'
      : `Total: ${peso(selected.discountedPrice * quantity + deliveryFee)}${deliveryFee ? ` (includes ${peso(deliveryFee)} delivery)` : ''}.`;
  };

  tableBody?.addEventListener('click', (event) => {
    const target = event.target as HTMLElement;
    const button = target.closest<HTMLButtonElement>('[data-take]');
    if (!button) return;
    const listing = listings.find((item) => item.id === button.dataset.take);
    if (!listing || listing.quantity <= 0) return;
    selected = listing;
    const donation = listing.channel === 'donation';
    if (title) title.textContent = `${donation ? 'Claim' : 'Buy'} ${listing.name}`;
    if (message) message.textContent = donation ? 'This is a free donation from the shop.' : '';
    if (confirm) confirm.textContent = donation ? 'Claim' : 'Buy';
    if (quantityInput) { quantityInput.max = String(listing.quantity); quantityInput.value = '1'; }
    if (quantityHint) quantityHint.textContent = `Up to ${listing.quantity}.`;
    const pickup = listing.allowsPickup ?? true;
    const delivery = Boolean(listing.allowsDelivery);
    if (pickupRadio) { pickupRadio.disabled = !pickup; pickupRadio.checked = pickup; }
    if (deliveryRadio) { deliveryRadio.disabled = !delivery; deliveryRadio.checked = !pickup && delivery; }
    if (deliveryLabel) deliveryLabel.textContent = delivery ? 'Deliver to us' : 'Deliver to us (not available)';
    showFormError('');
    updateTotal();
    openDialog('take-offer', button);
  });

  form?.addEventListener('input', updateTotal);
  form?.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!selected) return;
    const listing = selected;
    const quantity = Number(quantityInput?.value);
    if (!Number.isInteger(quantity) || quantity < 1 || quantity > listing.quantity) {
      showFormError(`Enter a whole number from 1 to ${listing.quantity}.`);
      quantityInput?.focus();
      return;
    }
    const fulfillmentType = chosen();
    const deliveryAddress = addressInput?.value.trim() ?? '';
    if (fulfillmentType === 'delivery' && deliveryAddress.length < 5) {
      showFormError('Enter a complete delivery address (at least 5 characters).');
      addressInput?.focus();
      return;
    }
    const input = { quantity, fulfillmentType, deliveryAddress: fulfillmentType === 'delivery' ? deliveryAddress : undefined };
    const order = await run(confirm ?? null, () => listing.channel === 'donation'
      ? api.partner.claim(listing.id, input)
      : api.partner.buy(listing.id, input));
    if (!order) return;
    closeDialog();
    announce(`${listing.channel === 'donation' ? 'Claimed' : 'Bought'} ${quantity} × ${listing.name}. Check My Orders.`);
    await refreshList();
  });

  try {
    const user = await currentAccount();
    if (user.role !== 'partner' || user.status !== 'active') return;
    if (addressInput) addressInput.value = user.partnerProfile?.address ?? '';
    await refreshList();
  } catch (error) {
    if (loading) loading.textContent = `Could not load account: ${errorMessage(error)}`;
    showError(errorMessage(error));
  }
}

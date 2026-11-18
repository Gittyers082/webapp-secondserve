/**
 * The buyer's wishlist and compare selection.
 *
 * Saved listing ids live in the browser until the wishlist endpoint is
 * agreed (see docs/api-contract.md). Any `[data-wishlist-toggle="<id>"]`
 * button saves or removes a listing and reports its state with aria-pressed.
 */
import { announce } from './announce';

const KEY = 'secondserve-wishlist';
export const COMPARE_LIMIT = 3;

let fallback: string[] = [];

export function savedIds(): string[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) return JSON.parse(raw) as string[];
  } catch {
    // Storage unavailable: keep the list for this page only.
  }
  return fallback;
}

function store(ids: string[]): void {
  fallback = ids;
  try {
    localStorage.setItem(KEY, JSON.stringify(ids));
  } catch {
    // See above.
  }
  document.dispatchEvent(new CustomEvent('wishlistchange', { detail: ids }));
}

export function isSaved(id: string): boolean {
  return savedIds().includes(id);
}

export function toggleSaved(id: string, name: string): boolean {
  const ids = savedIds();
  const saved = !ids.includes(id);
  store(saved ? [...ids, id] : ids.filter((other) => other !== id));
  announce(saved ? `${name} saved to your wishlist.` : `${name} removed from your wishlist.`);
  return saved;
}

function syncButtons(): void {
  const ids = savedIds();
  document.querySelectorAll<HTMLButtonElement>('[data-wishlist-toggle]').forEach((button) => {
    const saved = ids.includes(button.dataset.wishlistToggle ?? '');
    button.setAttribute('aria-pressed', String(saved));
    const label = button.querySelector<HTMLElement>('[data-wishlist-label]');
    if (label) label.textContent = saved ? 'Saved' : 'Save';
  });
  document.querySelectorAll<HTMLElement>('[data-wishlist-count]').forEach((node) => {
    node.textContent = String(ids.length);
    node.hidden = ids.length === 0;
    node.setAttribute('aria-label', `${ids.length} saved`);
  });
}

/** Seeds the list on first visit, then wires every save button on the page. */
export function initWishlist(seeded: string[]): void {
  fallback = seeded;
  try {
    if (localStorage.getItem(KEY) === null) localStorage.setItem(KEY, JSON.stringify(seeded));
  } catch {
    // See above.
  }

  syncButtons();
  document.addEventListener('wishlistchange', syncButtons);

  document.querySelectorAll<HTMLButtonElement>('[data-wishlist-toggle]').forEach((button) => {
    button.addEventListener('click', () => {
      toggleSaved(button.dataset.wishlistToggle ?? '', button.dataset.wishlistName ?? 'Item');
    });
  });
}

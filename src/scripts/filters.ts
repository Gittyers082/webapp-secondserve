/**
 * Shared filter-pill and search behaviour for Shop, User Management and
 * Item Moderation.
 *
 * Each screen supplies its items and a `matches` rule; this module keeps the
 * pills' `aria-pressed` state, shows or hides items, toggles the no-results
 * message and announces the visible count.
 */
import { announce, plural } from './announce';

interface FilterOptions {
  /** The elements that are shown or hidden. */
  items: () => HTMLElement[];
  /** Decides whether an item stays visible for the active pill and search term. */
  matches: (item: HTMLElement, filter: string, term: string) => boolean;
  /** Singular noun for the announcement: "listing" → "Showing 3 listings". */
  noun: string;
  /** Hidden together with the items when nothing matches. */
  container?: HTMLElement | null;
}

export function setupFilters({ items, matches, noun, container }: FilterOptions) {
  const pills = Array.from(document.querySelectorAll<HTMLButtonElement>('[data-filter]'));
  const search = document.querySelector<HTMLInputElement>('[data-search]');
  const noResults = document.querySelector<HTMLElement>('[data-no-results]');

  let filter = pills.find((pill) => pill.getAttribute('aria-pressed') === 'true')?.dataset.filter ?? 'all';
  let debounce = 0;

  const apply = (speak = true) => {
    const term = (search?.value ?? '').trim().toLowerCase();
    let visible = 0;

    items().forEach((item) => {
      const show = matches(item, filter, term);
      item.hidden = !show;
      if (show) visible += 1;
    });

    if (noResults) noResults.hidden = visible > 0;
    if (container) container.hidden = visible === 0;

    if (speak) {
      window.clearTimeout(debounce);
      debounce = window.setTimeout(() => {
        announce(visible === 0 ? `No ${noun}s match.` : `Showing ${plural(visible, noun)}.`);
      }, 350);
    }
  };

  pills.forEach((pill) => {
    pill.addEventListener('click', () => {
      filter = pill.dataset.filter ?? 'all';
      pills.forEach((other) => other.setAttribute('aria-pressed', String(other === pill)));
      apply();
    });
  });

  search?.addEventListener('input', () => apply());

  return { apply };
}

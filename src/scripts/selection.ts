/**
 * Single selection across selectable ListingCards (Shop, Manage Listings,
 * Item Moderation).
 *
 * The card's photo is the control: it is focusable, toggles with Enter or
 * Space as well as a click, and reports its state through `aria-pressed`.
 */

export interface SelectionOptions {
  /** Cards that can be selected; read on every change so removed cards drop out. */
  cards: () => HTMLElement[];
  onSelect?: (card: HTMLElement) => void;
  /** Return false to refuse a card (expired listings in the Shop). */
  canSelect?: (card: HTMLElement) => boolean;
}

export function setupSelection({ cards, onSelect, canSelect = () => true }: SelectionOptions) {
  const select = (card: HTMLElement) => {
    if (!canSelect(card)) return;

    cards().forEach((other) => {
      const isThis = other === card;
      other.classList.toggle('is-selected', isThis);
      other.querySelector('[data-select]')?.setAttribute('aria-pressed', String(isThis));
    });

    onSelect?.(card);
  };

  cards().forEach((card) => {
    const control = card.querySelector<HTMLElement>('[data-select]');
    if (!control) return;

    control.addEventListener('click', () => select(card));
    control.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        select(card);
      }
    });
  });

  return {
    select,
    selected: () => cards().find((card) => card.isConnected && card.classList.contains('is-selected')),
  };
}

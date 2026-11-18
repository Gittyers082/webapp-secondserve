/**
 * Polite screen-reader announcements.
 *
 * AppLayout renders one `[data-announcer]` status region per screen. Every
 * client-side change that is not otherwise visible to assistive tech (a filter
 * narrowing a grid, a row being removed, an order marked ready) goes through
 * here, so there is one live region rather than many competing ones.
 */
export function announce(message: string): void {
  const region = document.querySelector<HTMLElement>('[data-announcer]');
  if (!region) return;

  // Clearing first makes repeated identical messages announce again.
  region.textContent = '';
  window.setTimeout(() => {
    region.textContent = message;
  }, 60);
}

/** "1 listing" / "3 listings" */
export function plural(count: number, noun: string, pluralNoun = `${noun}s`): string {
  return `${count} ${count === 1 ? noun : pluralNoun}`;
}

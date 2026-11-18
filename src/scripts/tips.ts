/** Opens and closes the toggletips rendered by components/Tip.astro. */

const close = (button: HTMLButtonElement) => {
  button.setAttribute('aria-expanded', 'false');
  const bubble = document.getElementById(button.getAttribute('aria-controls') ?? '');
  if (bubble) bubble.hidden = true;
};

let wired = false;

export function initTips(): void {
  if (wired) return;
  wired = true;

  document.addEventListener('click', (event) => {
    const target = event.target as HTMLElement;
    const button = target.closest<HTMLButtonElement>('[data-tip]');

    document.querySelectorAll<HTMLButtonElement>('[data-tip][aria-expanded="true"]').forEach((open) => {
      if (open !== button) close(open);
    });

    if (!button) return;
    event.preventDefault();
    const bubble = document.getElementById(button.getAttribute('aria-controls') ?? '');
    if (!bubble) return;
    const opening = button.getAttribute('aria-expanded') !== 'true';
    button.setAttribute('aria-expanded', String(opening));
    // Re-inserting the text makes screen readers announce it each time.
    const text = bubble.textContent ?? '';
    bubble.textContent = '';
    bubble.hidden = !opening;
    if (opening) window.setTimeout(() => (bubble.textContent = text), 30);
    else bubble.textContent = text;
  });

  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    document.querySelectorAll<HTMLButtonElement>('[data-tip][aria-expanded="true"]').forEach((open) => {
      close(open);
      open.focus();
    });
  });
}

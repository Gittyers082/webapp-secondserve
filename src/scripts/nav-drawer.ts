/**
 * The menu drawer below 1000px wide.
 *
 * The top bar's menu button opens the sidebar as a drawer. Escape, the close
 * button, the scrim or choosing a page closes it, and focus returns to the
 * menu button. While it is open the page behind it is inert.
 */

const root = document.documentElement;

const isOpen = () => root.dataset.nav === 'open';

function setOpen(open: boolean): void {
  const button = document.querySelector<HTMLButtonElement>('[data-nav-open]');
  const drawer = document.getElementById('app-nav');
  const page = document.querySelectorAll<HTMLElement>('[data-page-content]');

  if (open) {
    root.dataset.nav = 'open';
  } else {
    delete root.dataset.nav;
  }

  button?.setAttribute('aria-expanded', String(open));
  page.forEach((node) => {
    node.inert = open;
  });

  if (open) {
    drawer?.querySelector<HTMLElement>('[aria-current="page"], a, button')?.focus();
  } else {
    button?.focus();
  }
}

let wired = false;

export function initNavDrawer(): void {
  if (wired) return;
  wired = true;

  document.addEventListener('click', (event) => {
    const target = event.target as HTMLElement;
    if (target.closest('[data-nav-open]')) {
      setOpen(!isOpen());
      return;
    }
    if (isOpen() && (target.closest('[data-nav-close]') || target.closest('#app-nav a'))) {
      setOpen(false);
    }
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && isOpen()) setOpen(false);
  });

  // Growing past the breakpoint closes the drawer, so it is never left open
  // behind a desktop layout.
  window.matchMedia('(min-width: 1000px)').addEventListener('change', (query) => {
    if (query.matches && isOpen()) setOpen(false);
  });
}

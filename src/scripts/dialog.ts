/**
 * Modal dialogs rendered by components/Dialog.astro.
 *
 * - `data-dialog-open="<id>"` on any button opens that dialog.
 * - `data-dialog-close` inside a dialog closes it.
 * - Escape and a click on the scrim close the open dialog.
 *
 * While a dialog is open, Tab and Shift+Tab cycle inside it, the page behind
 * it is inert, and closing it returns focus to whatever opened it.
 */

const FOCUSABLE = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

let openScrim: HTMLElement | null = null;
let returnFocus: HTMLElement | null = null;

const scrimFor = (id: string) => document.querySelector<HTMLElement>(`[data-dialog="${id}"]`);

const focusables = (root: HTMLElement) =>
  Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE)).filter((node) => node.offsetParent !== null);

const setBackgroundInert = (inert: boolean) => {
  document.querySelectorAll<HTMLElement>('[data-app-root]').forEach((node) => {
    node.inert = inert;
  });
};

export function openDialog(id: string, opener?: HTMLElement | null): void {
  const scrim = scrimFor(id);
  if (!scrim) return;

  // Moving from one dialog to the next (Capture → Use this photo) keeps the
  // original opener so focus still lands somewhere sensible at the end.
  if (openScrim && openScrim !== scrim) {
    openScrim.hidden = true;
  } else {
    returnFocus = opener ?? (document.activeElement as HTMLElement | null);
  }

  // Dialogs are authored inside the page content; lift them out to <body>
  // so the content can be made inert without taking the dialog with it.
  if (scrim.parentElement !== document.body) document.body.appendChild(scrim);

  scrim.hidden = false;
  openScrim = scrim;
  setBackgroundInert(true);

  const dialog = scrim.querySelector<HTMLElement>('[role="dialog"]');
  const target = dialog?.querySelector<HTMLElement>('[data-autofocus]') ?? (dialog ? focusables(dialog)[0] : null);
  (target ?? dialog)?.focus();
}

export function closeDialog(): void {
  if (!openScrim) return;
  openScrim.hidden = true;
  openScrim = null;
  setBackgroundInert(false);

  if (returnFocus?.isConnected) returnFocus.focus();
  returnFocus = null;
}

let wired = false;

/** Wires the declarative triggers once per page. Safe to call repeatedly. */
export function initDialogs(): void {
  if (wired) return;
  wired = true;

  document.addEventListener('click', (event) => {
    const target = event.target as HTMLElement;

    const opener = target.closest<HTMLElement>('[data-dialog-open]');
    if (opener && !(opener as HTMLButtonElement).disabled) {
      openDialog(opener.dataset.dialogOpen ?? '', opener);
      return;
    }

    if (target.closest('[data-dialog-close]')) {
      closeDialog();
      return;
    }

    if (openScrim && target === openScrim) closeDialog();
  });

  document.addEventListener('keydown', (event) => {
    if (!openScrim) return;

    if (event.key === 'Escape') {
      event.preventDefault();
      closeDialog();
      return;
    }

    if (event.key !== 'Tab') return;

    const dialog = openScrim.querySelector<HTMLElement>('[role="dialog"]');
    if (!dialog) return;
    const items = focusables(dialog);
    if (items.length === 0) {
      event.preventDefault();
      dialog.focus();
      return;
    }

    const first = items[0]!;
    const last = items[items.length - 1]!;
    const active = document.activeElement;

    if (event.shiftKey && (active === first || !dialog.contains(active))) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && (active === last || !dialog.contains(active))) {
      event.preventDefault();
      first.focus();
    }
  });
}

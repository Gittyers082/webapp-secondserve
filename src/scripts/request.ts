/**
 * Runs an API call for a button press: the button is disabled and marked
 * busy while the call is in flight, and a failure is shown on screen and
 * read out, with the page left as it was.
 */
import { errorMessage } from '../api/client';
import { announce } from './announce';

export function showError(message: string): void {
  const toast = document.querySelector<HTMLElement>('[data-toast]');
  if (toast) {
    toast.textContent = message;
    toast.hidden = false;
    window.clearTimeout(Number(toast.dataset.timer));
    toast.dataset.timer = String(window.setTimeout(() => (toast.hidden = true), 6000));
  }
  announce(message);
}

export async function run<T>(button: HTMLButtonElement | null, call: () => Promise<T>): Promise<T | undefined> {
  if (button) {
    button.disabled = true;
    button.setAttribute('aria-busy', 'true');
  }
  try {
    return await call();
  } catch (error) {
    showError(errorMessage(error));
    return undefined;
  } finally {
    if (button?.isConnected) {
      button.disabled = false;
      button.removeAttribute('aria-busy');
    }
  }
}

/**
 * Form handling while the frontend runs on seed data.
 *
 * Forms post nowhere yet. A form marked `data-demo-form` is intercepted on
 * submit so field values (passwords included) never end up in the address
 * bar. It then either moves to `data-next` or, without one, announces
 * `data-success` in place. Wiring a real server means replacing this module,
 * not the markup.
 */
import { announce } from './announce';

export function initDemoForms(): void {
  document.querySelectorAll<HTMLFormElement>('form[data-demo-form]').forEach((form) => {
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      if (!form.reportValidity()) return;

      const next = form.dataset.next;
      if (next) {
        window.location.assign(next);
        return;
      }

      const message = form.dataset.success ?? 'Saved.';
      const status = form.querySelector<HTMLElement>('[data-form-status]');
      if (status) {
        status.textContent = message;
        status.hidden = false;
      }
      announce(message);
    });
  });
}

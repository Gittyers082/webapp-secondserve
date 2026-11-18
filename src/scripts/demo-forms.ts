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
import { liveValidate, validate } from './validate';

export function initDemoForms(): void {
  document.querySelectorAll<HTMLFormElement>('form[data-demo-form]').forEach((form) => {
    liveValidate(form);
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      if (!validate(form)) return;

      // Immediate feedback while the next screen loads (NFR-USER-U-10).
      const submit = form.querySelector<HTMLButtonElement>('[type="submit"]');
      submit?.setAttribute('aria-busy', 'true');

      const next = form.dataset.next;
      if (next) {
        window.location.assign(next);
        return;
      }

      submit?.removeAttribute('aria-busy');
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

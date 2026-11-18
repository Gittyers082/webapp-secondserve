/**
 * Inline form validation (NFR-USER-U-8, NFR-USER-R-1).
 *
 * Every field that fails shows a plain-language message directly under it,
 * linked with aria-describedby, and the first one takes focus. Messages say
 * what is wrong and how to fix it. Fields re-check as the user types, so a
 * message clears as soon as it no longer applies.
 *
 * A field can set its own message with data-error="…"; otherwise one is
 * written from its label and the rule it broke.
 */

type Check = (field: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement) => string | null;

const label = (field: Element) =>
  (document.querySelector(`label[for="${field.id}"]`)?.textContent ?? 'This field')
    .replace(/\s*\(.*\)\s*$/, '')
    .trim();

const article = (word: string) => (/^[aeiou]/i.test(word) ? `an ${word}` : `a ${word}`);

/** Built-in rules, in the order they are checked. */
const rules: Check[] = [
  (field) => {
    if (!field.validity.valueMissing) return null;
    const name = label(field).toLowerCase();
    return field instanceof HTMLSelectElement ? `Choose ${article(name)}.` : `Enter ${article(name)}.`;
  },
  (field) => {
    // Checked by hand: browsers skip tooShort for values a script filled in.
    if (!(field instanceof HTMLInputElement) || field.minLength <= 0) return null;
    if (field.value === '' || field.value.length >= field.minLength) return null;
    return `${label(field)} must be at least ${field.minLength} characters. It has ${field.value.length}.`;
  },
  (field) => {
    if (!(field instanceof HTMLInputElement)) return null;
    if (field.validity.rangeUnderflow) return `${label(field)} must be ${field.min} or more.`;
    if (field.validity.rangeOverflow) return `${label(field)} must be ${field.max} or less.`;
    if (field.validity.badInput || field.validity.stepMismatch) return `Enter ${label(field).toLowerCase()} as a number.`;
    return null;
  },
  (field) => (field.validity.typeMismatch || field.validity.patternMismatch ? `Check the ${label(field).toLowerCase()}.` : null),
];

function messageFor(field: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement, extra?: Check): string | null {
  const custom = extra?.(field);
  if (custom) return custom;
  for (const rule of rules) {
    const message = rule(field);
    if (message) return field.dataset.error && field.validity.valueMissing ? field.dataset.error : message;
  }
  return null;
}

function errorNode(field: HTMLElement): HTMLElement {
  const id = `${field.id}-error`;
  let node = document.getElementById(id);
  if (!node) {
    node = document.createElement('p');
    node.id = id;
    node.className = 'field-error';
    node.hidden = true;
    field.insertAdjacentElement('afterend', node);
    const described = field.getAttribute('aria-describedby');
    field.setAttribute('aria-describedby', described ? `${id} ${described}` : id);
  }
  return node;
}

function show(field: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement, message: string | null): void {
  const node = errorNode(field);
  node.textContent = message ?? '';
  node.hidden = !message;
  field.setAttribute('aria-invalid', String(Boolean(message)));
}

export interface ValidateOptions {
  /** Extra rule per field, e.g. "discounted price below original". Return a message or null. */
  extra?: Check;
  /** Only check fields inside this element (one wizard step). */
  within?: HTMLElement;
}

/** Checks the form (or part of it); shows messages; focuses the first problem. */
export function validate(form: HTMLFormElement, options: ValidateOptions = {}): boolean {
  const scope = options.within ?? form;
  const fields = Array.from(scope.querySelectorAll<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>('input, textarea, select'))
    .filter((field) => field.id && field.type !== 'hidden' && !field.closest('[hidden]'));

  let first: HTMLElement | null = null;
  fields.forEach((field) => {
    const message = messageFor(field, options.extra);
    show(field, message);
    if (message && !first) first = field;
  });

  (first as HTMLElement | null)?.focus();
  return !first;
}

/** Re-checks a field as it changes, once it has shown an error. */
export function liveValidate(form: HTMLFormElement, extra?: Check): void {
  form.noValidate = true;
  form.addEventListener('input', (event) => {
    const field = event.target as HTMLInputElement;
    if (!field.id || field.getAttribute('aria-invalid') !== 'true') return;
    show(field, messageFor(field, extra));
  });
}

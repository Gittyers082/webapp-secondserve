/**
 * Light and dark themes.
 *
 * BaseLayout applies the saved choice in an inline script before the page
 * paints, so a reload never flashes the other theme. This module wires the
 * toggle buttons (`[data-theme-toggle]`) and keeps their state in step.
 */
import { announce } from './announce';

export type Theme = 'dark' | 'light';

const STORAGE_KEY = 'secondserve-theme';

export function currentTheme(): Theme {
  return document.documentElement.dataset.theme === 'light' ? 'light' : 'dark';
}

function save(theme: Theme): void {
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // Storage can be unavailable (private windows); the choice then lasts
    // for this page only.
  }
}

function syncToggles(theme: Theme): void {
  document.querySelectorAll<HTMLButtonElement>('[data-theme-toggle]').forEach((button) => {
    button.setAttribute('aria-pressed', String(theme === 'light'));
    button.title = theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode';
  });
}

export function setTheme(theme: Theme): void {
  const root = document.documentElement;
  // Switch every surface in one frame instead of letting each transition.
  root.classList.add('theme-switching');
  root.dataset.theme = theme;
  save(theme);
  syncToggles(theme);
  window.requestAnimationFrame(() => {
    window.requestAnimationFrame(() => root.classList.remove('theme-switching'));
  });
}

let wired = false;

export function initThemeToggles(): void {
  syncToggles(currentTheme());
  if (wired) return;
  wired = true;

  document.addEventListener('click', (event) => {
    const toggle = (event.target as HTMLElement).closest('[data-theme-toggle]');
    if (!toggle) return;
    const next: Theme = currentTheme() === 'light' ? 'dark' : 'light';
    setTheme(next);
    announce(next === 'light' ? 'Light mode on.' : 'Dark mode on.');
  });
}

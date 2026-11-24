/** Client-side role navigation and real account name, backed by GET /api/me. */
import { api } from '../api/client';
import { supabase } from '../api/supabase';
import type { BackendUser } from '../api/partner-data';
import type { Role } from '../data/types';

let accountPromise: Promise<BackendUser> | undefined;

export function currentAccount(): Promise<BackendUser> {
  accountPromise ??= api.account.me().catch((error: unknown) => {
    accountPromise = undefined;
    throw error;
  });
  return accountPromise;
}

export async function signOut(): Promise<void> {
  accountPromise = undefined;
  await supabase.auth.signOut();
  window.location.assign('/login');
}

const homeFor: Record<Role, string> = {
  buyer: '/buyer/shop', seller: '/seller', partner: '/partner', admin: '/admin',
};

export async function requireRole(role: Role): Promise<BackendUser> {
  const user = await currentAccount();
  if (user.status !== 'active') {
    throw { status: 403, message: 'Your account needs administrator approval before you can use this page.' };
  }
  if (user.role !== role) {
    window.location.replace(homeFor[user.role]);
    throw { status: 403, message: 'Redirecting to your account dashboard.' };
  }
  return user;
}

export function setAccountName(name: string): void {
  document.querySelectorAll<HTMLElement>('.sidebar .account-name, .profile .username')
    .forEach((element) => { element.textContent = name; });
  document.querySelectorAll<HTMLElement>('.sidebar .account .avatar, .profile .avatar')
    .forEach((element) => { element.textContent = name.charAt(0).toUpperCase(); });
  const usernameField = document.querySelector<HTMLInputElement>('#username-field');
  if (usernameField) usernameField.value = name;
}

export async function initAccountUi(): Promise<void> {
  const app = document.querySelector<HTMLElement>('[data-required-role]');
  if (!app) return;
  const required = app.dataset.requiredRole as Role;
  const loading = document.querySelector<HTMLElement>('[data-auth-loading]');
  const logout = document.querySelectorAll<HTMLAnchorElement>('.sidebar a.logout');
  logout.forEach((link) => link.addEventListener('click', (event) => {
    event.preventDefault();
    void signOut();
  }));

  try {
    const account = await requireRole(required);
    setAccountName(account.username);
    app.hidden = false;
    if (loading) loading.hidden = true;
  } catch (error) {
    const code = (error as { status?: number })?.status;
    if (code === 401) {
      window.location.replace('/login');
      return;
    }
    if (loading) {
      const message = (error as { message?: string })?.message;
      loading.textContent = message || 'Cannot load your account. Please refresh or sign in again.';
      if (!loading.querySelector('a')) {
        const link = document.createElement('a');
        link.href = '/login';
        link.textContent = ' Go to login';
        loading.append(link);
      }
    }
  }
}

import { api, errorMessage } from '../api/client';
import { currentAccount } from './account-ui';
import { announce } from './announce';
import { run } from './request';
import type { OrganizationType, PartnerProfile } from '../data/types';

export async function initPartnerProfile(): Promise<void> {
  const form = document.querySelector<HTMLFormElement>('[data-org-form]');
  const status = form?.querySelector<HTMLElement>('[data-org-status]');
  const loading = document.querySelector<HTMLElement>('[data-profile-loading]');
  const subtitle = document.querySelector<HTMLElement>('.section-sub');
  if (!form) return;
  const set = (name: string, value: string) => {
    const element = form.elements.namedItem(name) as HTMLInputElement | HTMLSelectElement | null;
    if (element) element.value = value;
  };
  const populate = (profile: PartnerProfile) => {
    set('organizationName', profile.organizationName);
    set('organizationType', profile.organizationType);
    set('contactPerson', profile.contactPerson);
    set('address', profile.address);
    set('accreditationUrl', profile.accreditationUrl ?? '');
    if (subtitle) subtitle.textContent = profile.verifiedAt
      ? `Verified by an administrator on ${new Date(profile.verifiedAt).toLocaleDateString('en-PH')}.`
      : 'Waiting for an administrator to verify your organization.';
  };

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    const data = new FormData(form);
    const text = (name: string) => String(data.get(name) ?? '').trim();
    const input = {
      organizationName: text('organizationName'),
      organizationType: text('organizationType') as OrganizationType,
      contactPerson: text('contactPerson'),
      address: text('address'),
      accreditationUrl: text('accreditationUrl') || null,
    };
    // Backend requires all four organization identity fields on a PATCH.
    const saved = await run(form.querySelector<HTMLButtonElement>('button[type="submit"]'), () =>
      api.partner.updateProfile(input));
    if (!saved) return;
    populate(saved);
    if (status) { status.textContent = 'Organization details saved.'; status.hidden = false; }
    announce('Organization details saved.');
  });

  try {
    const user = await currentAccount();
    if (user.role !== 'partner' || user.status !== 'active') return;
    const profile = await api.partner.profile();
    populate(profile);
    if (loading) loading.hidden = true;
    form.hidden = false;
  } catch (error) {
    if (loading) loading.textContent = `Cannot load organization details: ${errorMessage(error)}`;
  }
}

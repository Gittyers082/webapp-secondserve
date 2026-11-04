/** Tab bars for each role, in the order the wireframes show them. */

import type { Role } from './types';
import { cartItemCount, pendingOrders, handoverQueue, pendingAccounts, activeSessions } from './store';

export interface NavItem {
  label: string;
  href: string;
  /** Rendered as a lime pill after the label. */
  count?: number;
}

export const buyerNav: NavItem[] = [
  { label: 'Shop', href: '/buyer/shop' },
  { label: 'View Cart', href: '/buyer/cart', count: cartItemCount },
  { label: 'My Pending Orders', href: '/buyer/pending', count: pendingOrders.length },
  { label: 'My Order History', href: '/buyer/history' },
  { label: 'My Profile', href: '/buyer/profile' },
];

export const sellerNav: NavItem[] = [
  { label: 'Overview', href: '/seller' },
  { label: 'Add Listing', href: '/seller/add-listing' },
  { label: 'My Listed Items', href: '/seller/listed-items' },
  { label: 'Manage Listings', href: '/seller/manage' },
  { label: 'Reserved / Handover', href: '/seller/handover', count: handoverQueue.length },
  { label: 'My Profile', href: '/seller/profile' },
];

export const adminNav: NavItem[] = [
  { label: 'User Management', href: '/admin' },
  { label: 'Pending Approvals', href: '/admin/approvals', count: pendingAccounts.length },
  { label: 'Approved/Declined Users', href: '/admin/decisions' },
  { label: 'Item Moderation', href: '/admin/moderation' },
  { label: 'Active Sessions', href: '/admin/sessions', count: activeSessions.length },
];

export function navFor(role: Role): NavItem[] {
  if (role === 'buyer') return buyerNav;
  if (role === 'seller') return sellerNav;
  return adminNav;
}

export const roleLabel: Record<Role, string> = {
  buyer: 'Buyer',
  seller: 'Seller',
  admin: 'Administrator',
};

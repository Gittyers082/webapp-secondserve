/** Tab bars for each role, in the order the wireframes show them. */

import type { Role } from './types';
import type { IconName } from './icons';
import { cartItemCount, pendingOrders, handoverQueue, pendingAccounts, activeSessions } from './store';

export interface NavItem {
  label: string;
  href: string;
  icon: IconName;
  /** Rendered as a lime pill after the label. */
  count?: number;
}

export const buyerNav: NavItem[] = [
  { label: 'Shop', href: '/buyer/shop', icon: 'bag' },
  { label: 'View Cart', href: '/buyer/cart', icon: 'cart', count: cartItemCount },
  { label: 'My Pending Orders', href: '/buyer/pending', icon: 'clock', count: pendingOrders.length },
  { label: 'My Order History', href: '/buyer/history', icon: 'receipt' },
  { label: 'My Profile', href: '/buyer/profile', icon: 'user' },
];

export const sellerNav: NavItem[] = [
  { label: 'Overview', href: '/seller', icon: 'grid' },
  { label: 'Add Listing', href: '/seller/add-listing', icon: 'plus' },
  { label: 'My Listed Items', href: '/seller/listed-items', icon: 'shelf' },
  { label: 'Manage Listings', href: '/seller/manage', icon: 'sliders' },
  { label: 'Reserved / Handover', href: '/seller/handover', icon: 'handover', count: handoverQueue.length },
  { label: 'My Profile', href: '/seller/profile', icon: 'user' },
];

export const adminNav: NavItem[] = [
  { label: 'User Management', href: '/admin', icon: 'users' },
  { label: 'Pending Approvals', href: '/admin/approvals', icon: 'user-check', count: pendingAccounts.length },
  { label: 'Approved/Declined Users', href: '/admin/decisions', icon: 'list-check' },
  { label: 'Item Moderation', href: '/admin/moderation', icon: 'flag' },
  { label: 'Active Sessions', href: '/admin/sessions', icon: 'pulse', count: activeSessions.length },
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

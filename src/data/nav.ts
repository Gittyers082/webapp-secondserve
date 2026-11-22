/** Sidebar items for each role. */

import type { Role } from './types';
import type { IconName } from './icons';
import {
  activeSessions,
  adminNotifications,
  buyerNotifications,
  cartItemCount,
  handoverQueue,
  partnerNotifications,
  pendingAccounts,
  pendingOrders,
  savedListingIds,
  sellerNotifications,
  surplusBoard,
  undistributedOrders,
  unreadCount,
} from './store';

export interface NavItem {
  label: string;
  href: string;
  icon: IconName;
  /** Rendered as a lime pill after the label. */
  count?: number;
  /** What the count counts, read out after it: "3 unread". */
  countNoun?: string;
}

export const buyerNav: NavItem[] = [
  { label: 'Shop', href: '/buyer/shop', icon: 'bag' },
  { label: 'Wishlist', href: '/buyer/wishlist', icon: 'heart', count: savedListingIds.length, countNoun: 'saved' },
  { label: 'View Cart', href: '/buyer/cart', icon: 'cart', count: cartItemCount, countNoun: 'in cart' },
  { label: 'My Pending Orders', href: '/buyer/pending', icon: 'clock', count: pendingOrders.length },
  { label: 'My Order History', href: '/buyer/history', icon: 'receipt' },
  { label: 'Notifications', href: '/buyer/notifications', icon: 'bell', count: unreadCount(buyerNotifications), countNoun: 'unread' },
  { label: 'My Profile', href: '/buyer/profile', icon: 'user' },
  { label: 'Help & FAQ', href: '/buyer/help', icon: 'help' },
];

export const sellerNav: NavItem[] = [
  { label: 'Overview', href: '/seller', icon: 'grid' },
  { label: 'Analytics', href: '/seller/analytics', icon: 'chart' },
  { label: 'Add Listing', href: '/seller/add-listing', icon: 'plus' },
  { label: 'My Listed Items', href: '/seller/listed-items', icon: 'shelf' },
  { label: 'Manage Listings', href: '/seller/manage', icon: 'sliders' },
  { label: 'Reserved / Handover', href: '/seller/handover', icon: 'handover', count: handoverQueue.length },
  { label: 'Shop Profile', href: '/seller/shop-profile', icon: 'store' },
  { label: 'Reviews', href: '/seller/reviews', icon: 'star' },
  { label: 'Notifications', href: '/seller/notifications', icon: 'bell', count: unreadCount(sellerNotifications), countNoun: 'unread' },
  { label: 'My Profile', href: '/seller/profile', icon: 'user' },
  { label: 'Help & FAQ', href: '/seller/help', icon: 'help' },
];

export const partnerNav: NavItem[] = [
  { label: 'Surplus Board', href: '/partner', icon: 'bag', count: surplusBoard.length, countNoun: 'available' },
  { label: 'My Orders', href: '/partner/orders', icon: 'receipt', count: undistributedOrders.length, countNoun: 'to distribute' },
  { label: 'Notifications', href: '/partner/notifications', icon: 'bell', count: unreadCount(partnerNotifications), countNoun: 'unread' },
  { label: 'Organization Profile', href: '/partner/profile', icon: 'store' },
  { label: 'Help & FAQ', href: '/partner/help', icon: 'help' },
];

export const adminNav: NavItem[] = [
  { label: 'User Management', href: '/admin', icon: 'users' },
  { label: 'Pending Approvals', href: '/admin/approvals', icon: 'user-check', count: pendingAccounts.length },
  { label: 'Approved/Declined Users', href: '/admin/decisions', icon: 'list-check' },
  { label: 'Item Moderation', href: '/admin/moderation', icon: 'flag' },
  { label: 'Active Sessions', href: '/admin/sessions', icon: 'pulse', count: activeSessions.length, countNoun: 'online' },
  { label: 'Notifications', href: '/admin/notifications', icon: 'bell', count: unreadCount(adminNotifications), countNoun: 'unread' },
  { label: 'Help & FAQ', href: '/admin/help', icon: 'help' },
];

export function navFor(role: Role): NavItem[] {
  if (role === 'buyer') return buyerNav;
  if (role === 'seller') return sellerNav;
  if (role === 'partner') return partnerNav;
  return adminNav;
}

export const roleLabel: Record<Role, string> = {
  buyer: 'Buyer',
  seller: 'Seller',
  partner: 'Partner',
  admin: 'Administrator',
};

/** Where each role's notification centre lives. */
export const notificationsHref: Record<Role, string> = {
  buyer: '/buyer/notifications',
  seller: '/seller/notifications',
  partner: '/partner/notifications',
  admin: '/admin/notifications',
};

export const notificationsFor: Record<Role, typeof buyerNotifications> = {
  buyer: buyerNotifications,
  seller: sellerNotifications,
  partner: partnerNotifications,
  admin: adminNotifications,
};

/**
 * SecondServe domain model.
 *
 * Mirrors the entity diagram in the wireframes: users own listings,
 * listings produce orders, and both sides of an order can see it.
 */

export type Role = 'buyer' | 'seller' | 'admin';

export type UserStatus = 'active' | 'banned';

export type ListingStatus = 'active' | 'sold' | 'withdrawn' | 'expired';

export type OrderStatus = 'reserved' | 'ready' | 'picked-up';

export type ApprovalDecision = 'pending' | 'approved' | 'declined';

export type FoodCategory = 'bread' | 'pastries' | 'savory' | 'cakes' | 'fruit-cups';

/** Keys of the illustrated food artwork bundled with the app. */
export type FoodArt =
  | 'pandesal-ube'
  | 'pandesal-plain'
  | 'croissant'
  | 'empanada'
  | 'strawberry-cup'
  | 'cake-slice'
  | 'cheese-roll'
  | 'monay'
  | 'ensaymada'
  | 'mystery';

export interface User {
  id: string;
  username: string;
  role: Role;
  status: UserStatus;
  /** Only sellers carry a shop name. */
  shopName?: string;
}

export interface Listing {
  id: string;
  sellerId: string;
  shopName: string;
  name: string;
  description: string;
  category: FoodCategory;
  art: FoodArt;
  originalPrice: number;
  discountedPrice: number;
  quantity: number;
  /** Set once some of the stock has gone; used for the "0 of 7 left" label. */
  originalQuantity?: number;
  expiresAt: string;
  expiryLabel: string;
  pickupLocation: string;
  status: ListingStatus;
  /** How many units are currently held by reservations. */
  reserved?: number;
  flagged?: boolean;
}

export interface Order {
  id: string;
  listingId: string;
  buyerUsername: string;
  foodName: string;
  art: FoodArt;
  shopName: string;
  quantity: number;
  total: number;
  pickupLocation: string;
  expiryLabel: string;
  expiringSoon: boolean;
  status: OrderStatus;
  /** Present once the order has been collected. */
  pickedUpAt?: string;
}

export interface CartLine {
  listingId: string;
  shopName: string;
  pickupLocation: string;
  foodName: string;
  art: FoodArt;
  quantity: number;
  unitPrice: number;
  originalUnitPrice: number;
  expiryLabel: string;
  expiringSoon: boolean;
}

export interface PendingAccount {
  id: string;
  username: string;
  role: Exclude<Role, 'admin'>;
  shopName?: string;
  requestedAt: string;
  decision: ApprovalDecision;
}

export interface AccountDecision {
  id: string;
  username: string;
  role: Exclude<Role, 'admin'>;
  shopName?: string;
  decision: Exclude<ApprovalDecision, 'pending'>;
  decidedAt: string;
}

export interface Session {
  username: string;
  role: Role;
  connectedSince: string;
  clientAddress: string;
}

/** Formats a peso amount the way every screen in the wireframes does. */
export function peso(amount: number): string {
  return `₱${amount.toFixed(2)}`;
}

/** Percentage knocked off the original price, rounded to a whole number. */
export function discountPercent(listing: Pick<Listing, 'originalPrice' | 'discountedPrice'>): number {
  if (listing.originalPrice <= 0) return 0;
  return Math.round((1 - listing.discountedPrice / listing.originalPrice) * 100);
}

/**
 * SecondServe domain model.
 *
 * Mirrors the entity diagram in the wireframes: users own listings,
 * listings produce orders, and both sides of an order can see it.
 */

export type Role = 'buyer' | 'seller' | 'partner' | 'admin';

/** Roles a person can sign up for; administrators are created by the team. */
export type SignupRole = Exclude<Role, 'admin'>;

export type UserStatus = 'active' | 'banned';

export type ListingStatus = 'active' | 'sold' | 'withdrawn' | 'expired';

export type OrderStatus = 'reserved' | 'ready' | 'picked-up' | 'delivered' | 'cancelled';

/** How an order reaches the buyer or partner. */
export type FulfillmentType = 'pickup' | 'delivery';

/** Where a delivery order is, set by the (simulated) courier. */
export type DeliveryStatus = 'pending' | 'preparing' | 'out-for-delivery' | 'delivered' | 'cancelled';

/** A buyer's purchase, a partner's surplus purchase, or a free donation claim. */
export type OrderType = 'sale' | 'partner-purchase' | 'donation';

/** Where a listing is shown: the marketplace, or the partners' Surplus Board. */
export type ListingChannel = 'marketplace' | 'partner-offer' | 'donation';

/** Whether a partner has handed its food on to the people it serves. */
export type DistributionStatus = 'pending' | 'distributed';

/** Kinds of organization that can register as a partner. */
export type OrganizationType = 'lgu' | 'government-agency' | 'charity' | 'shelter';

export type ApprovalDecision = 'pending' | 'approved' | 'declined';

export type FoodCategory = 'bread' | 'pastries' | 'savory' | 'cakes' | 'fruit-cups' | 'groceries' | 'other';

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
  /** Only partners carry an organization name. */
  organizationName?: string;
}

/** What a partner organization tells SecondServe about itself. */
export interface PartnerProfile {
  organizationName: string;
  organizationType: OrganizationType;
  contactPerson: string;
  address: string;
  /** Link to the accreditation or registration document, if given. */
  accreditationUrl?: string;
  /** Set once an administrator has approved the organization. */
  verifiedAt?: string;
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
  /** Fulfillment options; pickup only when omitted. */
  allowsPickup?: boolean;
  allowsDelivery?: boolean;
  /** Set when delivery is offered; 0 means free delivery. */
  deliveryFee?: number;
  /** Marketplace when omitted. */
  channel?: ListingChannel;
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
  /** A sale when omitted. */
  orderType?: OrderType;
  /** Pickup when omitted. */
  fulfillmentType?: FulfillmentType;
  deliveryAddress?: string;
  deliveryFee?: number;
  deliveryStatus?: DeliveryStatus;
  /** Partner orders only. */
  distributionStatus?: DistributionStatus;
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
  role: SignupRole;
  shopName?: string;
  organizationName?: string;
  requestedAt: string;
  decision: ApprovalDecision;
}

export interface AccountDecision {
  id: string;
  username: string;
  role: SignupRole;
  shopName?: string;
  organizationName?: string;
  decision: Exclude<ApprovalDecision, 'pending'>;
  decidedAt: string;
}

export interface Session {
  username: string;
  role: Role;
  connectedSince: string;
  clientAddress: string;
}

/** Readable names for each organization type. */
export const organizationTypeLabel: Record<OrganizationType, string> = {
  lgu: 'Local government unit',
  'government-agency': 'Government agency',
  charity: 'Charity',
  shelter: 'Shelter',
};

/** Formats a peso amount the way every screen in the wireframes does. */
export function peso(amount: number): string {
  return `₱${amount.toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/** Percentage knocked off the original price, rounded to a whole number. */
export function discountPercent(listing: Pick<Listing, 'originalPrice' | 'discountedPrice'>): number {
  if (listing.originalPrice <= 0) return 0;
  return Math.round((1 - listing.discountedPrice / listing.originalPrice) * 100);
}

/** A buyer's rating of a shop after collecting an order. */
export interface Review {
  id: string;
  listingId: string;
  shopName: string;
  foodName: string;
  author: string;
  /** Whole stars, 1 to 5. */
  rating: number;
  comment: string;
  date: string;
  /** The order it was written for, so a buyer reviews each order once. */
  orderId?: string;
}

export type NotificationKind = 'order' | 'listing' | 'account' | 'review';

export interface AppNotification {
  id: string;
  kind: NotificationKind;
  title: string;
  body: string;
  time: string;
  read: boolean;
  /** Where the notification leads when opened. */
  href?: string;
}

/** One completed sale, the unit seller analytics is computed from. */
export interface SaleRecord {
  date: string;
  /** Short day label for charts, e.g. "Mon 2". */
  day: string;
  listingName: string;
  category: FoodCategory;
  quantity: number;
  total: number;
  /** What the same food would have cost at full price. */
  fullPrice: number;
}

export interface FaqEntry {
  question: string;
  answer: string;
  /** Which roles see it; omit for everyone. */
  roles?: Role[];
}

/** Average of a set of 1-5 ratings, to one decimal place. */
export function averageRating(ratings: number[]): number {
  if (ratings.length === 0) return 0;
  return Math.round((ratings.reduce((sum, value) => sum + value, 0) / ratings.length) * 10) / 10;
}

/** Tags a shop can show on its public profile. */
export const shopTags = [
  'Bread',
  'Pastries',
  'Savory',
  'Cakes',
  'Fruit cups',
  'Filipino classics',
  'Coffee shop',
  'Vegetarian options',
] as const;

export type ShopTag = (typeof shopTags)[number];

/** What buyers see about a shop (NFR-USER-PERS-3). */
export interface ShopProfile {
  shopName: string;
  description: string;
  tags: ShopTag[];
  /** URL of the uploaded logo; without one the shop's initials are shown. */
  logoUrl?: string;
  location: string;
}

/** Up to two initials for a shop with no logo: "Mang Ben's Bakery" → "MB". */
export function shopInitials(name: string): string {
  return name
    .replace(/[^A-Za-z\s]/g, '')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0]!.toUpperCase())
    .join('');
}

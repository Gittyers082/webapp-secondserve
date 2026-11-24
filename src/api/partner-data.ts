/** The backend responds with camelCase JSON, but its shapes differ from the UI models. */
import type { FoodArt, FoodCategory, Listing, Order, PartnerProfile, ShopProfile } from '../data/types';

const validArt = new Set<string>([
  'pandesal-ube', 'pandesal-plain', 'croissant', 'empanada', 'strawberry-cup',
  'cake-slice', 'cheese-roll', 'monay', 'ensaymada', 'mystery',
]);
const validCategories = new Set<string>(['bread', 'pastries', 'savory', 'cakes', 'fruit-cups', 'groceries', 'other']);

const asMoney = (value: string | number | null | undefined): number => {
  const parsed = Number(value ?? 0);
  return Number.isFinite(parsed) ? parsed : 0;
};

const foodArt = (art: string | null | undefined): FoodArt =>
  art && validArt.has(art) ? art as FoodArt : 'mystery';

const expiryLabel = (iso: string) => {
  const date = new Date(iso);
  return Number.isNaN(date.valueOf())
    ? 'Unknown'
    : new Intl.DateTimeFormat('en-PH', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }).format(date);
};

export interface BackendListing {
  id: string;
  sellerId: string;
  shopName: string;
  name: string;
  description: string;
  category: string;
  art: string | null;
  imageUrl?: string | null;
  originalPrice: string | number;
  discountedPrice: string | number;
  quantity: number;
  originalQuantity?: number;
  expiresAt: string;
  pickupLocation: string;
  status: string;
  allowsPickup: boolean;
  allowsDelivery: boolean;
  deliveryFee: string | number | null;
  channel: string;
  flagged?: boolean;
}

export interface BackendOrder {
  id: string;
  listingId: string;
  foodName: string;
  shopName: string;
  art: string | null;
  imageUrl?: string | null;
  quantity: number;
  total: string | number;
  pickupLocation: string;
  expiresAt: string;
  status: string;
  orderType: string;
  fulfillmentType: string;
  deliveryAddress: string | null;
  deliveryFee: string | number | null;
  deliveryStatus: string | null;
  distributionStatus: string | null;
  pickedUpAt?: string | null;
}

export interface BackendUser {
  id: string;
  email: string;
  username: string;
  fullName: string;
  role: 'buyer' | 'seller' | 'partner' | 'admin';
  status: 'active' | 'pending' | 'declined' | 'banned';
  partnerProfile?: PartnerProfile | null;
  sellerProfile?: {
    businessName: string;
    businessType: string;
    businessAddress: string;
    contactPhone: string;
    description: string | null;
    logoUrl: string | null;
  } | null;
}

export function listingFromBackend(data: BackendListing): Listing {
  return {
    id: data.id,
    sellerId: data.sellerId,
    shopName: data.shopName,
    name: data.name,
    description: data.description,
    category: validCategories.has(data.category) ? data.category as FoodCategory : 'savory',
    art: foodArt(data.art),
    originalPrice: asMoney(data.originalPrice),
    discountedPrice: asMoney(data.discountedPrice),
    quantity: data.quantity,
    originalQuantity: data.originalQuantity,
    expiresAt: data.expiresAt,
    expiryLabel: expiryLabel(data.expiresAt),
    pickupLocation: data.pickupLocation,
    status: data.status === 'sold-out' ? 'sold' : data.status === 'active' ? 'active' : 'expired',
    allowsPickup: data.allowsPickup,
    allowsDelivery: data.allowsDelivery,
    deliveryFee: data.deliveryFee == null ? undefined : asMoney(data.deliveryFee),
    channel: data.channel === 'donation' ? 'donation' : data.channel === 'partner-offer' ? 'partner-offer' : 'marketplace',
    flagged: data.flagged,
  };
}

export function orderFromBackend(data: BackendOrder): Order {
  return {
    id: data.id,
    listingId: data.listingId,
    buyerUsername: '',
    foodName: data.foodName,
    shopName: data.shopName,
    art: foodArt(data.art),
    quantity: data.quantity,
    total: asMoney(data.total),
    pickupLocation: data.pickupLocation,
    expiryLabel: expiryLabel(data.expiresAt),
    expiringSoon: Date.parse(data.expiresAt) - Date.now() < 24 * 60 * 60 * 1000,
    status: data.status === 'picked-up' || data.status === 'delivered' || data.status === 'cancelled' ? data.status : data.status === 'ready' ? 'ready' : 'reserved',
    orderType: data.orderType === 'donation' ? 'donation' : data.orderType === 'partner-purchase' ? 'partner-purchase' : 'sale',
    fulfillmentType: data.fulfillmentType === 'delivery' ? 'delivery' : 'pickup',
    deliveryAddress: data.deliveryAddress ?? undefined,
    deliveryFee: data.deliveryFee == null ? undefined : asMoney(data.deliveryFee),
    deliveryStatus: data.deliveryStatus as Order['deliveryStatus'] ?? undefined,
    distributionStatus: data.distributionStatus === 'distributed' ? 'distributed' : 'pending',
    pickedUpAt: data.pickedUpAt ?? undefined,
  };
}

export function partnerProfileFromUser(data: BackendUser): PartnerProfile {
  if (data.role !== 'partner' || !data.partnerProfile) {
    throw { status: 403, message: 'No organization profile was found on this account.' };
  }
  return data.partnerProfile;
}

export function shopProfileFromUser(data: BackendUser): ShopProfile {
  const profile = data.sellerProfile;
  if (data.role !== 'seller' || !profile) {
    throw { status: 403, message: 'No seller profile found on this account.' };
  }
  return {
    shopName: profile.businessName,
    description: profile.description ?? '',
    location: profile.businessAddress,
    tags: [], // Shop tags have no matching field in the current backend schema.
    logoUrl: profile.logoUrl ?? undefined,
  };
}

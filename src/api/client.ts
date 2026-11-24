/**
 * The API client every screen uses to change data.
 *
 * With PUBLIC_API_BASE_URL set (in .env, e.g. http://localhost:8000/api),
 * calls go to the server as JSON over fetch. Without it, they resolve against
 * the seed data in src/data/store.ts, so the frontend stays usable before the
 * backend exists. The screens never know which one answered.
 */
import type {
  ApiError,
  BuyerPreferences,
  ListingInput,
  PartnerOrderInput,
  ReviewInput,
} from "./contract";
import type {
  AccountDecision,
  AppNotification,
  Listing,
  Order,
  PartnerProfile,
  PendingAccount,
  Review,
  Session,
  ShopProfile,
  User,
} from "../data/types";
import * as seed from "../data/store";
import { supabase } from './supabase';
import {
  listingFromBackend, orderFromBackend, partnerProfileFromUser, shopProfileFromUser,
  type BackendListing, type BackendOrder, type BackendUser,
} from './partner-data';

const BASE_URL = (import.meta.env.PUBLIC_API_BASE_URL as string | undefined)?.replace(/\/+$/, '');
const API_BASE = BASE_URL ? (BASE_URL.endsWith('/api') ? BASE_URL : `${BASE_URL}/api`) : undefined;

/** True when the client talks to a real server. */
export const isLive = Boolean(BASE_URL);

async function tokenHeaders(extra: Record<string, string> = {}): Promise<Record<string, string>> {
  const { data, error } = await supabase.auth.getSession();
  if (error || !data.session?.access_token) {
    throw { status: 401, message: 'Please sign in first.' } satisfies ApiError;
  }
  return { ...extra, Authorization: `Bearer ${data.session.access_token}` };
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  if (!API_BASE) {
    throw { status: 0, message: 'Backend API URL is missing.' } satisfies ApiError;
  }
  const headers = await tokenHeaders(body === undefined ? {} : { 'Content-Type': 'application/json' });
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw { status: 0, message: 'Could not connect to the backend.' } satisfies ApiError;
  }
    if (!response.ok) {
    let message = response.statusText || `HTTP ${response.status}`;

    try {
      const body = (await response.json()) as {
        detail?: unknown;
        message?: string;
      };

      message = readDetail(body.detail) ?? body.message ?? message;
    } catch {
      // Not JSON; keep the status message.
    }

    throw { status: response.status, message } satisfies ApiError;
  }

  return response.status === 204
    ? null as T
    : await response.json() as T;
}

/**
 * FastAPI puts the error in `detail`: a sentence for most errors ("That username is
 * already taken."), or a list of field problems for validation errors (422).
 */
function readDetail(detail: unknown): string | undefined {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const problems = detail
      .map((item) =>
        typeof item === "string" ? item : (item as { msg?: string })?.msg,
      )
      .filter((text): text is string => Boolean(text))
      // Pydantic prefixes model-level errors with "Value error, ".
      .map((text) => text.replace(/^Value error, /, ""));
    return problems.length ? problems.join(" ") : undefined;
  }
  return undefined;
}

/** Seed fallback: answers after a short delay, like a real round trip. */
function offline<T>(value: T): Promise<T> {
  return new Promise((resolve) => window.setTimeout(() => resolve(value), 120));
}

function find<T extends { id: string }>(items: T[], id: string): T {
  const item = items.find((candidate) => candidate.id === id);
  if (!item) throw { status: 404, message: "Not found" } satisfies ApiError;
  return item;
}

export const api = {
  account: {
    me: () => request<BackendUser>('GET', '/me'),
  },

  seller: {
    listings: () =>
      isLive
        ? request<Listing[]>("GET", "/listings/mine")
        : offline(seed.sellerListings),

    createListing: (input: ListingInput) =>
      isLive
        ? request<Listing>("POST", "/listings", input)
        : offline({
            ...seed.sellerListings[0]!,
            ...input,
            id: `l-${Date.now()}`,
            status: "active",
          } as Listing),

    updateListing: (id: string, input: Partial<ListingInput>) =>
      isLive
        ? request<Listing>("PATCH", `/listings/${id}`, input)
        : offline({ ...find(seed.sellerListings, id), ...input } as Listing),

    setStatus: (id: string, status: "sold" | "withdrawn") =>
      isLive
        ? request<Listing>("POST", `/listings/${id}/status`, { status })
        : offline({ ...find(seed.sellerListings, id), status }),

    deleteListing: (id: string) =>
      isLive
        ? request<null>("DELETE", `/listings/${id}`)
        : offline(null),

    orders: () =>
      isLive
        ? request<Order[]>("GET", "/orders/mine")
        : offline(seed.handoverQueue),

    markReady: (orderId: string) =>
      isLive
        ? request<Order>("POST", `/orders/${orderId}/ready`)
        : offline({
            ...find(seed.handoverQueue, orderId),
            status: "ready",
          } as Order),

    // TODO(Role 1): the backend has no seller reviews route yet.
    reviews: () =>
      isLive
        ? request<Review[]>("GET", "/seller/reviews")
        : offline(seed.reviews),

    profile: async (): Promise<ShopProfile> =>
      isLive ? shopProfileFromUser(await request<BackendUser>('GET', '/me')) : offline(seed.sellerProfile),

    updateProfile: async (input: Partial<Omit<ShopProfile, 'logoUrl'>>): Promise<ShopProfile> => {
      if (!isLive) return offline({ ...seed.sellerProfile, ...input });
      const user = await request<BackendUser>('GET', '/me');
      const existing = user.sellerProfile;
      if (user.role !== 'seller' || !existing) {
        throw { status: 403, message: 'Seller profile was not found.' } satisfies ApiError;
      }
      // PATCH /me uses SellerDetails, which requires all identity fields.
      const updated = await request<BackendUser>('PATCH', '/me', {
        seller: {
          businessName: input.shopName ?? existing.businessName,
          businessType: existing.businessType,
          businessAddress: input.location ?? existing.businessAddress,
          contactPhone: existing.contactPhone,
          description: input.description ?? existing.description,
        },
      });
      return shopProfileFromUser(updated);
    },

    uploadLogo: async (file: File): Promise<{ logoUrl: string }> => {
      if (!isLive) return offline({ logoUrl: URL.createObjectURL(file) });
      const body = new FormData();
      body.append("file", file);
      const response = await fetch(`${API_BASE}/me/logo`, {
        method: "POST",
        headers: await tokenHeaders(),
        body,
      });
      if (!response.ok)
        throw {
          status: response.status,
          message: response.statusText,
        } satisfies ApiError;
      return (await response.json()) as { logoUrl: string };
    },
  },

  buyer: {
    preferences: () =>
      isLive
        ? request<BuyerPreferences>("GET", "/me/preferences")
        : offline<BuyerPreferences>({
            favouriteCategories: ["bread", "pastries"],
            minPrice: null,
            maxPrice: "100",
            deliveryOnly: false,
          }),

    savePreferences: (input: BuyerPreferences) =>
      isLive
        ? request<BuyerPreferences>("PUT", "/me/preferences", input)
        : offline(input),

    recommendations: async (): Promise<Listing[]> =>
      isLive
        ? (await request<BackendListing[]>('GET', '/me/recommendations')).map(listingFromBackend)
        : offline(seed.listings.filter((listing) => listing.status === 'active').slice(0, 4)),

    review: (input: ReviewInput) =>
      isLive
        ? request<Review>("POST", `/orders/${input.orderId}/review`, {
            rating: input.rating,
            comment: input.comment,
          })
        : offline({
            id: `r-${Date.now()}`,
            listingId: "",
            shopName: "",
            foodName: "",
            author: seed.buyer.username,
            date: "Today",
            ...input,
          } as Review),
  },

  partner: {
    // Render all pages of results, not just the backend's first 24 offers.
    surplus: async (): Promise<Listing[]> => {
      if (!isLive) return offline(seed.surplusBoard);
      const listings: Listing[] = [];
      for (let offset = 0; ; offset += 100) {
        const page = await request<{ items: BackendListing[]; total: number }>(
          'GET', `/partners/surplus?limit=100&offset=${offset}`,
        );
        listings.push(...page.items.map(listingFromBackend));
        if (page.items.length === 0 || listings.length >= page.total) break;
      }
      return listings;
    },

    orders: async (): Promise<Order[]> =>
      isLive
        ? (await request<BackendOrder[]>('GET', '/partners/orders')).map(orderFromBackend)
        : offline(seed.partnerOrders),

    buy: async (listingId: string, input: PartnerOrderInput): Promise<Order> =>
      isLive
        ? orderFromBackend(await request<BackendOrder>('POST', `/partners/surplus/${encodeURIComponent(listingId)}/buy`, input))
        : offline(partnerOrderFromSeed(listingId, input, 'partner-purchase')),

    claim: async (listingId: string, input: PartnerOrderInput): Promise<Order> =>
      isLive
        ? orderFromBackend(await request<BackendOrder>('POST', `/partners/surplus/${encodeURIComponent(listingId)}/claim`, input))
        : offline(partnerOrderFromSeed(listingId, input, 'donation')),

    markDistributed: async (orderId: string): Promise<Order> =>
      isLive
        ? orderFromBackend(await request<BackendOrder>('POST', `/partners/orders/${encodeURIComponent(orderId)}/distributed`))
        : offline({ ...find(seed.partnerOrders, orderId), distributionStatus: 'distributed' } as Order),

    profile: async (): Promise<PartnerProfile> =>
      isLive
        ? partnerProfileFromUser(await request<BackendUser>('GET', '/me'))
        : offline(seed.partnerProfile),

    updateProfile: async (input: Partial<Omit<PartnerProfile, 'verifiedAt' | 'accreditationUrl'>> & { accreditationUrl?: string | null }): Promise<PartnerProfile> =>
      isLive
        ? partnerProfileFromUser(await request<BackendUser>('PATCH', '/me', { partner: input }))
        : offline({ ...seed.partnerProfile, ...input, accreditationUrl: input.accreditationUrl ?? undefined }),
  },

  admin: {
    users: () =>
      isLive ? request<User[]>("GET", "/admin/users") : offline(seed.users),

    setBanned: (userId: string, banned: boolean) =>
      isLive
        ? request<User>(
            "POST",
            `/admin/users/${encodeURIComponent(userId)}/${banned ? "ban" : "unban"}`,
          )
        : offline({
            ...seed.users.find((user) => user.id === userId)!,
            status: banned ? "banned" : "active",
          } as User),

    approvals: () =>
      isLive
        ? request<PendingAccount[]>("GET", "/admin/approvals")
        : offline(seed.pendingAccounts),

    // Note: the backend returns the updated User here, not an AccountDecision.
    decide: (id: string, decision: "approved" | "declined") =>
      isLive
        ? request<AccountDecision>("POST", `/admin/approvals/${id}`, {
            decision,
          })
        : offline({
            ...find(seed.pendingAccounts, id),
            decision,
            decidedAt: "Just now",
          } as AccountDecision),

    // TODO(Role 1): the backend has no listing moderation or sessions routes yet.
    flagListing: (id: string) =>
      isLive
        ? request<Listing>("POST", `/admin/listings/${id}/flag`)
        : offline({ ...find(seed.moderatedListings, id), flagged: true }),

    removeListing: (id: string) =>
      isLive ? request<null>("DELETE", `/admin/listings/${id}`) : offline(null),

    sessions: () =>
      isLive
        ? request<Session[]>("GET", "/admin/sessions")
        : offline(seed.activeSessions),
  },

  notifications: {
    list: (fallback: AppNotification[]) =>
      isLive
        ? request<AppNotification[]>("GET", "/notifications")
        : offline(fallback),
    markRead: (id: string) =>
      isLive
        ? request<null>("POST", `/notifications/${id}/read`)
        : offline(null),
    markAllRead: () =>
      isLive ? request<null>("POST", "/notifications/read-all") : offline(null),
  },
};

/** What the seed fallback answers when a partner buys or claims surplus. */
function partnerOrderFromSeed(
  listingId: string,
  input: PartnerOrderInput,
  orderType: "partner-purchase" | "donation",
): Order {
  const listing = find(seed.surplusBoard, listingId);
  const delivery = input.fulfillmentType === "delivery";
  const deliveryFee = delivery ? (listing.deliveryFee ?? 0) : undefined;
  return {
    id: `o-${Date.now()}`,
    listingId,
    buyerUsername: seed.partner.username,
    foodName: listing.name,
    art: listing.art,
    shopName: listing.shopName,
    quantity: input.quantity,
    total: orderType === "donation" ? 0 : listing.discountedPrice * input.quantity,
    pickupLocation: listing.pickupLocation,
    expiryLabel: listing.expiryLabel,
    expiringSoon: false,
    status: "reserved",
    orderType,
    fulfillmentType: input.fulfillmentType,
    deliveryAddress: delivery ? input.deliveryAddress : undefined,
    deliveryFee,
    deliveryStatus: delivery ? "pending" : undefined,
    distributionStatus: "pending",
  };
}

/** A readable message for a failed call, for notices and announcements. */
export function errorMessage(error: unknown): string {
  const apiError = error as Partial<ApiError>;
  if (apiError?.status === 0 || error instanceof TypeError) {
    return "Could not reach the Hapag server. Check that this computer is online, then try again.";
  }
  switch (apiError?.status) {
    case 401:
      return "Your session has ended. Sign in again to continue.";
    case 403:
      return "Your account cannot do this. Ask an administrator if you think it should.";
    case 404:
      return "This item no longer exists. Refresh the page to see the latest list.";
    case 409:
      return (
        apiError.message ??
        "Someone changed this at the same time. Refresh the page and try again."
      );
    default:
      if (apiError?.status && apiError.status >= 500) {
        return "The server had a problem and nothing was saved. Wait a moment, then try again.";
      }
      return (
        apiError?.message ??
        "That did not work and nothing was saved. Try again."
      );
  }
}

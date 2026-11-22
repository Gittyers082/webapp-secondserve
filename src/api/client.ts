/**
 * The API client every screen uses to change data.
 *
 * With PUBLIC_API_BASE_URL set (in .env, e.g. http://localhost:8000/api),
 * calls go to the server as JSON over fetch. Without it, they resolve against
 * the seed data in src/data/store.ts, so the frontend stays usable before the
 * backend exists. The screens never know which one answered.
 */
import type { ApiError, ListingInput, PartnerOrderInput, ReviewInput } from "./contract";
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

const BASE_URL: string | undefined = import.meta.env.PUBLIC_API_BASE_URL;

/** True when the client talks to a real server. */
export const isLive = Boolean(BASE_URL);

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    credentials: "include",
    headers:
      body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (!response.ok) {
    let message = response.statusText;
    try {
      message =
        ((await response.json()) as { message?: string }).message ?? message;
    } catch {
      // Not JSON; keep the status text.
    }
    throw { status: response.status, message } satisfies ApiError;
  }

  return response.status === 204 ? (null as T) : ((await response.json()) as T);
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

    // TODO(Role 4): GET /me returns the user with the shop inside `sellerProfile`; map it to ShopProfile.
    profile: () =>
      isLive
        ? request<ShopProfile>("GET", "/me")
        : offline(seed.sellerProfile),

    updateProfile: (input: Partial<Omit<ShopProfile, "logoUrl">>) =>
      isLive
        ? // TODO(Role 4): map ShopProfile fields to the backend's seller fields.
          request<ShopProfile>("PATCH", "/me", { seller: input })
        : offline({ ...seed.sellerProfile, ...input }),

    uploadLogo: async (file: File): Promise<{ logoUrl: string }> => {
      if (!isLive) return offline({ logoUrl: URL.createObjectURL(file) });
      // TODO(Role 1): the backend has no logo upload route yet.
      const body = new FormData();
      body.append("logo", file);
      const response = await fetch(`${BASE_URL}/seller/profile/logo`, {
        method: "POST",
        credentials: "include",
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
    // The backend answers with a page: { items, total, limit, offset }.
    surplus: async () =>
      isLive
        ? (await request<{ items: Listing[] }>("GET", "/partners/surplus")).items
        : offline(seed.surplusBoard),

    orders: () =>
      isLive
        ? request<Order[]>("GET", "/partners/orders")
        : offline(seed.partnerOrders),

    // TODO(Role 3): buy, claim and distributed answer 501 until the backend implements them.
    buy: (listingId: string, input: PartnerOrderInput) =>
      isLive
        ? request<Order>("POST", `/partners/surplus/${listingId}/buy`, input)
        : offline(partnerOrderFromSeed(listingId, input, "partner-purchase")),

    claim: (listingId: string, input: PartnerOrderInput) =>
      isLive
        ? request<Order>("POST", `/partners/surplus/${listingId}/claim`, input)
        : offline(partnerOrderFromSeed(listingId, input, "donation")),

    markDistributed: (orderId: string) =>
      isLive
        ? request<Order>("POST", `/partners/orders/${orderId}/distributed`)
        : offline({
            ...find(seed.partnerOrders, orderId),
            distributionStatus: "distributed",
          } as Order),

    // TODO(Role 4): GET /me returns the user with the organization inside `partnerProfile`.
    profile: () =>
      isLive
        ? request<PartnerProfile>("GET", "/me")
        : offline(seed.partnerProfile),

    updateProfile: (input: Partial<Omit<PartnerProfile, "verifiedAt">>) =>
      isLive
        ? request<PartnerProfile>("PATCH", "/me", { partner: input })
        : offline({ ...seed.partnerProfile, ...input }),
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
    return "Could not reach the SecondServe server. Check that this computer is online, then try again.";
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

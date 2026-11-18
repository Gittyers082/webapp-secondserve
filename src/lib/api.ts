/**
 * Typed client for the SecondServe API.
 *
 * Owner: Role 4 (Frontend Developer). The backend's live contract is at
 * `${PUBLIC_API_URL}/docs`. JSON fields are camelCase, matching src/data/types.ts.
 *
 * Usage in a page <script>:
 *
 *   import { api, setTokenProvider } from '../lib/api';
 *   setTokenProvider(async () => (await supabase.auth.getSession()).data.session?.access_token ?? null);
 *   const page = await api.listings.browse({ category: 'bread', sort: 'discount' });
 *
 * TODO(Role 4): install @supabase/supabase-js, create src/lib/supabase.ts, and
 * call setTokenProvider() once at startup.
 */

const BASE_URL = (import.meta.env.PUBLIC_API_URL as string | undefined) ?? 'http://localhost:8000';

/** Error with the HTTP status and the server's message (shown to users as-is). */
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public details?: unknown,
  ) {
    super(message);
  }
}

type TokenProvider = () => Promise<string | null>;
let getToken: TokenProvider = async () => null;

export function setTokenProvider(provider: TokenProvider): void {
  getToken = provider;
}

type Query = Record<string, string | number | boolean | undefined | null>;

async function request<T>(method: string, path: string, body?: unknown, query?: Query): Promise<T> {
  const url = new URL(path, BASE_URL);
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, String(value));
  }

  const headers: Record<string, string> = { Accept: 'application/json' };
  const token = await getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers['Content-Type'] = 'application/json';

  const res = await fetch(url, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });

  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = data?.detail;
    // FastAPI sends either a string, a list of our messages, or a list of field errors.
    const message =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => (typeof d === 'string' ? d : d.msg)).join(' ')
          : `Request failed (${res.status})`;
    throw new ApiError(res.status, message, detail);
  }
  return data as T;
}

/* ---------------------------------- Types --------------------------------- */
/* Mirror backend/app/schemas. Keep in sync when the API changes.             */

export type Role = 'buyer' | 'seller' | 'admin';
export type AccountStatus = 'pending' | 'active' | 'declined' | 'banned';
export type ApiCategory = 'bread' | 'pastries' | 'savory' | 'cakes' | 'fruit-cups' | 'groceries' | 'other';
export type ApiListingStatus = 'active' | 'sold-out' | 'withdrawn' | 'expired' | 'removed';
export type ApiOrderStatus = 'reserved' | 'ready' | 'picked-up' | 'cancelled';
export type PaymentMethod = 'pay-on-pickup' | 'gcash-simulated' | 'card-simulated';
export type SortOption = 'newest' | 'price-asc' | 'price-desc' | 'discount' | 'expiring';

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface SellerDetails {
  businessName: string;
  businessType: string;
  businessAddress: string;
  contactPhone: string;
  description?: string | null;
}

export interface Me {
  id: string;
  email: string;
  username: string;
  fullName: string;
  phone: string | null;
  role: Role;
  status: AccountStatus;
  createdAt: string;
  sellerProfile: (SellerDetails & { logoUrl: string | null; verifiedAt: string | null }) | null;
}

export interface ApiListing {
  id: string;
  sellerId: string;
  shopName: string;
  name: string;
  description: string;
  category: ApiCategory;
  art: string | null;
  imageUrl: string | null;
  /** Decimals arrive as strings, e.g. "60.00". Use Number() before maths. */
  originalPrice: string;
  discountedPrice: string;
  discountPercent: number;
  quantity: number;
  originalQuantity: number;
  expiresAt: string;
  pickupLocation: string;
  status: ApiListingStatus;
  flagged: boolean;
  createdAt: string;
}

export interface ListingInput {
  name: string;
  description: string;
  category: ApiCategory;
  originalPrice: number;
  discountedPrice: number;
  quantity: number;
  /** ISO string with a time zone, e.g. new Date(...).toISOString() */
  expiresAt: string;
  pickupLocation?: string;
  art?: string;
}

export interface ApiOrder {
  id: string;
  listingId: string;
  buyerId: string;
  sellerId: string;
  foodName: string;
  shopName: string;
  art: string | null;
  imageUrl: string | null;
  quantity: number;
  unitPrice: string;
  originalUnitPrice: string;
  total: string;
  pickupLocation: string;
  pickupCode: string;
  expiresAt: string;
  status: ApiOrderStatus;
  paymentStatus: 'pending' | 'paid' | 'failed' | 'refunded' | null;
  pickedUpAt: string | null;
  createdAt: string;
}

export interface ApiNotification {
  id: string;
  type: string;
  title: string;
  body: string;
  link: string | null;
  readAt: string | null;
  createdAt: string;
}

export interface BrowseQuery {
  q?: string;
  category?: ApiCategory;
  minPrice?: number;
  maxPrice?: number;
  minDiscount?: number;
  expiresBefore?: string;
  sort?: SortOption;
  limit?: number;
  offset?: number;
}

/* -------------------------------- Endpoints ------------------------------- */

export const api = {
  me: {
    get: () => request<Me>('GET', '/api/me'),
    createProfile: (body: {
      role: 'buyer' | 'seller';
      username: string;
      fullName: string;
      phone?: string;
      seller?: SellerDetails;
    }) => request<Me>('POST', '/api/me/profile', body),
    update: (body: Partial<Pick<Me, 'fullName' | 'phone'>> & { seller?: SellerDetails }) =>
      request<Me>('PATCH', '/api/me', body),
  },

  listings: {
    browse: (query: BrowseQuery = {}) => request<Page<ApiListing>>('GET', '/api/listings', undefined, { ...query }),
    get: (id: string) => request<ApiListing>('GET', `/api/listings/${id}`),
    mine: () => request<ApiListing[]>('GET', '/api/listings/mine'),
    create: (body: ListingInput) => request<ApiListing>('POST', '/api/listings', body),
    update: (id: string, body: Partial<ListingInput>) => request<ApiListing>('PATCH', `/api/listings/${id}`, body),
    setStatus: (id: string, status: 'active' | 'sold-out' | 'withdrawn') =>
      request<ApiListing>('POST', `/api/listings/${id}/status`, { status }),
    remove: (id: string) => request<void>('DELETE', `/api/listings/${id}`),
  },

  orders: {
    reserve: (body: { listingId: string; quantity: number; paymentMethod?: PaymentMethod }) =>
      request<ApiOrder>('POST', '/api/orders', body),
    mine: (status?: ApiOrderStatus) => request<ApiOrder[]>('GET', '/api/orders/mine', undefined, { status }),
    get: (id: string) => request<ApiOrder>('GET', `/api/orders/${id}`),
  },

  notifications: {
    list: (unreadOnly = false) =>
      request<ApiNotification[]>('GET', '/api/notifications', undefined, { unread_only: unreadOnly }),
    markRead: (id: string) => request<void>('POST', `/api/notifications/${id}/read`),
    markAllRead: () => request<void>('POST', '/api/notifications/read-all'),
  },

  admin: {
    users: (query: { q?: string; role?: Role; status?: AccountStatus } = {}) =>
      request<Me[]>('GET', '/api/admin/users', undefined, { ...query }),
    ban: (id: string) => request<Me>('POST', `/api/admin/users/${id}/ban`),
    unban: (id: string) => request<Me>('POST', `/api/admin/users/${id}/unban`),
    approvals: () => request<Me[]>('GET', '/api/admin/approvals'),
    decide: (id: string, decision: 'approved' | 'declined', reason?: string) =>
      request<Me>('POST', `/api/admin/approvals/${id}`, { decision, reason }),
  },
};

/**
 * Live stock updates. Calls `onChange` whenever a listing's quantity or status changes.
 * Returns a function that closes the connection.
 */
export function subscribeToStock(
  onChange: (update: { listingId: string; quantity: number; status: ApiListingStatus }) => void,
): () => void {
  const wsUrl = new URL('/ws/stock', BASE_URL);
  wsUrl.protocol = wsUrl.protocol === 'https:' ? 'wss:' : 'ws:';
  let socket: WebSocket | null = null;
  let closed = false;

  const connect = () => {
    socket = new WebSocket(wsUrl);
    socket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === 'stock') onChange(message);
    };
    // Reconnect after drops (e.g. Render waking up).
    socket.onclose = () => {
      if (!closed) setTimeout(connect, 3000);
    };
  };
  connect();

  return () => {
    closed = true;
    socket?.close();
  };
}

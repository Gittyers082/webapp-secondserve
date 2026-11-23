/**
 * The API contract the frontend is built against.
 *
 * Every endpoint the seller and admin screens call is listed here with its
 * method, path, request body and response. docs/api-contract.md describes the
 * same endpoints for the backend team. Change both together.
 */
import type {
  AccountDecision,
  AppNotification,
  Listing,
  ListingStatus,
  FulfillmentType,
  Order,
  PendingAccount,
  Review,
  SaleRecord,
  Session,
  ShopProfile,
  User,
} from '../data/types';

export interface ApiError {
  status: number;
  message: string;
}

/** Fields a seller sends to create or edit a listing. */
export interface ListingInput {
  name: string;
  description?: string;
  category: Listing['category'];
  quantity: number;
  originalPrice: number;
  discountedPrice: number;
  /** ISO local date-time, e.g. "2026-11-05T18:00". */
  expiresAt: string;
  pickupLocation: string;
  /** Id of a photo uploaded through POST /photos. */
  photoId?: string;
}

/** What a partner sends to buy surplus or claim a donation. */
export interface PartnerOrderInput {
  quantity: number;
  fulfillmentType: FulfillmentType;
  /** Required when fulfillmentType is "delivery". */
  deliveryAddress?: string;
}

export interface ReviewInput {
  orderId: string;
  rating: number;
  comment: string;
}

export interface Endpoints {
  // Seller
  'GET /listings/mine': { response: Listing[] };
  'POST /listings': { body: ListingInput; response: Listing };
  'PATCH /listings/:id': { body: Partial<ListingInput>; response: Listing };
  'POST /listings/:id/status': { body: { status: Extract<ListingStatus, 'sold' | 'withdrawn'> }; response: Listing };
  'DELETE /listings/:id': { response: null };
  'GET /orders/mine': { response: Order[] };
  'POST /orders/:id/ready': { response: Order };
  'GET /seller/sales': { response: SaleRecord[] };
  'GET /seller/reviews': { response: Review[] };
  'GET /me': { response: ShopProfile };
  'PATCH /me': { body: Partial<Omit<ShopProfile, 'logoUrl'>>; response: ShopProfile };
  /** multipart/form-data with a "file" field (JPEG, PNG or WebP, up to 2 MB). */
  'POST /me/logo': { body: FormData; response: { logoUrl: string } };

  // Buyer
  'POST /orders/:orderId/review': { body: ReviewInput; response: Review };

  // Partner
  'GET /partners/surplus': { response: { items: Listing[]; total: number; limit: number; offset: number } };
  'GET /partners/orders': { response: Order[] };
  'POST /partners/surplus/:id/buy': { body: PartnerOrderInput; response: Order };
  'POST /partners/surplus/:id/claim': { body: PartnerOrderInput; response: Order };
  'POST /partners/orders/:id/distributed': { response: Order };
  'POST /listings/:id/offer-to-partners': {
    body: { channel: 'partner-offer' | 'donation'; partnerPrice?: number };
    response: Listing;
  };

  // Administrator
  'GET /admin/users': { response: User[] };
  'POST /admin/users/:userId/ban': { response: User };
  'POST /admin/users/:userId/unban': { response: User };
  'GET /admin/approvals': { response: PendingAccount[] };
  'POST /admin/approvals/:id': { body: { decision: 'approved' | 'declined' }; response: AccountDecision };
  'GET /admin/decisions': { response: AccountDecision[] };
  'GET /admin/listings': { response: Listing[] };
  'POST /admin/listings/:id/flag': { response: Listing };
  'DELETE /admin/listings/:id': { response: null };
  'GET /admin/sessions': { response: Session[] };

  // Everyone signed in
  'GET /notifications': { response: AppNotification[] };
  'POST /notifications/:id/read': { response: null };
  'POST /notifications/read-all': { response: null };
}

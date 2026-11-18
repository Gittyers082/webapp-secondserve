/**
 * Seed data for the SecondServe frontend.
 *
 * Every figure here matches the wireframes so the screens read as one
 * continuous story: Mang Ben's lists ube cheese pandesal, maria_c reserves
 * two boxes, and the order lands in both histories.
 */

import type {
  AccountDecision,
  AppNotification,
  FaqEntry,
  Review,
  SaleRecord,
  CartLine,
  Listing,
  Order,
  PendingAccount,
  Session,
  User,
} from './types';

export const SERVER = {
  host: '192.168.1.20',
  port: '5050',
} as const;

export const serverAddress = `${SERVER.host}:${SERVER.port}`;

/* -------------------------------------------------------------------------- */
/* Users                                                                      */
/* -------------------------------------------------------------------------- */

export const users: User[] = [
  { id: 'u-001', username: 'maria_c', role: 'buyer', status: 'active' },
  {
    id: 'u-002',
    username: 'mangben_owner',
    role: 'seller',
    status: 'active',
    shopName: "Mang Ben's Bakery",
  },
  {
    id: 'u-003',
    username: 'kapeatbp_owner',
    role: 'seller',
    status: 'active',
    shopName: 'Kape Atbp Café',
  },
  { id: 'u-004', username: 'jun_dela_cruz', role: 'buyer', status: 'active' },
  { id: 'u-005', username: 'ally.p', role: 'buyer', status: 'active' },
  {
    id: 'u-006',
    username: 'promo_blaster',
    role: 'seller',
    status: 'active',
    shopName: 'Promo Blaster',
  },
  {
    id: 'u-007',
    username: 'spamlistings99',
    role: 'seller',
    status: 'banned',
    shopName: 'Spam Listings',
  },
];

export const buyer: User = users[0]!;
export const seller: User = users[1]!;
export const admin: User = {
  id: 'u-000',
  username: 'admin_ana',
  role: 'admin',
  status: 'active',
};

/* -------------------------------------------------------------------------- */
/* Marketplace listings                                                        */
/* -------------------------------------------------------------------------- */

export const listings: Listing[] = [
  {
    id: 'l-001',
    sellerId: 'u-002',
    shopName: "Mang Ben's Bakery",
    name: 'Ube Cheese Pandesal (box of 6)',
    description:
      'Soft ube pandesal filled with cheese, baked this morning. Surplus from today’s batch, still fresh.',
    category: 'bread',
    art: 'pandesal-ube',
    originalPrice: 120,
    discountedPrice: 60,
    quantity: 8,
    expiresAt: '2026-11-05T18:00',
    expiryLabel: 'Tomorrow, 6:00 PM',
    pickupLocation: "Mang Ben's Bakery, Session Road, Baguio",
    status: 'active',
    reserved: 2,
  },
  {
    id: 'l-002',
    sellerId: 'u-003',
    shopName: 'Kape Atbp Café',
    name: 'Croissant (pair)',
    description: 'Butter croissants from the morning bake, two to a bag.',
    category: 'pastries',
    art: 'croissant',
    originalPrice: 160,
    discountedPrice: 80,
    quantity: 5,
    expiresAt: '2026-11-06T20:00',
    expiryLabel: 'Nov 6, 8:00 PM',
    pickupLocation: 'Kape Atbp Café, Upper Session Rd, Baguio',
    status: 'active',
  },
  {
    id: 'l-003',
    sellerId: 'u-008',
    shopName: 'Session Road Deli',
    name: 'Chicken Empanada (3 pcs)',
    description: 'Baked chicken empanada, three pieces per order.',
    category: 'savory',
    art: 'empanada',
    originalPrice: 105,
    discountedPrice: 55,
    quantity: 12,
    expiresAt: '2026-11-07T17:00',
    expiryLabel: 'Nov 7, 5:00 PM',
    pickupLocation: 'Session Road, Baguio',
    status: 'active',
  },
  {
    id: 'l-004',
    sellerId: 'u-009',
    shopName: 'Green Basket Market',
    name: 'Strawberry Cups (250 g)',
    description: 'Fresh La Trinidad strawberries, cupped and ready to go.',
    category: 'fruit-cups',
    art: 'strawberry-cup',
    originalPrice: 150,
    discountedPrice: 90,
    quantity: 6,
    expiresAt: '2026-11-09T12:00',
    expiryLabel: 'Nov 9, 12:00 PM',
    pickupLocation: 'Harrison Road, Baguio',
    status: 'active',
  },
  {
    id: 'l-005',
    sellerId: 'u-010',
    shopName: 'Café Camp John Hay',
    name: 'Carrot Cake Slice',
    description: 'Thick carrot cake slice with cream cheese frosting.',
    category: 'cakes',
    art: 'cake-slice',
    originalPrice: 140,
    discountedPrice: 70,
    quantity: 4,
    expiresAt: '2026-11-10T15:00',
    expiryLabel: 'Nov 10, 3:00 PM',
    pickupLocation: 'Camp John Hay, Baguio',
    status: 'active',
  },
  {
    id: 'l-006',
    sellerId: 'u-002',
    shopName: "Mang Ben's Bakery",
    name: 'Pan de Sal (dozen)',
    description: 'Classic pan de sal by the dozen.',
    category: 'bread',
    art: 'pandesal-plain',
    originalPrice: 60,
    discountedPrice: 35,
    quantity: 14,
    expiresAt: '2026-11-03T18:00',
    expiryLabel: 'Nov 3, 6:00 PM',
    pickupLocation: "Mang Ben's Bakery, Session Road, Baguio",
    status: 'expired',
  },
];

/** Listings owned by Mang Ben's Bakery, as the seller tabs show them. */
export const sellerListings: Listing[] = [
  listings[0]!,
  {
    id: 'l-007',
    sellerId: 'u-002',
    shopName: "Mang Ben's Bakery",
    name: 'Cheese Roll (box of 4)',
    description: 'Soft rolls with a cheese centre, four to a box.',
    category: 'bread',
    art: 'cheese-roll',
    originalPrice: 100,
    discountedPrice: 55,
    quantity: 10,
    expiresAt: '2026-11-06T19:00',
    expiryLabel: 'Nov 6, 7:00 PM',
    pickupLocation: "Mang Ben's Bakery, Session Road, Baguio",
    status: 'active',
  },
  {
    id: 'l-008',
    sellerId: 'u-002',
    shopName: "Mang Ben's Bakery",
    name: 'Ensaymada (pack of 3)',
    description: 'Buttery ensaymada dusted with sugar and cheese.',
    category: 'pastries',
    art: 'ensaymada',
    originalPrice: 130,
    discountedPrice: 70,
    quantity: 9,
    expiresAt: '2026-11-08T12:00',
    expiryLabel: 'Nov 8, 12:00 PM',
    pickupLocation: "Mang Ben's Bakery, Session Road, Baguio",
    status: 'withdrawn',
  },
  {
    id: 'l-009',
    sellerId: 'u-002',
    shopName: "Mang Ben's Bakery",
    name: 'Monay Loaf',
    description: 'Dense monay loaf, good for merienda.',
    category: 'bread',
    art: 'monay',
    originalPrice: 70,
    discountedPrice: 40,
    quantity: 0,
    originalQuantity: 7,
    expiresAt: '2026-11-09T18:00',
    expiryLabel: 'Nov 9, 6:00 PM',
    pickupLocation: "Mang Ben's Bakery, Session Road, Baguio",
    status: 'sold',
  },
  listings[5]!,
];

/** Everything the administrator moderates, across all shops. */
export const moderatedListings: Listing[] = [
  listings[0]!,
  listings[1]!,
  listings[2]!,
  listings[3]!,
  {
    id: 'l-010',
    sellerId: 'u-006',
    shopName: 'promo_blaster',
    name: 'Mystery Meal Tray',
    description: 'No description given.',
    category: 'savory',
    art: 'mystery',
    originalPrice: 20,
    discountedPrice: 20,
    quantity: 1,
    expiresAt: '',
    expiryLabel: 'No expiry given',
    pickupLocation: 'Not given',
    status: 'active',
    flagged: true,
  },
  listings[5]!,
];

/* -------------------------------------------------------------------------- */
/* Buyer cart and orders                                                       */
/* -------------------------------------------------------------------------- */

export const cart: CartLine[] = [
  {
    listingId: 'l-001',
    shopName: "Mang Ben's Bakery",
    pickupLocation: "Mang Ben's Bakery, Session Road, Baguio",
    foodName: 'Ube Cheese Pandesal (box of 6)',
    art: 'pandesal-ube',
    quantity: 2,
    unitPrice: 60,
    originalUnitPrice: 120,
    expiryLabel: 'Tomorrow, 6:00 PM',
    expiringSoon: true,
  },
  {
    listingId: 'l-002',
    shopName: 'Kape Atbp Café',
    pickupLocation: 'Kape Atbp Café, Upper Session Rd, Baguio',
    foodName: 'Croissant (pair)',
    art: 'croissant',
    quantity: 1,
    unitPrice: 80,
    originalUnitPrice: 160,
    expiryLabel: 'Nov 6, 8:00 PM',
    expiringSoon: true,
  },
];

export const pendingOrders: Order[] = [
  {
    id: 'o-101',
    listingId: 'l-001',
    buyerUsername: 'maria_c',
    foodName: 'Ube Cheese Pandesal (box of 6)',
    art: 'pandesal-ube',
    shopName: "Mang Ben's Bakery",
    quantity: 2,
    total: 120,
    pickupLocation: "Mang Ben's Bakery, Session Road, Baguio",
    expiryLabel: 'Tomorrow, 6:00 PM',
    expiringSoon: true,
    status: 'ready',
  },
  {
    id: 'o-102',
    listingId: 'l-002',
    buyerUsername: 'maria_c',
    foodName: 'Croissant (pair)',
    art: 'croissant',
    shopName: 'Kape Atbp Café',
    quantity: 1,
    total: 80,
    pickupLocation: 'Kape Atbp Café, Upper Session Rd, Baguio',
    expiryLabel: 'Nov 6, 8:00 PM',
    expiringSoon: true,
    status: 'reserved',
  },
];

export const orderHistory: Order[] = [
  {
    id: 'o-090',
    listingId: 'l-001',
    buyerUsername: 'maria_c',
    foodName: 'Ube Cheese Pandesal (box of 6)',
    art: 'pandesal-ube',
    shopName: "Mang Ben's Bakery",
    quantity: 2,
    total: 120,
    pickupLocation: "Mang Ben's Bakery, Session Road, Baguio",
    expiryLabel: 'Nov 5, 6:00 PM',
    expiringSoon: false,
    status: 'picked-up',
    pickedUpAt: 'Nov 5, 4:35 PM',
  },
  {
    id: 'o-081',
    listingId: 'l-006',
    buyerUsername: 'maria_c',
    foodName: 'Pan de Sal (dozen)',
    art: 'pandesal-plain',
    shopName: "Mang Ben's Bakery",
    quantity: 1,
    total: 35,
    pickupLocation: "Mang Ben's Bakery, Session Road, Baguio",
    expiryLabel: 'Oct 29, 6:00 PM',
    expiringSoon: false,
    status: 'picked-up',
    pickedUpAt: 'Oct 29, 5:10 PM',
  },
  {
    id: 'o-074',
    listingId: 'l-005',
    buyerUsername: 'maria_c',
    foodName: 'Carrot Cake Slice',
    art: 'cake-slice',
    shopName: 'Café Camp John Hay',
    quantity: 1,
    total: 70,
    pickupLocation: 'Camp John Hay, Baguio',
    expiryLabel: 'Oct 22, 4:00 PM',
    expiringSoon: false,
    status: 'picked-up',
    pickedUpAt: 'Oct 22, 3:45 PM',
  },
  {
    id: 'o-066',
    listingId: 'l-003',
    buyerUsername: 'maria_c',
    foodName: 'Chicken Empanada (3 pcs)',
    art: 'empanada',
    shopName: 'Session Road Deli',
    quantity: 2,
    total: 110,
    pickupLocation: 'Session Road, Baguio',
    expiryLabel: 'Oct 15, 7:00 PM',
    expiringSoon: false,
    status: 'picked-up',
    pickedUpAt: 'Oct 15, 6:20 PM',
  },
  {
    id: 'o-058',
    listingId: 'l-004',
    buyerUsername: 'maria_c',
    foodName: 'Strawberry Cups (250 g)',
    art: 'strawberry-cup',
    shopName: 'Green Basket Market',
    quantity: 1,
    total: 90,
    pickupLocation: 'Harrison Road, Baguio',
    expiryLabel: 'Oct 9, 12:00 PM',
    expiringSoon: false,
    status: 'picked-up',
    pickedUpAt: 'Oct 9, 11:05 AM',
  },
];

/* -------------------------------------------------------------------------- */
/* Seller handover                                                             */
/* -------------------------------------------------------------------------- */

export const handoverQueue: Order[] = [
  {
    id: 'o-101',
    listingId: 'l-001',
    buyerUsername: 'maria_c',
    foodName: 'Ube Cheese Pandesal (box of 6)',
    art: 'pandesal-ube',
    shopName: "Mang Ben's Bakery",
    quantity: 2,
    total: 120,
    pickupLocation: "Mang Ben's Bakery, Session Road, Baguio",
    expiryLabel: 'Tomorrow, 6:00 PM',
    expiringSoon: true,
    status: 'reserved',
  },
  {
    id: 'o-103',
    listingId: 'l-007',
    buyerUsername: 'jun_dela_cruz',
    foodName: 'Cheese Roll (box of 4)',
    art: 'cheese-roll',
    shopName: "Mang Ben's Bakery",
    quantity: 1,
    total: 55,
    pickupLocation: "Mang Ben's Bakery, Session Road, Baguio",
    expiryLabel: 'Nov 6, 7:00 PM',
    expiringSoon: true,
    status: 'reserved',
  },
  {
    id: 'o-104',
    listingId: 'l-008',
    buyerUsername: 'ally.p',
    foodName: 'Ensaymada (pack of 3)',
    art: 'ensaymada',
    shopName: "Mang Ben's Bakery",
    quantity: 1,
    total: 70,
    pickupLocation: "Mang Ben's Bakery, Session Road, Baguio",
    expiryLabel: 'Nov 8, 12:00 PM',
    expiringSoon: false,
    status: 'ready',
  },
];

export const handoverRecord: Order[] = [
  {
    id: 'o-095',
    listingId: 'l-008',
    buyerUsername: 'ally.p',
    foodName: 'Ensaymada (pack of 3)',
    art: 'ensaymada',
    shopName: "Mang Ben's Bakery",
    quantity: 1,
    total: 70,
    pickupLocation: "Mang Ben's Bakery, Session Road, Baguio",
    expiryLabel: 'Nov 3, 6:00 PM',
    expiringSoon: false,
    status: 'picked-up',
    pickedUpAt: 'Nov 3, 5:20 PM',
  },
  {
    id: 'o-092',
    listingId: 'l-006',
    buyerUsername: 'jun_dela_cruz',
    foodName: 'Pan de Sal (dozen)',
    art: 'pandesal-plain',
    shopName: "Mang Ben's Bakery",
    quantity: 2,
    total: 70,
    pickupLocation: "Mang Ben's Bakery, Session Road, Baguio",
    expiryLabel: 'Nov 2, 6:00 PM',
    expiringSoon: false,
    status: 'picked-up',
    pickedUpAt: 'Nov 2, 4:05 PM',
  },
];

/* -------------------------------------------------------------------------- */
/* Administration                                                              */
/* -------------------------------------------------------------------------- */

export const pendingAccounts: PendingAccount[] = [
  {
    id: 'p-01',
    username: 'green_basket_owner',
    role: 'seller',
    shopName: 'Green Basket Market',
    requestedAt: 'Nov 4, 2:10 PM',
    decision: 'pending',
  },
  { id: 'p-02', username: 'luis_t', role: 'buyer', requestedAt: 'Nov 4, 1:42 PM', decision: 'pending' },
  {
    id: 'p-03',
    username: 'session_deli_owner',
    role: 'seller',
    shopName: 'Session Road Deli',
    requestedAt: 'Nov 4, 11:05 AM',
    decision: 'pending',
  },
  { id: 'p-04', username: 'carol.m', role: 'buyer', requestedAt: 'Nov 3, 8:30 PM', decision: 'pending' },
];

export const accountDecisions: AccountDecision[] = [
  {
    id: 'd-01',
    username: 'mangben_owner',
    role: 'seller',
    shopName: "Mang Ben's Bakery",
    decision: 'approved',
    decidedAt: 'Nov 1, 9:12 AM',
  },
  { id: 'd-02', username: 'maria_c', role: 'buyer', decision: 'approved', decidedAt: 'Nov 1, 9:14 AM' },
  {
    id: 'd-03',
    username: 'kapeatbp_owner',
    role: 'seller',
    shopName: 'Kape Atbp Café',
    decision: 'approved',
    decidedAt: 'Oct 31, 4:02 PM',
  },
  {
    id: 'd-04',
    username: 'fakeshop_88',
    role: 'seller',
    shopName: 'Free Pizza Co.',
    decision: 'declined',
    decidedAt: 'Oct 30, 1:20 PM',
  },
  {
    id: 'd-05',
    username: 'jun_dela_cruz',
    role: 'buyer',
    decision: 'approved',
    decidedAt: 'Oct 29, 10:47 AM',
  },
  { id: 'd-06', username: 'ally.p', role: 'buyer', decision: 'approved', decidedAt: 'Oct 28, 6:31 PM' },
  { id: 'd-07', username: 'test_acct_1', role: 'buyer', decision: 'declined', decidedAt: 'Oct 27, 3:05 PM' },
];

export const activeSessions: Session[] = [
  { username: 'admin_ana', role: 'admin', connectedSince: 'Today, 6:30 PM', clientAddress: '192.168.1.2' },
  { username: 'maria_c', role: 'buyer', connectedSince: 'Today, 6:42 PM', clientAddress: '192.168.1.24' },
  {
    username: 'mangben_owner',
    role: 'seller',
    connectedSince: 'Today, 5:58 PM',
    clientAddress: '192.168.1.31',
  },
  {
    username: 'kapeatbp_owner',
    role: 'seller',
    connectedSince: 'Today, 5:12 PM',
    clientAddress: '192.168.1.45',
  },
  { username: 'ally.p', role: 'buyer', connectedSince: 'Today, 4:47 PM', clientAddress: '192.168.1.52' },
];

/* -------------------------------------------------------------------------- */
/* Derived figures used by the dashboards                                      */
/* -------------------------------------------------------------------------- */

export const cartTotal = cart.reduce((sum, line) => sum + line.quantity * line.unitPrice, 0);
export const cartItemCount = cart.reduce((sum, line) => sum + line.quantity, 0);
export const cartShopCount = new Set(cart.map((line) => line.shopName)).size;

export const historyTotal = orderHistory.reduce((sum, order) => sum + order.total, 0);

export const expiringWithinThreeDays = sellerListings.filter(
  (listing) => listing.status === 'active' && listing.expiresAt && listing.expiresAt <= '2026-11-07',
);

export const reservedOrderCount = handoverQueue.length;

/* -------------------------------------------------------------------------- */
/* Reviews                                                                     */
/* -------------------------------------------------------------------------- */

export const reviews: Review[] = [
  {
    id: 'r-01',
    listingId: 'l-001',
    shopName: "Mang Ben's Bakery",
    foodName: 'Ube Cheese Pandesal (box of 6)',
    author: 'maria_c',
    rating: 5,
    comment: 'Still soft at pickup and the cheese had not dried out. The counter had my name ready.',
    date: 'Nov 5',
    orderId: 'o-090',
  },
  {
    id: 'r-02',
    listingId: 'l-006',
    shopName: "Mang Ben's Bakery",
    foodName: 'Pan de Sal (dozen)',
    author: 'jun_dela_cruz',
    rating: 4,
    comment: 'Good for the price. Two were a little flat but the rest were fine for breakfast.',
    date: 'Nov 2',
  },
  {
    id: 'r-03',
    listingId: 'l-008',
    shopName: "Mang Ben's Bakery",
    foodName: 'Ensaymada (pack of 3)',
    author: 'ally.p',
    rating: 5,
    comment: 'Plenty of cheese on top. Would reserve again.',
    date: 'Nov 3',
  },
  {
    id: 'r-04',
    listingId: 'l-007',
    shopName: "Mang Ben's Bakery",
    foodName: 'Cheese Roll (box of 4)',
    author: 'carol.m',
    rating: 3,
    comment: 'Tasty, but the pickup took a while because the shop was busy.',
    date: 'Oct 30',
  },
  {
    id: 'r-05',
    listingId: 'l-002',
    shopName: 'Kape Atbp Café',
    foodName: 'Croissant (pair)',
    author: 'ally.p',
    rating: 4,
    comment: 'Flaky and buttery. Reheated well the next morning.',
    date: 'Nov 1',
  },
  {
    id: 'r-06',
    listingId: 'l-005',
    shopName: 'Café Camp John Hay',
    foodName: 'Carrot Cake Slice',
    author: 'maria_c',
    rating: 5,
    comment: 'A big slice and the frosting was fresh.',
    date: 'Oct 22',
    orderId: 'o-074',
  },
  {
    id: 'r-07',
    listingId: 'l-003',
    shopName: 'Session Road Deli',
    foodName: 'Chicken Empanada (3 pcs)',
    author: 'jun_dela_cruz',
    rating: 4,
    comment: 'Crisp crust, generous filling.',
    date: 'Oct 18',
  },
];

/** Reviews for one shop, newest first as seeded. */
export const reviewsForShop = (shopName: string) => reviews.filter((review) => review.shopName === shopName);

/* -------------------------------------------------------------------------- */
/* Wishlist                                                                    */
/* -------------------------------------------------------------------------- */

/** Listings the buyer has saved before this session; the page adds to it locally. */
export const savedListingIds: string[] = ['l-002', 'l-004'];

/* -------------------------------------------------------------------------- */
/* Notifications                                                               */
/* -------------------------------------------------------------------------- */

export const buyerNotifications: AppNotification[] = [
  {
    id: 'n-b1',
    kind: 'order',
    title: 'Ready for pickup',
    body: "Ube Cheese Pandesal (box of 6) is ready at Mang Ben's Bakery. Collect it before tomorrow, 6:00 PM.",
    time: '10 min ago',
    read: false,
    href: '/buyer/pending',
  },
  {
    id: 'n-b2',
    kind: 'listing',
    title: 'A saved item is expiring',
    body: 'Croissant (pair) from Kape Atbp Café expires Nov 6, 8:00 PM. 5 left.',
    time: '1 hr ago',
    read: false,
    href: '/buyer/listing/l-002',
  },
  {
    id: 'n-b3',
    kind: 'review',
    title: 'How was your order?',
    body: 'You collected Ube Cheese Pandesal on Nov 5. Rate the shop to help other buyers.',
    time: 'Yesterday',
    read: true,
    href: '/buyer/history',
  },
  {
    id: 'n-b4',
    kind: 'account',
    title: 'Account approved',
    body: 'An administrator approved your buyer account. Welcome to SecondServe.',
    time: 'Nov 1',
    read: true,
  },
];

export const sellerNotifications: AppNotification[] = [
  {
    id: 'n-s1',
    kind: 'order',
    title: 'New reservation',
    body: 'maria_c reserved 2 × Ube Cheese Pandesal (box of 6). Mark it ready when it is packed.',
    time: '25 min ago',
    read: false,
    href: '/seller/handover',
  },
  {
    id: 'n-s2',
    kind: 'order',
    title: 'New reservation',
    body: 'jun_dela_cruz reserved 1 × Cheese Roll (box of 4).',
    time: '1 hr ago',
    read: false,
    href: '/seller/handover',
  },
  {
    id: 'n-s3',
    kind: 'review',
    title: 'New 5-star review',
    body: 'maria_c rated Ube Cheese Pandesal 5 stars: "Still soft at pickup…"',
    time: 'Yesterday',
    read: false,
    href: '/seller/reviews',
  },
  {
    id: 'n-s4',
    kind: 'listing',
    title: 'Listing expired',
    body: 'Pan de Sal (dozen) passed its expiry and was taken out of the Shop.',
    time: 'Nov 3',
    read: true,
    href: '/seller/manage',
  },
];

export const adminNotifications: AppNotification[] = [
  {
    id: 'n-a1',
    kind: 'account',
    title: '4 accounts waiting',
    body: 'Two sellers and two buyers asked to join. Review them in Pending Approvals.',
    time: '5 min ago',
    read: false,
    href: '/admin/approvals',
  },
  {
    id: 'n-a2',
    kind: 'listing',
    title: 'Listing flagged',
    body: 'Mystery Meal Tray from promo_blaster has no description, pickup place or expiry.',
    time: '40 min ago',
    read: false,
    href: '/admin/moderation',
  },
  {
    id: 'n-a3',
    kind: 'account',
    title: 'Repeated sign-in failures',
    body: 'spamlistings99 failed to sign in 6 times after being banned.',
    time: 'Yesterday',
    read: true,
    href: '/admin',
  },
];

/* -------------------------------------------------------------------------- */
/* Seller sales, for analytics                                                 */
/* -------------------------------------------------------------------------- */

/** Mang Ben's Bakery's completed sales over the last 7 days. */
export const salesLog: SaleRecord[] = [
  { date: '2026-10-30', day: 'Fri 30', listingName: 'Pan de Sal (dozen)', category: 'bread', quantity: 3, total: 105, fullPrice: 180 },
  { date: '2026-10-30', day: 'Fri 30', listingName: 'Cheese Roll (box of 4)', category: 'bread', quantity: 1, total: 55, fullPrice: 100 },
  { date: '2026-10-31', day: 'Sat 31', listingName: 'Ensaymada (pack of 3)', category: 'pastries', quantity: 2, total: 140, fullPrice: 260 },
  { date: '2026-10-31', day: 'Sat 31', listingName: 'Ube Cheese Pandesal (box of 6)', category: 'bread', quantity: 2, total: 120, fullPrice: 240 },
  { date: '2026-11-01', day: 'Sun 1', listingName: 'Monay Loaf', category: 'bread', quantity: 4, total: 160, fullPrice: 280 },
  { date: '2026-11-02', day: 'Mon 2', listingName: 'Pan de Sal (dozen)', category: 'bread', quantity: 2, total: 70, fullPrice: 120 },
  { date: '2026-11-02', day: 'Mon 2', listingName: 'Monay Loaf', category: 'bread', quantity: 3, total: 120, fullPrice: 210 },
  { date: '2026-11-03', day: 'Tue 3', listingName: 'Ensaymada (pack of 3)', category: 'pastries', quantity: 1, total: 70, fullPrice: 130 },
  { date: '2026-11-03', day: 'Tue 3', listingName: 'Cheese Roll (box of 4)', category: 'bread', quantity: 2, total: 110, fullPrice: 200 },
  { date: '2026-11-04', day: 'Wed 4', listingName: 'Ube Cheese Pandesal (box of 6)', category: 'bread', quantity: 3, total: 180, fullPrice: 360 },
  { date: '2026-11-05', day: 'Thu 5', listingName: 'Ube Cheese Pandesal (box of 6)', category: 'bread', quantity: 2, total: 120, fullPrice: 240 },
  { date: '2026-11-05', day: 'Thu 5', listingName: 'Ensaymada (pack of 3)', category: 'pastries', quantity: 1, total: 70, fullPrice: 130 },
];

/* -------------------------------------------------------------------------- */
/* FAQ and help                                                                */
/* -------------------------------------------------------------------------- */

export const faq: FaqEntry[] = [
  {
    question: 'How does reserving work?',
    answer:
      'Add food to your cart and check out to reserve it. The shop holds it for you. When the shop marks it ready, collect it in person before its expiry time and give your name at the counter.',
    roles: ['buyer'],
  },
  {
    question: 'Do I pay online?',
    answer: 'No. You pay the shop when you collect your order, at the discounted price shown when you reserved.',
    roles: ['buyer'],
  },
  {
    question: 'What if I cannot collect in time?',
    answer:
      'Food that is not collected before its expiry time goes back to the shop. Please only reserve what you can pick up, so the food reaches someone who can.',
    roles: ['buyer'],
  },
  {
    question: 'How do I save or compare items?',
    answer:
      'Use the heart on any listing to save it to your Wishlist. From the Wishlist, choose up to three items and select Compare to see their prices, discounts and pickup details side by side.',
    roles: ['buyer'],
  },
  {
    question: 'What food can I list?',
    answer:
      'Surplus food that is still safe to eat and not yet expired. The discounted price must be lower than the original price, and every listing needs a photo, a pickup place and an expiry time.',
    roles: ['seller'],
  },
  {
    question: 'When should I mark an order ready?',
    answer:
      'As soon as it is packed and waiting at the counter. The buyer sees it turn ready in My Pending Orders and gets a notification.',
    roles: ['seller'],
  },
  {
    question: 'How are my analytics worked out?',
    answer:
      'From the orders buyers have collected. Revenue is what buyers paid; food rescued counts the items sold; savings is the difference from the full price.',
    roles: ['seller'],
  },
  {
    question: 'Why was an account or listing flagged?',
    answer:
      'Listings without a description, pickup place or expiry, and accounts that post misleading offers, are flagged for review. Flag a listing to keep it visible to you while you decide; remove it to take it out of the Shop.',
    roles: ['admin'],
  },
  {
    question: 'I forgot my password.',
    answer: 'Ask an administrator to reset it. Passwords cannot be recovered by email in the desktop app.',
  },
  {
    question: 'The app says it cannot reach the server.',
    answer:
      'Check that this computer is on the same network as the SecondServe server, then confirm the address and port on the Connect screen.',
  },
];

/* -------------------------------------------------------------------------- */
/* Unread counts                                                               */
/* -------------------------------------------------------------------------- */

export const unreadCount = (items: AppNotification[]) => items.filter((item) => !item.read).length;

// src/types/index.ts
export interface Shop {
  id: number;
  name: string;
  description: string | null;
  phone: string | null;
  username: string | null;
  is_active: number;
  status: string;
  created_at: string;
}

export interface Category {
  id: number;
  shop_id: number;
  name: string;
  description: string | null;
  created_at: string;
}

export interface Product {
  id: number;
  shop_id: number;
  category_id: number;
  name: string;
  description: string | null;
  price: number;
  stock: number;
  reserved_stock: number;
  image_file_id: string | null;
  is_active: number;
  created_at: string;
  updated_at: string;
  available_stock?: number;
}

export interface User {
  user_id: number;
  current_shop_id: number | null;
  first_name: string | null;
  last_name: string | null;
  username: string | null;
  phone: string | null;
  address: string | null;
  is_blocked: number;
  registered_at: string;
}

export interface OrderItem {
  id: number;
  order_id: number;
  product_id: number | null;
  product_name: string;
  quantity: number;
  unit_price: number;
}

export interface Order {
  id: number;
  shop_id: number;
  tracking_code: string;
  user_id: number;
  total_price: number;
  status: string;
  payment_method: string | null;
  payment_ref: string | null;
  payment_status: string | null;
  receiver_name: string | null;
  shipping_address: string;
  phone: string;
  status_history: string;
  created_at: string;
  updated_at: string;
  items?: OrderItem[];
}

export interface ShopOwner {
  id: number;
  user_id: number;
  shop_id: number;
  first_name: string | null;
  username: string | null;
  registered_at: string;
}

export interface ClaimCode {
  id: number;
  code: string;
  shop_id: number;
  created_by: number;
  is_used: number;
  used_by: number | null;
  used_at: string | null;
  expires_at: string;
  created_at: string;
}

export interface Stats {
  totalShops: number;
  activeShops: number;
  totalProducts: number;
  totalOrders: number;
  pendingOrders: number;
  paidOrders: number;
  totalUsers: number;
}

export interface ShopStats {
  totalProducts: number;
  totalOrders: number;
  pendingOrders: number;
  paidOrders: number;
  totalRevenue: number;
}

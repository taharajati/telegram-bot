// src/app/seller/layout.tsx
import SellerLayoutClient from './SellerLayoutClient';

export default async function SellerRootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Auth check happens in client layout
  return <SellerLayoutClient>{children}</SellerLayoutClient>;
}
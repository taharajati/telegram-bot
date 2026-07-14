// src/app/admin/layout.tsx
import AdminLayoutClient from './AdminLayoutClient';

export default async function AdminRootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AdminLayoutClient>{children}</AdminLayoutClient>;
}

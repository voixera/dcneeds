import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DRX Bot Control",
  description: "Dashboard kontrol bot Discord DRX",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="id">
      <body>{children}</body>
    </html>
  );
}

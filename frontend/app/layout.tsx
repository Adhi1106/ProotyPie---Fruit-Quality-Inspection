import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ProotyPie - AI Freshness Guard",
  description: "AI fruit freshness inspection and storage recommendations."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SmartWaiting",
  description: "Gestion intelligente des files d'attente",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}

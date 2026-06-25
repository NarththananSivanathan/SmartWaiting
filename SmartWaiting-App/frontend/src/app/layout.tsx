import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Toaster } from "sonner";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "SmartWaiting",
    template: "%s | SmartWaiting",
  },
  description:
    "Système intelligent de gestion de file d’attente médicale avec interface médecin et affichage patient en temps réel.",
  applicationName: "SmartWaiting",
  authors: [{ name: "SmartWaiting Team" }],
  keywords: [
    "Next.js",
    "medical queue",
    "waiting room",
    "dashboard médical",
    "temps d'attente",
    "YOLO",
    "IoT",
    "healthcare",
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fr" className={inter.variable} suppressHydrationWarning>
      <body className="app-shell bg-background font-sans text-foreground antialiased">
        {children}

        <Toaster
          position="top-right"
          richColors
          closeButton
          toastOptions={{
            classNames: {
              toast: "sonner-toast",
              title: "sonner-title",
              description: "sonner-description",
            },
          }}
        />
      </body>
    </html>
  );
}
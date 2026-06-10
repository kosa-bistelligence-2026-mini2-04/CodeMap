import type { Metadata } from "next";
import {
  Geist,
  Geist_Mono,
  Playfair_Display,
  Playfair,
} from "next/font/google";
import "./globals.css";
import { WindowProvider } from "@/contexts/window-context";
import { WindowManager } from "@/components/windows/window-manager";
import { QueryProvider } from "@/contexts/query-provider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const playfair = Playfair({
  variable: "--font-playfair",
  subsets: ["latin"],
});

const playfairDisplay = Playfair_Display({
  variable: "--font-playfair-display",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Chat with Any GitHub Repository",
  description:
    "Use AI to chat with the codebase of any GitHub repository in your browser.",
  openGraph: {
    images: ["/social-preview.png"],
  },
  twitter: {
    card: "summary_large_image",
    images: ["/social-preview.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} ${playfairDisplay.variable} ${playfair.variable} antialiased overscroll-contain overflow-hidden`}
      >
        <QueryProvider>
          <WindowProvider>
            {children}
            <WindowManager />
          </WindowProvider>
        </QueryProvider>
      </body>
    </html>
  );
}

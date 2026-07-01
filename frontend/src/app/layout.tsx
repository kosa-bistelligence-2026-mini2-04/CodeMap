import type { Metadata } from "next";
import { Montserrat } from "next/font/google";
import "./globals.css";
import { Navbar } from "@/common/components/layout/Navbar";
import { AppProvider } from "@/common/contexts/AppContext";
import { AuthGuard } from "@/features/auth/components/AuthGuard";

const montserrat = Montserrat({
  variable: "--font-montserrat",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700", "800"],
});

export const metadata: Metadata = {
  title: "CodeMap AI — Codebase Intelligence",
  description:
    "Multi-agent system that helps you map, understand, and onboard to any codebase instantly with interactive graphs and reports.",
  keywords: [
    "codebase analysis",
    "AI code review",
    "repository intelligence",
    "code architecture",
    "multi-agent AI",
    "developer tools",
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${montserrat.variable}`}
      suppressHydrationWarning
      data-theme="dark"
    >
      <body className="antialiased font-sans" suppressHydrationWarning>
        <AppProvider>
          <AuthGuard>
            <Navbar />
            {children}
          </AuthGuard>
        </AppProvider>
      </body>
    </html>
  );
}

import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

// Vendored rather than fetched from Google at build time, so the Docker build
// works without network access. See fonts/README.md.
const displayFont = localFont({
  src: "./fonts/space-grotesk-latin.woff2",
  variable: "--font-display",
  weight: "300 700",
  display: "swap",
});

const bodyFont = localFont({
  src: "./fonts/manrope-latin.woff2",
  variable: "--font-body",
  weight: "200 800",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Kanban Studio",
  description: "A focused, single-board kanban workspace.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${displayFont.variable} ${bodyFont.variable}`}>
        {children}
      </body>
    </html>
  );
}

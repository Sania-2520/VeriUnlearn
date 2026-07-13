import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: {
    default: "VeriUnlearn - Verifiable Machine Unlearning",
    template: "%s | VeriUnlearn",
  },
  description:
    "A Verifiable Machine Unlearning Framework with Cryptographic Proofs for GDPR-Compliant AI Systems",
  keywords: [
    "machine unlearning",
    "GDPR",
    "right to be forgotten",
    "AI compliance",
    "cryptographic proof",
    "verifiable deletion",
  ],
  authors: [{ name: "VeriUnlearn Team" }],
  openGraph: {
    type: "website",
    locale: "en_US",
    siteName: "VeriUnlearn",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        {children}
      </body>
    </html>
  );
}

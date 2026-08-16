import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./Providers";

export const metadata: Metadata = {
  title: "VeriUnlearn — Verifiable Machine Unlearning",
  description:
    "Production-grade verifiable machine unlearning framework for GDPR Art. 17 & DPDP Act 2023 compliance: SISA, influence functions, certified removal, Merkle-tree deletion proofs, signed certificates, immutable audit trail.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

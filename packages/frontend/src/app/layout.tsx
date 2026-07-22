import type { Metadata } from "next"
import { Inter } from "next/font/google"
import { ThemeProvider } from "@/components/theme-provider"
import "./globals.css"

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" })

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
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning className={inter.variable}>
      <body className="font-sans antialiased">
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem
          disableTransitionOnChange
        >
          {children}
        </ThemeProvider>
      </body>
    </html>
  )
}

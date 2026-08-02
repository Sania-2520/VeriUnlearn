import type { Metadata } from "next"
import { Inter } from "next/font/google"
import { ThemeProvider } from "@/components/theme-provider"
import { SkipToContent } from "@/components/ui/skip-to-content"
import { LiveRegion } from "@/components/ui/live-region"
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
      <head>
        <meta
          name="viewport"
          content="width=device-width, initial-scale=1, viewport-fit=cover"
        />
      </head>
      <body className="font-sans antialiased">
        <SkipToContent />
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem
          disableTransitionOnChange
        >
          <LiveRegion mode="polite" />
          {children}
        </ThemeProvider>
      </body>
    </html>
  )
}

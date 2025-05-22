import type React from "react"
import "./globals.css"
import { GoogleSansMono, RobotoFont } from "../components/kokonutui/fonts"
import { ThemeProvider } from "@/components/theme-provider"

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning className={`${GoogleSansMono.variable} ${RobotoFont.variable}`}>
      <head>
        <title>Soundsboard</title>
        <meta name="description" content="Interactive soundboard with visual effects" />
      </head>
      <body>
        <ThemeProvider attribute="class" defaultTheme="dark">
          {children}
        </ThemeProvider>
      </body>
    </html>
  )
}

export const metadata = {
      generator: 'v0.dev'
    };

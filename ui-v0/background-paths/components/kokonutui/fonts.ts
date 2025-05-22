import { Noto_Sans_Mono as Google_Sans_Mono } from "next/font/google"
import { Roboto } from "next/font/google"

export const GoogleSansMono = Google_Sans_Mono({
  weight: ["700"], // Only using bold weight
  subsets: ["latin"],
  display: "swap",
  variable: "--font-google-sans-mono",
})

export const RobotoFont = Roboto({
  weight: ["700"], // Bold weight for the title
  subsets: ["latin"],
  display: "swap",
  variable: "--font-roboto",
})

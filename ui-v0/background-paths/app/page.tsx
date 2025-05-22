"use client"

import dynamic from "next/dynamic"
import { Suspense } from "react"

// Import the component with SSR disabled to prevent hydration mismatches
const SoundsboardNoSSR = dynamic(() => import("../components/kokonutui/soundsboard"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center min-h-screen bg-neutral-950">
      <div className="text-white text-2xl font-bold">Loading Soundsboard...</div>
    </div>
  ),
})

export default function Page() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-neutral-950" />}>
      <SoundsboardNoSSR title="Soundsboard" />
    </Suspense>
  )
}

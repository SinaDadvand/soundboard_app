"use client"

import { motion } from "framer-motion"
import { Button } from "@/components/ui/button"
import { useState, useRef, useEffect } from "react"
import { GoogleSansMono, RobotoFont } from "./fonts"

function FloatingPaths({
  position,
  isAnimating,
  animationColor,
}: {
  position: number
  isAnimating: boolean
  animationColor: string
}) {
  // Generate paths data
  const paths = Array.from({ length: 36 }, (_, i) => ({
    id: i,
    d: `M-${380 - i * 5 * position} -${189 + i * 6}C-${
      380 - i * 5 * position
    } -${189 + i * 6} -${312 - i * 5 * position} ${216 - i * 6} ${
      152 - i * 5 * position
    } ${343 - i * 6}C${616 - i * 5 * position} ${470 - i * 6} ${
      684 - i * 5 * position
    } ${875 - i * 6} ${684 - i * 5 * position} ${875 - i * 6}`,
    width: 0.5 + i * 0.03,
    // Use deterministic durations based on index
    duration: 15 + (i % 10),
  }))

  return (
    <div className="absolute inset-0 pointer-events-none">
      <svg className="w-full h-full" viewBox="0 0 696 316" fill="none">
        <title>Gold Background Paths</title>
        <defs>
          <linearGradient id="goldGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#FFD700" stopOpacity="0.6" /> {/* Gold */}
            <stop offset="50%" stopColor="#DAA520" stopOpacity="0.5" /> {/* GoldenRod */}
            <stop offset="100%" stopColor="#B8860B" stopOpacity="0.4" /> {/* DarkGoldenRod */}
          </linearGradient>
          <linearGradient id="animationGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={animationColor} stopOpacity="0.8" />
            <stop offset="50%" stopColor={animationColor} stopOpacity="0.6" />
            <stop offset="100%" stopColor={animationColor} stopOpacity="0.4" />
          </linearGradient>
          <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="6" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>
        {paths.map((path) => (
          <motion.path
            key={`path-${position}-${path.id}`}
            d={path.d}
            stroke={
              isAnimating
                ? path.id % 2 === 0
                  ? "url(#animationGradient)"
                  : animationColor
                : path.id % 3 === 0
                  ? "url(#goldGradient)"
                  : path.id % 3 === 1
                    ? "#FFD700"
                    : "#DAA520"
            }
            strokeWidth={isAnimating ? path.width * 1.2 : path.width}
            strokeOpacity={isAnimating ? 0.2 + path.id * 0.03 : 0.1 + path.id * 0.02}
            filter={isAnimating ? "url(#glow)" : "none"}
            initial={{ pathLength: 0.3, opacity: 0.4, pathOffset: 0 }}
            animate={{
              pathLength: 1,
              opacity: isAnimating ? [0.4, 0.8, 0.4] : [0.2, 0.5, 0.2],
              pathOffset: [0, 1],
            }}
            transition={{
              duration: path.duration,
              repeat: Number.POSITIVE_INFINITY,
              ease: "linear",
              pathOffset: {
                duration: path.duration,
                repeat: Number.POSITIVE_INFINITY,
                ease: "linear",
              },
            }}
          />
        ))}
      </svg>
    </div>
  )
}

export default function Soundsboard({
  title = "Soundsboard",
}: {
  title?: string
}) {
  const words = title.split(" ")
  const [isAnimating, setIsAnimating] = useState(false)
  const [animationColor, setAnimationColor] = useState("#FFD700")
  const timeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Clean up timeout on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [])

  // Function to trigger animation with a specific color
  const triggerAnimation = (color: string) => {
    // Clear any existing timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }

    // Set animation color and state
    setAnimationColor(color)
    setIsAnimating(true)

    // Reset animation after 1.5 seconds
    timeoutRef.current = setTimeout(() => {
      setIsAnimating(false)
    }, 1500)
  }

  // Sound button data for the smaller buttons with colors
  const soundButtons = [
    { name: "Kick", delay: 0.1, color: "#FF5555" },
    { name: "Snare", delay: 0.15, color: "#FF8A5E" },
    { name: "Hi-Hat", delay: 0.2, color: "#FFB454" },
    { name: "Clap", delay: 0.25, color: "#FFD700" },
    { name: "Crash", delay: 0.3, color: "#F9F871" },
    { name: "Tom", delay: 0.35, color: "#A5FF8F" },
    { name: "Bass", delay: 0.4, color: "#64DFDF" },
    { name: "Synth", delay: 0.45, color: "#56CFE1" },
    { name: "Piano", delay: 0.5, color: "#48BFE3" },
    { name: "Strings", delay: 0.55, color: "#5390D9" },
    { name: "Vocal", delay: 0.6, color: "#6930C3" },
    { name: "FX", delay: 0.65, color: "#9D4EDD" },
    { name: "Ambient", delay: 0.7, color: "#C77DFF" },
  ]

  return (
    <div
      className={`relative min-h-screen w-full flex items-center justify-center overflow-hidden bg-neutral-950 ${GoogleSansMono.className}`}
    >
      <div className="absolute inset-0">
        <FloatingPaths position={1} isAnimating={isAnimating} animationColor={animationColor} />
        <FloatingPaths position={-1} isAnimating={isAnimating} animationColor={animationColor} />
      </div>

      <div className="relative z-10 container mx-auto px-4 md:px-6 py-12">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1 }}
          className="max-w-5xl mx-auto"
        >
          <h1
            className={`text-5xl sm:text-7xl md:text-8xl font-bold mb-16 tracking-tighter text-center text-white ${RobotoFont.className}`}
          >
            {words.map((word, wordIndex) => (
              <span key={wordIndex} className="inline-block mr-4 last:mr-0">
                {word.split("").map((letter, letterIndex) => (
                  <motion.span
                    key={`${wordIndex}-${letterIndex}`}
                    initial={{ y: 50, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{
                      delay: wordIndex * 0.1 + letterIndex * 0.03,
                      type: "spring",
                      stiffness: 150,
                      damping: 25,
                    }}
                    className="inline-block font-bold"
                  >
                    {letter}
                  </motion.span>
                ))}
              </span>
            ))}
          </h1>

          {/* Sound Buttons Grid - 13 smaller buttons with transparent backgrounds */}
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3 max-w-4xl mx-auto">
            {soundButtons.map((button, index) => (
              <motion.div
                key={button.name}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: button.delay, duration: 0.4 }}
                className="group"
              >
                <Button
                  variant="outline"
                  onClick={() => triggerAnimation(button.color)}
                  className="w-full h-16 rounded-xl text-sm font-bold
                            border border-white/20 text-white/80 hover:text-white
                            bg-transparent hover:bg-white/10 hover:border-white/30
                            transition-all duration-200 backdrop-blur-sm
                            hover:shadow-md hover:shadow-amber-500/20
                            active:scale-95 active:shadow-inner"
                  style={{
                    boxShadow: isAnimating && animationColor === button.color ? `0 0 15px ${button.color}40` : "none",
                  }}
                >
                  {button.name}
                </Button>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  )
}

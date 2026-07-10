"use client";

import { useState, useEffect } from "react";
import Image from "next/image";

const IMAGES = [
  "/bg-football.png",
  "/bg-f1.png",
  "/bg-cricket.png",
];

export default function BackgroundCarousel() {
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setActiveIndex((current) => (current + 1) % IMAGES.length);
    }, 6000); // 6 seconds per background
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="fixed inset-0 z-[-1] bg-sky-canvas overflow-hidden">
      {IMAGES.map((src, index) => (
        <div
          key={src}
          className={`absolute inset-0 transition-opacity duration-1000 ease-in-out ${
            index === activeIndex ? "opacity-100" : "opacity-0"
          }`}
        >
          <div className="absolute inset-0 bg-black/70 z-10" /> {/* Dark overlay to ensure text readability */}
          <Image
            src={src}
            alt="SportIQ Background"
            fill
            className="object-cover object-center scale-105"
            priority={index === 0}
            unoptimized // Since these are local dev artifacts currently
          />
        </div>
      ))}
    </div>
  );
}

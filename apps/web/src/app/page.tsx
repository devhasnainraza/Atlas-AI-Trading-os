"use client";

import React, { useState, useEffect } from "react";
import { LandingPageView } from "../components/LandingPageView";

export default function HomePage() {
  const [theme, setTheme] = useState<"light" | "dark">("light");

  useEffect(() => {
    try {
      const saved = localStorage.getItem("atlas_theme") as "light" | "dark" | null;
      if (saved) {
        setTheme(saved);
        document.documentElement.setAttribute("data-theme", saved);
      }
    } catch {}
  }, []);

  const handleToggleTheme = () => {
    setTheme((prev) => {
      const next = prev === "light" ? "dark" : "light";
      try {
        localStorage.setItem("atlas_theme", next);
        document.documentElement.setAttribute("data-theme", next);
      } catch {}
      return next;
    });
  };

  return (
    <LandingPageView
      onLaunchCockpit={() => {
        window.location.href = "/cockpit";
      }}
      theme={theme}
      onToggleTheme={handleToggleTheme}
    />
  );
}

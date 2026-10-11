import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  devIndicators: false,
  // Lets a second instance (e.g. browser tests on other ports) build into its own folder without clobbering the main one.
  distDir: process.env.NEXT_DIST_DIR || ".next",
};

export default nextConfig;

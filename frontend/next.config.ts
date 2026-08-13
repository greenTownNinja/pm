import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Static export: `next build` writes out/, which FastAPI serves at /.
  output: "export",
  images: { unoptimized: true },
};

export default nextConfig;

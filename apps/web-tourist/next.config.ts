import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  outputFileTracingRoot: path.join(process.cwd(), "../.."),
  transpilePackages: ["@aether/design-system"],
  experimental: {
    viewTransition: true
  }
};

export default nextConfig;

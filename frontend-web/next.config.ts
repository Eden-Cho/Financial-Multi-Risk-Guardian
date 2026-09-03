import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export", // 정적 HTML/JS/CSS 내보내기 (FastAPI 정적 마운트용)
  trailingSlash: true,
  images: {
    unoptimized: true, // 정적 export 시 이미지 최적화 오류 방지
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
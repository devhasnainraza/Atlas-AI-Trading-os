/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  transpilePackages: ["@atlas/ui", "@atlas/api-client", "@atlas/config"],
};

export default nextConfig;

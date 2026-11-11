/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  trailingSlash: true,
  typescript: { ignoreBuildErrors: false },
};

export default nextConfig;

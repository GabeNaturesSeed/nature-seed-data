/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  basePath: '/nature-seed-data',
  images: { unoptimized: true },
  trailingSlash: true,
};

module.exports = nextConfig;

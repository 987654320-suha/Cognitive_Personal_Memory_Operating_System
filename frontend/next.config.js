let apiUrl = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").trim();
if (!apiUrl.includes(".") && !apiUrl.startsWith("localhost") && !apiUrl.startsWith("127.0.0.1") && !apiUrl.includes(":")) {
  apiUrl = `${apiUrl}.onrender.com`;
}
if (!apiUrl.startsWith("http://") && !apiUrl.startsWith("https://")) {
  apiUrl = (apiUrl.startsWith("localhost") || apiUrl.startsWith("127.0.0.1")) ? `http://${apiUrl}` : `https://${apiUrl}`;
}
apiUrl = apiUrl.replace(/\/+$/, "");

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    domains: ["localhost"],
    remotePatterns: [
      { protocol: "http", hostname: "localhost", port: "8000", pathname: "/uploads/**" },
      { protocol: "https", hostname: "**.onrender.com", pathname: "/uploads/**" },
    ],
  },
  env: {
    NEXT_PUBLIC_API_URL: apiUrl,
  },
};

module.exports = nextConfig;
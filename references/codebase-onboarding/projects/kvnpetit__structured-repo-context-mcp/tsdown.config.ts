import { defineConfig } from "tsdown";

const isProd = process.env.NODE_ENV === "production";

export default defineConfig({
  entry: ["./src/index.ts", "./src/bin.ts"],
  outDir: "dist",
  clean: true,

  format: ["esm"],
  platform: "node",
  target: "node22",

  treeshake: true,
  minify: isProd,
  sourcemap: !isProd,
  dts: true,

  report: {
    gzip: true,
    brotli: false,
    maxCompressSize: 1_000_000,
  },
  logLevel: isProd ? "warn" : "info",

  onSuccess: async () => {
    console.log("✅ Build completed!");
  },
});

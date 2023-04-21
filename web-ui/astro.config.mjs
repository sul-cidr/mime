import svelte from "@astrojs/svelte";
import { defineConfig } from "astro/config";
import tailwind from "@astrojs/tailwind";

// https://astro.build/config
export default defineConfig({
  trailingSlash: "always",
  integrations: [svelte(), tailwind()],
  vite: {
    cacheDir: process.env.VITE_CACHE_DIR || "node_modules/.vite",
  },
});

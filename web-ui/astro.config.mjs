import { defineConfig } from "astro/config";
import { searchForWorkspaceRoot } from "vite";
import svelte from "@astrojs/svelte";
import tailwind from "@astrojs/tailwind";

// https://astro.build/config
const config = defineConfig({
  trailingSlash: "always",
  integrations: [svelte(), tailwind()],
  vite: {
    cacheDir: process.env.VITE_CACHE_DIR || "node_modules/.vite",
  },
});

if (process.env.MODULES_DIR) {
  // If MODULES_DIR is defined, we need to allow access for the vite dev server
  //  (this is expected in the dockerized stack).
  config.vite.server = {
    fs: {
      allow: [searchForWorkspaceRoot(process.cwd()), process.env.MODULES_DIR],
    },
  };
}

export default config;

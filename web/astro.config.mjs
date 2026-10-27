import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';

// https://astro.build/config
export default defineConfig({
  output: 'static',
  server: {
    host: '127.0.0.1',
    port: 4321,
  },
  integrations: [tailwind()],
});

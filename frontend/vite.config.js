import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The app lives under /ttb (elijahwf.com/ttb via a Vercel rewrite). base makes
// asset URLs /ttb/..., and outDir 'dist/ttb' makes the SWA serve the files at
// the matching path (SWA output root = dist/, so files land under /ttb/).
export default defineConfig({
  plugins: [react()],
  base: '/ttb/',
  build: {
    outDir: 'dist/ttb',
    emptyOutDir: true,
  },
})

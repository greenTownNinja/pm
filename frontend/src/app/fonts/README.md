# Vendored fonts

Latin-subset variable woff2 files, taken from Google Fonts. Both are licensed under the
SIL Open Font License 1.1.

- `space-grotesk-latin.woff2` - Space Grotesk, weight axis 300-700
- `manrope-latin.woff2` - Manrope, weight axis 200-800

They are vendored so `next build` needs no network access, which keeps the Docker build
reproducible and offline-capable. Loaded via `next/font/local` in `../layout.tsx`.

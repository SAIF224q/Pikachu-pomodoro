# Drift Timer Tauri

This is a separate Tauri version of Drift Timer. The original Electron app in the parent folder is unchanged.

## Requirements

- Node.js and npm
- Rust from <https://www.rust-lang.org/tools/install>
- Microsoft Edge WebView2 on Windows (the installer can bootstrap it)

## Development

```bash
npm install
npm run tauri:dev
```

## Build Windows installers

```bash
npm run tauri:build
```

Installers are written under `src-tauri/target/release/bundle/`.

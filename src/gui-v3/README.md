# Taranis NG - Vue 3 GUI

This directory contains the Vue 3 Taranis NG graphical user interface.

**Audience:** Vue 3 frontend developers.

**Deployment status:** the tracked Docker stack serves the Vue 2 GUI at `/`.
The Vue 3 application uses `/v2/`, but its tracked Compose service is disabled.
The commands below are for frontend development and evaluation. Use the
[Docker deployment guide](../../docker/README.md) for the supported complete
application stack.

## Tech Stack

- **Vue** - Composition API application framework
- **Vite** - Development and production build tooling
- **Vuetify** - Material Design component framework
- **Pinia** - Application state management
- **Vue Router** - Client-side routing under `/v2/`
- **Vue I18n** - Internationalization and locale fallback
- **Axios** - HTTP client

Exact dependency versions are defined in `package.json` and
`package-lock.json`.

## 📚 Documentation

See [docs/README.md](./docs/README.md) for complete documentation index:

- **[Status reference](./docs/IMPLEMENTATION_STATUS.md)** - Current feature and deployment status
- **[Architecture](./docs/README.md#for-architecture)** - Design and component architecture index

## Development Setup

### Prerequisites

- Node.js 22 and npm

### Install Dependencies

```bash
npm ci
```

### Development Server

```bash
npm run dev
```

The development server starts at `http://localhost:4444/v2/` by default. Use a
different port when Docker or another service already owns port 4444.

You can override the port if needed:

```bash
VITE_PORT=8082 npm run dev
```

### Build for Production

```bash
npm run build
```

The production build will be output to the `dist/` directory.

### Verification

```bash
npm run format:check
npm run lint:check
npm run typecheck
npm run test:unit
npm run build
```

## Environment Variables

The following environment variables are used (configured at Docker runtime):

- `VITE_APP_TARANIS_NG_URL` - Public application URL
- `VITE_APP_TARANIS_NG_CORE_API` - Backend API endpoint
- `VITE_APP_TARANIS_NG_CORE_SSE` - Server-Sent Events endpoint
- `VITE_APP_TARANIS_NG_LOCALE` - Default locale code
- `VITE_APP_TARANIS_NG_LOGIN_URL` - Optional OIDC login URL; use `TARANIS_GUI_URI` for the encoded `/v2/login` callback
- `VITE_APP_TARANIS_NG_LOGOUT_URL` - Optional OIDC logout URL; use `TARANIS_GUI_URI` for the encoded `/v2/login` return URL
- `VITE_APP_VERSION` - Application version
- `VITE_DEV_BACKEND_ORIGIN` - Development proxy target origin

## Languages

The Vue 3 interface is translated into the following languages:

- Asian languages: Hindi (`hi`), Japanese (`ja`), Korean
  (`ko`), Simplified Chinese (`zh-CN`), Thai (`th`), and Vietnamese (`vi`)
- Central and Eastern European languages: Czech (`cs`), Polish (`pl`), Russian
  (`ru`), Slovak (`sk`), and Ukrainian (`uk`)
- Western European languages: Dutch (`nl`), English (`en`), French (`fr`),
  German (`de`), Italian (`it`), Brazilian Portuguese (`pt-BR`), and Spanish
  (`es`)
- Turkish (`tr`)

English is the fallback locale.

The legacy Vue 2 interface currently supports Czech (`cs`), English (`en`),
and Slovak (`sk`).

Locale catalogs are discovered automatically from `src/i18n/*.json` at build
time, so adding a catalog does not require a source-code registry or database
option entry.

### Env Precedence in Dev (`npm run dev`)

Vite loads env files from two places, in this order:

1. `docker/.env*`
2. `src/gui-v3/.env*` (overrides same keys from `docker/.env*`)

For backend proxying in `vite.config.js`, values are resolved as follows:

- Backend origin: `VITE_DEV_BACKEND_ORIGIN` -> `TARANIS_NG_HTTPS_URI` -> `http://127.0.0.1:8082`
- API URL: `VITE_APP_TARANIS_NG_CORE_API` -> `${backendOrigin}/api/v1`
- SSE URL: `VITE_APP_TARANIS_NG_CORE_SSE` -> `${backendOrigin}/sse`

Notes:

- Vue 3 uses `VITE_APP_*`; `VUE_APP_*` belongs to the Vue 2 GUI.
- Dev server default port is `4444` (override with `VITE_PORT` or `PORT`).

## Project Structure

```
src/
├── api/          # API endpoint wrappers
├── assets/       # Static assets and styles
├── components/   # Reusable Vue components
├── composables/  # Composition API composables
├── i18n/         # Internationalization files
├── services/     # Business logic services
├── stores/       # Pinia stores
├── views/        # Route view components
├── App.vue       # Root component
├── main.ts       # Application entry point
└── router.ts     # Vue Router configuration
```

## Runtime paths

- Vue 2 uses `/` in the tracked Docker deployment.
- Vue 3 uses `/v2/` when its container or development server is running.
- Vue Router and the production Nginx configuration both preserve `/v2/` for
  direct navigation and SPA fallback.

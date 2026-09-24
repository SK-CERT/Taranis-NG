# Taranis NG - GUI

This directory contains the Taranis NG graphical user interface, a Vue 3
application.

**Audience:** frontend developers.

The Docker stack serves this application at `/` (Compose service `gui`). The
commands below are for frontend development. Use the
[Docker deployment guide](../../docker/README.md) for the complete application
stack.

## Tech Stack

- **Vue** - Composition API application framework
- **Vite** - Development and production build tooling
- **Vuetify** - Material Design component framework
- **Pinia** - Application state management
- **Vue Router** - Client-side routing
- **Vue I18n** - Internationalization and locale fallback
- **Axios** - HTTP client

Exact dependency versions are defined in `package.json` and
`package-lock.json`.

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

The development server starts at `http://localhost:4444/` by default. Use a
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
- `VITE_DEV_BACKEND_ORIGIN` - Development proxy target origin

## Languages

The interface is translated into the following languages:

- Arabic (`ar`), rendered right-to-left
- Asian languages: Hindi (`hi`), Japanese (`ja`), Korean
  (`ko`), Simplified Chinese (`zh-CN`), Thai (`th`), and Vietnamese (`vi`)
- Central and Eastern European languages: Czech (`cs`), Polish (`pl`), Russian
  (`ru`), Slovak (`sk`), and Ukrainian (`uk`)
- Western European languages: Dutch (`nl`), English (`en`), French (`fr`),
  German (`de`), Italian (`it`), Brazilian Portuguese (`pt-BR`), and Spanish
  (`es`)
- Turkish (`tr`)

English is the fallback locale.

Locale catalogs are discovered automatically from `src/i18n/*.json` at build
time, so adding a catalog does not require a source-code registry or database
option entry.

### Env Precedence in Dev (`npm run dev`)

Vite loads env files from two places, in this order:

1. `docker/.env*`
2. `src/gui/.env*` (overrides same keys from `docker/.env*`)

For backend proxying in `vite.config.js`, values are resolved as follows:

- Backend origin: `VITE_DEV_BACKEND_ORIGIN` -> `TARANIS_NG_HTTPS_URI` -> `http://127.0.0.1:8082`
- API URL: `VITE_APP_TARANIS_NG_CORE_API` -> `${backendOrigin}/api/v1`
- SSE URL: `VITE_APP_TARANIS_NG_CORE_SSE` -> `${backendOrigin}/sse`

Dev server default port is `4444` (override with `VITE_PORT` or `PORT`).

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

The application is served at `/`. Vue Router uses HTML5 history mode, and the
production Nginx configuration (`extras/default.conf`) falls back to
`index.html` so direct navigation to any client route works. `/api` and `/sse`
belong to core: Traefik routes them in Docker, the Vite proxy in development.

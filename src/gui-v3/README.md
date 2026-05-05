# Taranis NG - Vue 3 GUI

This is the Vue 3 version of the Taranis NG graphical user interface, built with modern web technologies.

## Tech Stack

- **Vue 3** - Progressive JavaScript framework with Composition API
- **Vite** - Next generation frontend tooling
- **Vuetify 3** - Material Design component framework
- **Pinia** - Intuitive state management for Vue
- **Vue Router 4** - Official router for Vue.js
- **Vue I18n 9** - Internationalization plugin
- **Axios** - HTTP client

## 📚 Documentation

See [docs/README.md](./docs/README.md) for complete documentation index:

- **[Migration Guide](./docs/migration/README.md)** - Vue2→Vue3 component migration progress
- **[IMPLEMENTATION_STATUS](./docs/IMPLEMENTATION_STATUS.md)** - Overall project status and phase tracking
- **[Architecture](./docs/architecture/README.md)** - Design and component architecture

## Development Setup

### Prerequisites

- Node.js 18+ and npm

### Install Dependencies

```bash
npm install
```

### Development Server

```bash
npm run dev
```

The development server will start at `http://localhost:4444/v2/` by default.

You can override the port if needed:

```bash
VITE_PORT=8082 npm run dev
```

### Build for Production

```bash
npm run build
```

The production build will be output to the `dist/` directory.

### Lint

```bash
npm run lint
```

## Environment Variables

The following environment variables are used (configured at Docker runtime):

- `VUE_APP_TARANIS_NG_URL` - Base URL of the application
- `VUE_APP_TARANIS_NG_CORE_API` - Backend API endpoint
- `VUE_APP_TARANIS_NG_CORE_SSE` - Server-Sent Events endpoint
- `VUE_APP_TARANIS_NG_LOCALE` - Default locale (en, cs, sk)
- `VUE_APP_VERSION` - Application version

### Env Precedence in Dev (`npm run dev`)

Vite loads env files from two places, in this order:

1. `docker/.env*`
2. `src/gui-v3/.env*` (overrides same keys from `docker/.env*`)

For backend proxying in `vite.config.js`, values are resolved with fallbacks:

- Backend origin: `VITE_DEV_BACKEND_ORIGIN` -> `TARANIS_NG_HTTPS_URI` -> `http://127.0.0.1:8082`
- API URL: `VITE_APP_TARANIS_NG_CORE_API` -> `VUE_APP_TARANIS_NG_CORE_API` -> `${backendOrigin}/api/v1`
- SSE URL: `VITE_APP_TARANIS_NG_CORE_SSE` -> `VUE_APP_TARANIS_NG_CORE_SSE` -> `${backendOrigin}/sse`

Notes:

- `VITE_APP_*` is preferred for Vue 3.
- `VUE_APP_*` is kept as compatibility fallback for existing Docker/runtime configuration.
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
├── main.js       # Application entry point
└── router.js     # Vue Router configuration
```

## Migration Status

This is a **work in progress** migration from Vue 2 to Vue 3. The legacy Vue 2 UI is still accessible at `/` while this Vue 3 version is available at `/v2/`.

See the migration plan documentation for details on the gradual component-by-component migration strategy.

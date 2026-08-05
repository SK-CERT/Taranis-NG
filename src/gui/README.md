# Taranis NG GUI

**Audience:** developers of the Vue 2 frontend.

**Release status:** this is the GUI enabled by the current default Docker
Compose stack. It is distinct from the Vue 3 application under `src/gui-v3`.

The GUI is written in [Vue.js](https://vuejs.org/) with [Vuetify](https://vuetifyjs.com/en/).

Use the [Docker deployment guide](../../docker/README.md) for a complete
deployment. The remainder of this file covers development of this component
only.

## Project setup

Install the dependencies

```bash
npm ci
```

## Development server

Set the public frontend, API, SSE, and locale values for the backend instance
used during development. The default Docker example is available through
Traefik at `https://localhost:4443`.

```bash
export VUE_APP_TARANIS_NG_CORE_API="https://localhost:4443/api/v1"
export VUE_APP_TARANIS_NG_CORE_SSE="https://localhost:4443/sse"
export VUE_APP_TARANIS_NG_URL="https://localhost:4443"
export VUE_APP_TARANIS_NG_LOCALE="en"

npm run serve
```

## Languages

The Vue 2 interface is available in Czech (`cs`), English (`en`), and Slovak
(`sk`). English is the fallback locale. The Vue 3 interface has a larger set of
translations documented in the [Vue 3 GUI README](../gui-v3/README.md#languages).

Vue 2 locale catalogs are discovered automatically from
`src/i18n/<locale>/messages.js` at build time, so they do not require database
option entries.

## Production build

When you are ready to generate the final static version of the GUI, run

```bash
npm run build
```

The static html/js/css files will be stored under the `dist/` subdirectory.

## Testing and linting

```bash
npm run test
npm run lint
```

## Configuration reference

See [Configuration Reference](https://cli.vuejs.org/config/).

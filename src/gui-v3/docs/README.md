# Vue 3 GUI Documentation Index

**Audience:** Vue 3 frontend developers. These are implementation and
architecture references, not deployment instructions. See the repository
[Docker deployment guide](../../../docker/README.md) for the supported stack.

This directory contains implementation, status, and architecture documentation
for the Taranis NG Vue 3 GUI.

## Directory structure

```
src/gui-v3/docs/
├── README.md (this file)
├── IMPLEMENTATION_STATUS.md (main status reference)
├── migration/
│   └── README.md
└── architecture/
    ├── STATE_MANAGEMENT.md
    ├── ROUTING_AND_AUTH.md
    ├── ATTRIBUTE_SYSTEM.md
    └── UNIFIED_TOOLBAR_FILTERS.md
```

## Quick navigation

### For Project Status

- **[IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md)** — Feature,
  verification, and deployment status.

### For Architecture

- **[architecture/STATE_MANAGEMENT.md](./architecture/STATE_MANAGEMENT.md)** — Pinia stores, API service layer, and UI constants.
- **[architecture/ROUTING_AND_AUTH.md](./architecture/ROUTING_AND_AUTH.md)** — Vue Router setup, navigation guards, permissions, and SSE.
- **[architecture/ATTRIBUTE_SYSTEM.md](./architecture/ATTRIBUTE_SYSTEM.md)** — Dynamic attribute dispatcher pattern and all attribute types.
- **[architecture/UNIFIED_TOOLBAR_FILTERS.md](./architecture/UNIFIED_TOOLBAR_FILTERS.md)** — BaseToolbarFilter component, toolbar layout, and view-specific implementations.

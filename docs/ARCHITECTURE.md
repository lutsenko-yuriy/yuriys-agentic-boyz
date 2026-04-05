# Architecture

<!-- Describe how the code is organised.
     The Tech Lead and Developer agents read this file before planning or implementing work.
     Keep it accurate — update it whenever the structure changes. -->

## Overview

{{ARCHITECTURE_SUMMARY}}

## Directory structure

```
<!-- Add your project's directory tree here. Example:

src/
├── main.<ext>          # Entry point
├── features/           # Vertical slices / modules
│   └── <feature>/
│       ├── domain/     # Business logic, models, interfaces
│       ├── data/       # Storage, API, repository implementations
│       └── ui/         # Presentation layer
└── shared/             # Cross-cutting utilities

test/
└── features/           # Mirrors src/features/
-->
```

## Layers

<!-- Describe each layer's responsibilities and rules.
     Be explicit about what may and may not import from where. -->

### Domain
<!-- Core business logic. No dependencies on data, UI, or infrastructure. -->

### Data
<!-- Storage and persistence. Implements repository interfaces from domain. -->

### UI
<!-- Presentation layer. -->

## Dependencies

<!-- List key libraries and frameworks with links. -->

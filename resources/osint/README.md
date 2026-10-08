# Optional OSINT source catalog

**Audience:** administrators who intentionally import source definitions.

**Status:** optional catalog; these files are not automatically installed or
activated by the Docker deployment.

This directory contains preconfigured OSINT source definitions that can be
reviewed and imported into Taranis NG.

The sources are organized into folders by category. Each folder contains
individual JSON files and an aggregate `all.json`. Do not modify generated
`all.json` files directly.

The default refresh interval for RSS and Atom feeds is 180 minutes, with an article limit of 10.

Files ending in `_csaf.json` use the CSAF collector, which reads security advisories in
the CSAF format from a provider's metadata, a ROLIE or RSS feed, a directory, or a GitHub
repository. They refresh every 180 minutes, collect at most 100 new or changed documents
per distribution and run, skip VEX documents, and check each document's published hash
and signature. A newer version of an advisory already collected marks its news item unread
again; turn off "Resurface new versions" on a source to update its items quietly instead.
The `cert` folder holds national CERTs.

Review a source's URL, collection limit, legal constraints, expected volume,
and relevance before importing it. Importing an aggregate catalog is not
recommended for a first evaluation; start with one or two bounded sources.

> [!WARNING]
> In the current application, deleting a source can leave previously collected
> news items without their original source relation. Before deleting a source,
> record how many items it collected and decide whether that historical evidence
> must be retained. There is not yet a supported demo-reset operation that
> guarantees removal without orphaned data.

Import, refresh, retirement, historical-data preservation, and eventual
deletion are separate lifecycle stages. Do not assume deleting the definition
also deletes or safely preserves all related data.

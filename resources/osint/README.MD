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

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [v23.09.1] - 2023-09-27
### Added
* New reports (OSINT, Disinfo, Offensive, Weekly)
* Keycloak authentication support
* JSON presenter
* Email presenter
* LDAP authentication
* Support for password authentication (database), removed test_authenticator
* More product information inside the presenter to be able to use it in reports
* Password data were logged in plain text, now replaced by string CENSORED

### Changed
* In Products, display "Report type" instead of the string "Title" in row detail
* Fixed GUI shortcuts
* Collectors: better logs, fixed "Popup close" crash
* Fixed Access denied by ACL in News items (deleting Osint sources)
* Fixed MISP template
* Confidentiality not showing TOP SECRET on PDF, HTML, HTML WEEKLY templates
* TLC updated: WHITE to CLEAR, added AMBER+STRICT
* CASE INSENSITIVE search for attributes
* Fixed time zone displacement out of range error when time > 16:00 + wrong datetime evaluated in SQL queries
* Fixed error: Signature has expired
* Properly display attributes in an aggregate
* Fixed bad authentication required for the product (PUBLISH_ACCESS, PRODUCT_TYPE_ACCESS)
* Fixed bots crash, better Regex
* Added missing TOR binary to the collectors
* Improved templates
* A lot of various fixes

Thanks for the contributions: @sebix, @multiflexi

## [v21.11.1] - 2021-11-19
### Added
* Added collector management to manage.py - https://github.com/SK-CERT/Taranis-NG/issues/18

### Changed
* Docker readme: Fix URLs/Ports with switch to HTTPS by @sebix in https://github.com/SK-CERT/Taranis-NG/pull/21
* Tidied up word lists
* Re-worked proxy handling for the RSS collector
* Fixed issues with collector node and OSINT source status models and schemas - https://github.com/SK-CERT/Taranis-NG/issues/23

## [v21.10.6] - 2021-11-10
### Added
- added sample word block list for tag cloud

### Changed
- more verbose logging in the RSS collector
- usability fixes in collectors
- fixed asset group updates
- improved default templates for products

## [v21.10.5] - 2021-11-09
### Added
- authors of _Product templates_ may now use the new `Configuration -> Product types` help screen, which lists all the fields defined in a chosen _Report item type_. This simplifies the development of new product templates.

### Changed
- GUI and RSS collector fixes

## [v21.10.4] - 2021-11-08
### Added
- keycloak container (not enabled yet)

### Changed
- gui: fix news item group operations
- gui: bundle fonts
- gui: upgrade for security (breaks minor stuff, will be fixed in a later release)
- web collector: minor improvements

## [v21.10.3] - 2021-11-08
### Changed
- minor fixes and improvements across the entire project
- security patches for third party libraries
- docker:
   - deployment now includes Traefik as a reverse proxy for more convenient deployment (supports self generated, pre-uploaded, and letsencrypt certificates)
   - collectors container minimised
- complete rewrite of web collector: more robust, better support for various selectors, upgrade to selenium 4.0.0

### New Contributors
- @sebix made their first contribution in https://github.com/SK-CERT/Taranis-NG/pull/5

## [v21.10.2] - 2021-09-25
### Added
- sample templates for products (PDF, HTML, TXT, MISP)

### Changed
- multiple usability fixes across the product

## [v21.10.1] - 2021-09-25
### Added
- Initial release of Taranis NG

### Changed
- Merged multiple Taranis NG repositories into one for easier understanding and management of the project


[v23.09.1]: https://github.com/SK-CERT/Taranis-NG/releases/tag/v23.09.1
[v21.11.1]: https://github.com/SK-CERT/Taranis-NG/releases/tag/v21.11.1
[v21.10.6]: https://github.com/SK-CERT/Taranis-NG/releases/tag/v21.10.6
[v21.10.5]: https://github.com/SK-CERT/Taranis-NG/releases/tag/v21.10.5
[v21.10.4]: https://github.com/SK-CERT/Taranis-NG/releases/tag/v21.10.4
[v21.10.3]: https://github.com/SK-CERT/Taranis-NG/releases/tag/v21.10.3
[v21.10.2]: https://github.com/SK-CERT/Taranis-NG/releases/tag/v21.10.2
[v21.10.1]: https://github.com/SK-CERT/Taranis-NG/releases/tag/v21.10.1

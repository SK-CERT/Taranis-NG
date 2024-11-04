# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [v24.11.1] - 2024-11-04

### Breaking Change! (Database migration from Postgres version 13 to 16)
Please read `docker/MIGRATE_DB.md` documentation for migrate process.

### Added
- Email collector improvements #402
    - Save attachment to Taranis only if it's not another email or signature
    - Improve logging
    - Fixed bugs
    - Remove inclusion of server type in server URL
    - Fix bug in web collector
    - Limit debug output in email publisher
    - Many other improvements and fixes
- Logging improvement #351 
    - Uses logging class shared for all containers
    - Now possible to set logging level in .env
    - Fixed some f strings, some minor issues
    - Removed unused code
- Logging improvement part 2. (Collectors) #399 
    - Tidy up log types
    - Same logs for each collector (start, finish) moved to one place
    - Fixed: AttributeError: 'WebDriver' object has no attribute 'dispose'
- Add possibility delete already "used" OSINT Source Group #389
    - Now it's possible delete OSINT Source Group that has already assigned some News items. News items from this group 
      will be reassigned to default group. Before this change you can't delete "used" Group. You get error message about 
      failed delete action.
- Improve RSS collector #360
    - If downloading of HTML article fails, use feed data only.
- Improve RSS collector #345
    - Better review and content handling
    - Can handle both RSS and Atom feeds (Atom collector may be phased out whenever)
    - Improve and update code in general
    - Unified date and time of publishing
- Display "Report item type" instead of string "Title" in Analyze row details #329 
- Check if ldap authentication is used #328
    - Add check if ldap is set to be used.
- Added "Last attempt" and "Last collected" columns in OSINT sources #316
    - Added "Last attempt" and "Last collected" date columns in OSINT sources configuration view
- Add cascade delete to NEWS_ITEM releated tables #286 
    - Allow keep data in database more consistent
    - Simplifies "maintenance" of the database (if you want manually delete some old data)
- Use secrets for Docker #211 
    - Replaces plaintext passwords used for Docker with Docker secrets
- Docker secrets - Keycloak #293
    - Added Docker secrets functionality for Keycloak
- Noto fonts tidy up (presenter) #296
    - Decreasing container size from 710 vs 589 MB
    - Faster build
    - We go back to initial revisited list of installed languages (before font-noto-all update)
    - Based on most used, if we miss some we can still add it
- Delete confirmation window #243 
- Add confirmation to Publish button #270 
    - Add confirmation to publish product button
    - Add generic MessageBox component
    - Update slovak translation
- Replaced ConfirmDelete component to universal MessageBox #271 
    - Just replaced ConfirmDelete component to universal MessageBox, no other functional changes
    - Old ConfirmDelete component deleted
- Add Czech translation #222 
    - Added new CZ translation
    - Fixed mistakes in ENG translation
    - Added possibility to set language in .env (works only before login and if other methods to determine language fail)
- Added CWE attribute #209 
    - Added special CWE attribute
    - Frontend button for reload
    - Updated README files
    - Created migrations
    - Excluded migrations folder from flake8 check, because it was too annoying
- Attribute description - CWE #312 
    - Adds attribute description to report item. This is useful for CWE, CVE, CPE and other attributes which have value description. This is also usable in presenter - for now just for CWE as it is new and does not brake anything, but in future it is possible to improve this to include CVE, CPE or other.
- Collectors update (Limit for article links, logs, fixes) #221     
    - Better logs: article link progress for current page
    - Added optional "Limit for article links" setting (WEB, RSS, ATOM). You can process only first N articles. Usefull on sources with big article count (when you don't want kill collector)
    - Display "Page limit reached" only if "Pagination limit" was set
    - Fixed crash when article items are parsed ok but link is not found (java scripts, not fully dynamicaly loaded page)
    - Removed one duplicity log about parsing article link
    - Removed from RSS/ATOM date check condition (now it works in the same way as in WEB collector, now it's possible collect initial source state)
    - Fixed ATOM author element that can exist/miss in header/entry
- Add logging messages to mailer, improved SMTP communication #213 
    - Added logging messages to email publisher
    - This will hopefully eliminate this issue: SMTP sender refused, unable to reconnect.
- PDF report update #205 
    - Fix broken AFFECTED SYSTEMS field (affected by later update)
    - Add support for multi-line in DESCRIPTION, AFFECTED SYSTEMS & RECOMMENDATIONS fields
    - Change format of AFFECTED SYSTEMS field in Vulnerability report (text -> text area)
- Remove false translation warnings, correct some tooltips, don't try translate user strings #200 
    - Added & corrected translation for some tool-tips (removes warnings in console)
    - Added translation configuration for navigation bar (don't show false warnings, possibility to translate system and not user named sections)- 
- Allow store CVSS as number (quick need for reporting) #203
- Add support for language setting per user #202 
- Cancel the same GET request #204 
    - Cancel the same GET request (not yet processed) on some main screens.
      This prevent blinking, dalayed loading old data. Need solve cancel backend actions too (database selects..)

### Fixed
- Fixed: first key is acting as shorcut in empty editor #387 
    - Fixed: first key is acting as shorcut in empty editor component (e.g Assess Detail Comments)
    - Added: set focus directly to to Assess Detail Comments after switching to Comments tab
- Fixed keycloak logout #381 
    - Fixed keycloak logout (was not possible logout from system)
    - Fix not working Keycloak build/deploy (download link was not valid anymore)
    - Keycloak upgrade 15.0.2 -> 25.0.6
    - Added support for new Keycloak versions (>= 17.0.0, url path was changed)
    - New realm export (old renamed to realm-export_v16.1.1.json)
    - New modern keycloak login screen (old one was broken, not updated for long time, we will use native keycloak login, nicer and support all new things)
    - Updated documentation for latest Keycloak versions
- Fix keycloak secrets #378
- Fix double scrollbars in Analyze & Publish screens #375 
    - There is a very nasty bug: when you open analyze screen for a second time, two scrollbars are shown.
- Fix error: Property or method "editorData" is not defined #369 
    - Error: Property or method "editorData" is not defined on the instance but referenced during render. Make sure that this property is reactive, either in the data option, or for class-based components, by initializing the property.
- Fix: SAWarning: Coercing Subquery object into a select() #352 
    - Fix for this endless warning :)
- Fix: OSINT sources open first OSINT group screen #350 
    - When you open OSINT sources multiple times you get first Osint groups screen which you must first close to continue work
- Fixed bugs in Product and Report screens (endless status, errors mesages) #348
    - Empty type cause endless progress status without any error message
    - If any error occurred and you return back or open another screen a previous error message stay on the screen
- Fix sorting report atrributes to respect user order #343 
    - Fix sorting report attributes to respect user order.
- Fix error for user with no organization #335
    - Fix IndexError: list index out of range when user is not part of any organization
    - Docstrings
    - F-strings instead of str + var + str
- Fix: WARN: FromAsCasing: 'as' and 'FROM' keywords' casing do not match #333 
    - Remove 2 warnings from GUI building
- Fix: Manually creating news item can produce error #330 
    - Creating news item manually with empty "Content" field can cause: 500: Internal Server Error and some generic user message. User doesn't know what is wrong. Normally is possible store empty Content but user must do some interaction first (write and delete text)
- Fix LDAP env variables #326
    - LDAP variables added to .env.example. LDAP_CA_CERT_PATH is not mandatory because it defaults to default location, so if not set, it won't printout warnings, but still can override default path when set.
- Fix missing value_description definition #325
- Fix: run collector always in new class #322 
    - If scheduler or source save action run on the "same time" local variables start overwriting.Collect function can run multiple times in same class instance in some circumstances. Result can be wrong category, bad source update times and it start mixing source parsing rules across various sites -> damaged news items!!!
      This update fix:
    - After some time scheduler cross runs
    - Collectors refresh on source save and already running scheduler
    - Applying bad parsing attributes to another source !!!!
- Fix error when adding CWE to report item #324
- Fix error: '': No such file or directory" on mapped folder #287 
- Fix: Display the description in the OSINT source groups grid #295
- Fix non working ACL for Product Types #249 
    - When you set ACL for Product Types in selection combo you get all types. This is wrong behavior. Now you can see only your an "public" types.
- Fix errors: t is null & semicolon #252 
    - TypeError: t is null (in console on Asses)
    - Error by parsing language (Unnecessary semicolon)
- Fix selector for some element types #263 
    - Multiple selector was not working (find_elements_by XPATH, NAME & CLASS)
- Fix upgrade db error (caused previous PR) #223
    - Multiple head revisions are present for given argument 'head'; please specify a specific target revision
- Fix upgrade db error 2 (caused previous PR) #224
- Fix: disable shorcuts on text/textarea fields (prevents typing text) #207 
    - In Assess, create report from item and you type N in description field -> all is canceled and it creates new report again
- Fixed bug in chrome driver: unrecognized proxy type: MANUAL #214 
    - This fix crash on some special OSINT source configurations
- Dark theme fix (bad colors) #219 
    - Report item attributes were unreadable (bad background hover color)
    - White text on white background + unified richtextbox components
    - Initial help text in richtextbox was unreadable (bad color)
    - Fixed white color on toolbars
    - Keyboard shortcuts
    - Unified richtextbox toolbars (same order of tools)
    - De-duplicate styles in centralize.css
- Fix crash when user try create new user with filled password #130 
- Fix some small code issues from last PR #198 
    - Small code beautify (use of .keys(), comments, try catch.. )
    - Rss collector now import just items with published date > last previous crawl (based on atom collector logic)
    - Better unique temporary names in pdf presenter (fixed possible overwriting temp files)
- Message product preview fix #244
    - Fix preview of message in product creation. Now it displays as plain text.
- A lot of various small fixes

### Changed
- Remove redundant code #404 
    - Remove code that is already called in main base collector
- Remove marshmallow-enum #403 
    - Remove unnecessary and deprecated library marshmallow-enum. Enum is part of marshmallow since version 3.18.0
- Removed extra step in web driver exiting #400
- Upgrade GitHub actions warnings #386 
    - Warning: The following actions use a deprecated Node.js version and will be forced to run on node20: docker/login-action@v2, docker/build-push-action@v3.
- Upgrade GitHub action: checkout@v2 -> v4 on lint #385
    - The following actions uses node12 which is deprecated and will be forced to run on node16: actions/checkout@v2.
- Remove duplicate env variables #377 
    - Remove duplicate env variables declared in both docker-compose.yml and individual dockerfiles: NGINX_WORKERS, NGINX_CONNECTIONS, WORKERS_PER_CORE
- Remove old Python 3.8 references #374 
    - Git doesn't run the 3.8 linting (tests are faster)
- Don't try translate news items categories on report items screen selector #370 
    - It produce false warnings on text that should not be translated
- Use text format in Content for manually entered news items #361 
    - Create manually news item content with text format. Use same format for content as other collected news items from various source types. Before html now pure text.
      Problem was that content viewer show also html tags from text, These html tags were also indexed.
    - Update Slovak language
- Removed .env password support #344
    - Removed .env passwords, now are only Secrets supported
    - Removed docker warnings: variable is not set. Defaulting to a blank string.
    - Removed warning: the attribute version is obsolete, it will be ignored, please remove it to avoid potential confusion"
- Opitimalization: tables relationship (join) #334 
    - This commit add some speed up with modifying "lazy" parameter in db.relationship. Mostly is added JOIN type. This reduce a quantity of database requests from framework resulting more user gui fluently work and reducing waiting times on some actions.
- Update value desc only if found #327
    - Another fix of value_description. It is updated only if found in input data.
- Ignore custom settings files and templates #323
    - Just a folder for custom templates with its content ignored in .gitignore and the same for dynamic traefik yml files
- Update/rewrite slackclient to 2.9.4 #318 
    - Docker was unable to build - dependency conflict by websocket-client by upgrading selenium
- Correct date formats #319 
    - Corrected wrong formatting: %H:%M:%s -> %H:%M:%S (%s doesn't return seconds)
    - For WEB collector show nice published date for news items (no need microseconds, looks ugly)
- Language update (previous messagebox commit) #274 
    - Fixed Czech translation
    - Removed some old unused strings from previous commits
- Link deduplication in product #210 
    - This deduplicates links in across multiple report items, saves them in product and edits text accordingly. It makes creation of products easier.
      This also enables to have multiple custom vulnerability report with this functionality, because it works as long as the type of the report starts with "Vulnerability Report" string.
- A lot of components update (bumping to new versions)

Thanks for the contributions: @multiflexi, @Ximelele

## [v23.12.1] - 2023-12-06

### Breaking Change! (Only for Docker users who use customized or new report templates)

**Background:**
The Presenter Docker maps the `/app/templates` directory to the `presenters_templates` container.
This overrides the original `/app/templates` files with user modifications. When new or updated templates arrive with a new version, they stay hidden due to this mapping.

**Solution:**
Remap user-changed reports to the `/app/templates/user_templates` directory. 
Simply update the old template path in `Configuration / Product Types`: e.g., `/app/templates/file.html` -> `/app/templates/user_templates/file.html`

### Added
- Added variable `TARANIS_NG_AUTHENTICATOR` to `docker.yml` and `.env` (default value "password").
- Improved regex bots (logs, multiple regex, disable bot, don't try to create duplicity values...).
- Migrated COLLECTORS, PUBLISHERS, BOTS, and PRESENTERS to the latest Python 3.12, Alpine 3.18, and latest Python modules.
- Migrated to the new PDF presenter (WeasyPrint, before deprecated PDFKit).
- Migrated Collectors to the latest Selenium version.
- New SFTP publisher (Paramiko).
- If more users work on the same report item -> update locked field with a new value.

### Changed
- Fixed the issue when the message title or body is missing in the publisher.
- Fixed LDAP crash (moved cert path to env variable `LDAP_CA_CERT_PATH`).
- Disabled keyboard shortcuts in News Items comments editor.
- Fixed saving comments in News Items (was not working).
- Fixed the display of report item details on the product (was empty before).
- Fixed some small GUI crashes (null .link, fast report item open).
- Fixed a bad condition in bots (not processing records that were issued in 00 seconds).
- Fixed blinking/jumping in Assess (data reload).
- Replaced PNG picture in the template with a new fixed SVG image that finally works everywhere.
- Updated PDF template.
- Don't show/send the user password field to the backend (report items).
- Fixed deleting/updating items on the report item.
- Bot container was missing a restart policy.
- Fixed bad mapping of user report templates.
- Disabled log duplicities on the screen if SYSLOG is disabled.
- Fixed dialog centering based on scrollbar range and not on screen size.
- Improved temp file names in the PDF presenter.
- Scheduled actions in Collectors are more exception-resistant.
- A lot of various fixes.

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
* Fixed bug when new templates stay hiden due wrong docker mapping
* A lot of various fixes

## [v22.12.1] - 2022-12-16

### GUI
* Analyze: new feature - side by side view
* Assess: Show number of selected news items
* possibility to NOT set hotkeys in user profile
* taranis-logo.svg now has colors

### Collectors
* fixed crash when processing an empty link in RSS
* fixed proxy settings parsing ; fixed setting proxy for firefox headless browser
* fixed chromium driver initialization; added more logging for web driver initialization

### Logging
* more verbose logging in cve/cpe import
* removed useless warnings from logs

### Wordlists
* Added default wordlists for the English and Slovak language
* added option to download wordlists from URL; added default downloadable wordlists

### Other changes and fixes
* build: added Github action and pre-commit hook for linting
* certain packages upgraded for security
* refactor some code to create "shared" module with data models
* various other fixes and updates across the code base

## [v22.05.1] - 2022-05-17

### Added
* gui: keyboard shortcuts: use delete for deleting news items by @sebix in #46
* assess: add noreferrer attribute to source links by @sebix in #44
* readme: add alternative source for stop lists by @sebix in #34
* gitignore: add more rules and make others more generic by @sebix in #25
* Document keyboard shortchuts by @sebix in #31
* doc harware requirements: add cpu cores by @sebix in #75

### Changed
* fix bare except clauses by @sebix in #42
* Assess: Do not reload news items when in selection mode by @sebix in #40
* fix gui shortcuts in assess by @sebix in #56
* Security upgrade lxml from 4.5.0 to 4.6.3 by @sebix in #47
* Keyboard fixes and new shortcuts by @sebix in #52
* gui: remove unused vue logo by @sebix in #58
* GUI Keyboard improvements by @sebix in #57
* use log_manager by @b3n4kh in #62
* refactor auth_manager by @b3n4kh in #63
* cleanup ftp publisher code by @b3n4kh in #64
* monkeypatch before init by @b3n4kh in #65
* shortcuts: ignore keypresses in search field except Escape by @sebix in #76

## [v21.11.1] - 2021-11-19

### Added
* Added collector management to manage.py

### Changed
* Docker readme: Fix URLs/Ports with switch to HTTPS by @sebix
* Tidied up word lists
* Re-worked proxy handling for the RSS collector
* Fixed issues with collector node and OSINT source status models and schemas

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


[v24.11.1]: https://github.com/SK-CERT/Taranis-NG/releases/tag/v24.11.1
[v23.12.1]: https://github.com/SK-CERT/Taranis-NG/releases/tag/v23.12.1
[v23.09.1]: https://github.com/SK-CERT/Taranis-NG/releases/tag/v23.09.1
[v22.12.1]: https://github.com/SK-CERT/Taranis-NG/releases/tag/v22.12.1
[v22.05.1]: https://github.com/SK-CERT/Taranis-NG/releases/tag/v22.05.1
[v21.11.1]: https://github.com/SK-CERT/Taranis-NG/releases/tag/v21.11.1
[v21.10.6]: https://github.com/SK-CERT/Taranis-NG/releases/tag/v21.10.6
[v21.10.5]: https://github.com/SK-CERT/Taranis-NG/releases/tag/v21.10.5
[v21.10.4]: https://github.com/SK-CERT/Taranis-NG/releases/tag/v21.10.4
[v21.10.3]: https://github.com/SK-CERT/Taranis-NG/releases/tag/v21.10.3
[v21.10.2]: https://github.com/SK-CERT/Taranis-NG/releases/tag/v21.10.2
[v21.10.1]: https://github.com/SK-CERT/Taranis-NG/releases/tag/v21.10.1

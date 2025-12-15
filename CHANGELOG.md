# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [v25.12.1] - 2025-12-15

- Increase version to v25.12.1 #950
    - version bump to 25.12.1

- All News Item category, Available Wordlist API #947
    - All category for News Items - respects ACLs
    - Fix error when users which are not admins do not see word lists in User Settings
    - simplified request.args.get()
    - some generic "from import" is exactly defined
    - fixed osint_source_group_id type (it's GUID)
    - added possibility use color in navigation buttons
    - All sources and Uncategorized buttons have now own colors (blue and grey)

- Small fix #949
    - crash with same Resource name exists

- Optimise news-items-updated events #948
    - don't trigger news-items-updated & remote_access_news_items_updated event if no new items were collected (no useless screen blinking in Asses screen each time when crawler finish his job)
    - fixed crash when executing remote_access_news_items_updated with no IDs
    - ruff checks + optimize code

- Vulnerability report css style cleanup (html, pdf) #946
    - Replaced bootstrap.css (196KB) with main.css (3KB) to reduce legacy bloat and eliminate numerous [WARNING]s in the presenter log when rendering PDFs. Visual style remains identical.
    - Merged custom.css into main.css.
    - pdf_template.html now uses only the smaller main.css. PDF rendering speed increased.
    - template.html: sorted styles for clarity; improved checkboxes.
    - No other visual changes—pure cleanup!

- Fix attribute sort #945
    - Fixed sorting on attributes:
        - bad sorting "Sort values from newest" - was sorting by last updated value, after processing sort was impossible show original order
        - wrong behavior for: "Show my values first then others" - opposite working (your values were last)

- Update stop lists #934
    - Update English stop list
    - Add Czech stop list
    - (for update you need reimport old, use Delete existing words to avoid duplicity)

- Comment icon in News items #933
    - Add comment icon to asses to indicate comments presence. It allow user identify what items have comment.

- Osint sources screen fixes, Db constraints.. #912
    - fix: Osint sources screen, collectors are not refreshed on node combo change (multiple nodes case)
    - add: in collectors node delete action remap osint sources to next node (avoid loosing sources, allow delete node)
    - add: delete unused parameters after node delete action (we don't delete them to this moment yet, dead records)
    - add: cascade delete for all nodes (7x)
    - add: show warning on unknown db_migration.py command
    - remove ID from collector combo
    - remove some dead data initialization in OSINT source import
    - add: better error messages on delete action in collector nodes, not just generic error message (show backend error on frontend)
    - changed some function names (misleading names)
    - removed unused code
    - again ruff checks on not processed files

- States #908
    - added states to entities report item and product
    - added editing of states
    - added assigning states to entities
    - fixed minor bug in dark mode
    - fixed translations, added CZ translations

- Fix: Request Line is too large (4XXX > 4094) #923
    - This is quick fix. We need change way of sending long jwt token via path in url and put it inside body
    - In gunicorn we change default value 4094 to 8192

- Fix in message Jinja filters #922
    - Jinja filters were loaded too late causing templating error when used in message presenter

- Fix Jinja for plaintext #916
    - remove autoescape for plaintext
    - fixes rendering of symbols like ' or "
    - fixed typo

- Support for ACME #909
    - added config for ACME
    - works with custom CA
    - added example of TLS configuration

- Fixed selection color on dark theme #907
    - records selection (News, grouped News, Reports, Osint sources)
    - unified selection color

- Remove unused vue sources #897
    - some unused .vue and .js sources were removed

- Fixed refresh on News items group actions #896
    - Refresh on News items group action was not working (non existing event: update-news-items-list) Nobody noticed it yet?

- Crash on new report when you click on some sub aggregate item #895
    - Fixed: AttributeError: 'NoneType' object has no attribute 'news_item_data'. It was caused by calling showItemDetail in NewsItemSelector.vue where was send wrong parameter. Now is called child function that emit correct parameter. (It was crashing when you create new report, add some news item aggregates and then click on some on some sub aggregate item)
    - Tidy up code in NewReportItem

- Add 'Hide source link' option to News items screen #883
    - move 'Show source link on news items' from user settings to News items screen icon
    - will be stored in local storage as other options on the page

- Additional fix for #784 Data providers #882
    - crash fix
    - fix ruff

- Data providers #784
    - added API configuration for CWE, EPSS, EUVD, NVD, CPE
    - renamed local AI models to AI models
    - small fixes

- Fixed: No module named 'langchain.chains' #881
    - Fixed: No module named 'langchain.chains' after upgrading langchain from 0.3.27 to 1.0.1 in /src/core

- Show/hide news items reviews #875
    - adds button to hide or show review of all news items to filter toolbar
    - stays persistent across categories

- Fix multiple AI buttons on Analyze form#874
    - Each AI button on Analyze form now has own status and animation (before they share one status)

- Tag cloud improvements #873
    - Optimise TAG cloud creation (speed)
    - Add "-" char inside TAG words (now CVE looks better ;-)
    - Better split when creating TAG words (now splitting on white space chars, before failed on TAB, NBSP)
    - Fixed TAG word creation (don't use HTML tags as words)
    - Fixed background color of TAG cloud on dark theme
    - Added new user setting: Colorful tag cloud
    - small GUI changes on Dashbord screen
    - Added support for delayed setting loading (isInitializedSetting, settings-loaded)
    - Ruff precomit checks

- Small migration fix #872
    - Fix: cannot drop table user_profile because other objects depend on it. Constraint user_profile_id_fkey on table "user" depends on table user_profile

- User settings #867
    - Added support for generic global/user settings. We have big need of user customization and this simplify future process. Developer now just add setting definition and can immediately use it in code by (get_setting - python, getSetting - js, vue), No other coding.
    - Added new table settings_user that is sub-table for settings. Each user has own records. There are global and user settings now.
    - New table user_word_list (before user_profile_word_list). All user worlists are migrated
    - Some API optimizations in old settings code
    - Fixed news item keywords highlighting in dark theme
    - Heavy corrections in code (ruff checks)
    - Fixed jinja2.exceptions.UndefinedError: 'dict object' has no attribute 'baseScore' - added default values for empty CVSS
    - Added new user setting: Show source link in news items (default True)
    - Fixed: In agregate news items content was displayed html code instead of formatted text
    - Some small source refactoring

- Additional fix to #854 #855
    - Additional fix to #854 (Fixed filter bug in 'Select Report Items' in Publish screen)
    - Select Report Items from Remote Nodes show local reports

- Fixed filter bug in 'Select Report Items' in Publish screen #854
    - Fixed filter bug in Publish screen when you use 'Select Report Items' and previously you use 'Select Report Items from Remote Nodes' dialog in Analyze screen. Selector start show just REMOTE reports until you hard reload the page

- Fix plaintext in collected content #853
    - Fix saving plaintext as HTML if RSS scraping returns raw text.

- Fix 'NewsItemData' object has no attribute 'content_plaintext' + Add review for title if it's empty #845
    - Fixed 'NewsItemData' object has no attribute 'content_plaintext' (caused by previous changes)
    - replaced HTTP codes constants with readable enumerator
    - Small TimeZone fix
    - In WEB collector use beginning of the review for title if it's empty
    - Decreased waiting time for find element in web collector from 15 -> 7 sec

- Add HTML display support for WEB-collected news items #844
    - Added HTML content support for WEB-type collected items
    - Works only on new items; old crawled text remains plain text (losing line breaks)
    - Added extra strip() step to remove_empty_html_tags output — removes useless leading and trailing whitespace
    - Remove empty html tags on manual user news item input
    - New function text_to_simple_html for future using (formatting other collectors content to display properly line breaks in news feed)

- Fix not working report items
    - Fix not working report items in Analyze (caused by #831 HTML News items)

- Exclude html tags from new items indexing and some mastodon fixes #842
    - mastodon publisher: fixed crash on empty status
    - mastodon publisher: add skip message instead failed post
    - don't store html tags for new items searching

- Small fixes #841
    - fix broken templates\template_osint.html (bad merge?)
    - small Import optimizations
    - remove empty defaults from parameters
    - Use Tor: added default value, read setting with read_bool_parameter
    - revert id names changes in news_item.py (crashing, not complete)
    - Code refactoring (ruff checks)

- Fixes #839
    - fixes of issues caused by #831

- Store manually-entered news content as HTML #840
    - Store manually-entered news content as HTML instead of plain text.
    - Add `<u>, <s>` to allowed tags in HTML sanitizer.
    - Code refactoring (ruff checks)

- HTML in news item content #831
    - Sanitized HTML may now be in news item content
    - introduced new parameter for RSS collector - PREFER_SCRAPING, tries to scrape web from feed link every time.
      Otherwise, feed link is only used as last resort if no summary and content is available in feed
    - improved logic for web scraping feed links - scrapes `<p>`, if no `<p>` are found, tries `<pre>`, if no tags are found, treats data as plaintext
    - updated OSINT sources
    - docstrings, making ruff happy

- Fix bad `<div>` tags on OSINT template report #830

- Djlint #828
    - added linting of Jinja templates - passes
    - formatting is off
    - added badges of used tools and libraries

- MESSAGE Presenter: added support for custom attachment file names #829
    - Introduced new parameter for specifying attachment file name.
    - Defaults to `file_YYYYmmddHHMMSS` if left empty.
    - Supports static strings or Jinja templates (e.g. `file_{{ data.product.title }}`).

- Some corrections of templates (formatting, fixes) #803
    - fixed some broken templates (previous changes)
    - fixed CVSS field in OSINT Report template
    - restored JINJA formatting in code (previous changes)
    - fixed some possible crashes on templates (missing fields)
    - better display of array values

- Minor fixes #802
    - Just some minor fixes including docstrings and type annotations

- side-by-side view: adjust news panel behavior and fix ESC handling #801
    - Show news item only on the right side of the screen in side-by-side mode (before in fullscreen). This allows users to read/copy news while writing a report simultaneously.
    - Fixed ESC key handling in side-by-side view: pressing ESC now closes only the news panel, not also the parent report.

- Improved templating #800
    - improved security of Jinja templating - uses only files in predefined directory
    - added Jinja filter for TLP colours - also modified templates using it
    - refactoring of code
    - other fixes, mainly annotations, docstrings

- Fixing run and conf files #799
    - fixed formatting
    - slight refactoring
    - added docstrings
    - added missing __init__.py

- Basic formatting #798
    - This adresses following in non Python files:
        - missing newlines at the end of the file
        - useless whitespace in files
        - some basic Jinja HTML formatting

- uv and ruff in GitHub Actions #797
    - uses uv and ruff for GitHub Actions
    - ruff should fail because the code is not formatted properly - this will be addressed in following commits

- Use uv, pyproject.toml #783
    - uses uv instead of pip for container building
    - uses pyproject.toml instead of requirements.txt

- Add pyproject.toml and ruff #782
    - instead of Black, Flake etc. use just ruff, it is fast and all-in-one
    - add pyproject.toml for configuration

- Jinja template loading secured #759
    - Adresses #725 CESNET pentest: Arbitrary file read by /config/product/types
    - PDF is typeset without temporary files
    - unified Jinja template path handling for all presenters

- Enable HTTP/3 #760
    - requires open UDP port 443

- Bump pre-commit plugins #781
    - updated pre-commit plugins versions

- improve English translations #753
    - English i18n file has been modified for better English.

- Fixed TAG CLOUD ignoring stop words #752
    - fixed bug that TAG CLOUD doesn't take in account stop words
    - remove redundant .distinct() from TAG CLOUD query (there is already .group_by)
    - remove SQL duplicity logs when SQL debugging is ON
    - web collector added warnings: "Element found, but text content is empty", "Element not found" that can help you find wrong defined selectors
    - web collector: changed rest of functions and removed @classmethod attribute. Now is unified

- GUI improvements #743
    - password and API key hiding with reveal button
    - added translation strings
    - added tooltips for some icons - delete, edit...

- Add max_cvss to product #748
    - Add maximum value of CVSSs from reports to product similarly to TLP.

- Disallow Crawlers #741
    - added robots meta tag
    - added robots.txt

- Small AI changes #742
    - Allow run model when no news items are attached to report (just log this action)
    - Show better error message on backend in case of problems with LLM connecting
    - Name changed: AI Provider -> Local AI model
    - Updated documentation
    - Added animation when AI prompt is running
    - Don't run another request when AI prompt is already running

- Small docs changes #740

- Documentation tidy-up #739
    - Added AI-related documentation
    - Updated existing documentation
    - Created additional help file howto.md – guides for using Taranis NG to perform specific tasks
    - Main README.md kept minimal: overview only; Docker-specific instructions separated to avoid mixing content
    - Management script help moved to howto.md (unrelated to Docker build process)
    - Removed duplicate CPE upload section from main and Docker READMEs — full version retained in howto.md
    - Removed obsolete demo files from Docusaurus (only outdated examples, no active content)
    - Renamed folder doc › docs (all documentation will reside here)
    - Fixed broken taranis-logo.svg in assets (may still be unused)

- Optimize case-insensitive search performance #733
    - optimize case-insensitive search performance: func.lower() + .like() -> .ilike()
    - optimize code

- Login page is visible for logged user #732
    - Fix #729 Login page is visible for logged in user
    - This should not be visible and should just redirect user to dashboard page.

- Translation strings tidy up #731
    - Language strings have been tidied up (most 5 repeated strings).
    - By changing just 5 strings, you can now translate the app in over 100 places.
    - Translation has been simplified by reducing the word count by 113.

- Add AI support for creating report items - Part 2 (GUI configuration) #730
    - added GUI for AI configuration

- Improve security part 1 #728
    - removed unused code
    - port 5002 (or whatever user set) was open to internet, it is available only from localhost now
    - added permanent redirect to HTTPS, HTTP response code 308

- Add AI support for creating report items - Part 1 #727
    - add support for creating AI summaries or other text processing. It's based on user defined prompt that process added news items and AI generated result is filled to the text field.
    - add database table (AI_PROVIDER) where are stored AI connections (openai, ollama supported)
    - in Configuration / Report types you can assign AI + prompt to specified report item attribute
    - in Analyze you can see now on defined report item attribute AI button. Pressing it will process added news items and fill output to text field
    - this is just 1. part. There is need add settings screen to edit AI providers and documentation. For early testing you can insert some values to ai_provider table and then you can see AI things. Example for local Ollama server:

        `INSERT INTO public.ai_provider ("name", api_type, api_url, api_key, model) VALUES('Ollama - llama3.2:1b', 'openai', 'http://localhost:11434/v1', 'none', 'llama3.2:1b');`

- Improve news item content display #715
    - Improve displaying of scraped content in news item - respects newlines

- Update Alpine Linux #714
    - Bump Alpine Linux to 3.22

- Improved collector behaviour #690
    - better HTTP error handling
    - now possible to parse multiple articles on single Web page

- Improve use of objects #670
    - No new features, just refactoring and using objects instead of parameters.

- minor GUI improvements #681
    - Show item type instead of static Title string in Configuration for bots, publishers and products.

- Added to Message presenter PDF template attachment #686
    - Added to Message presenter PDF template attachment
    - Added possibility preview message attachment by holding Ctrl key
    - Unify all modules (presenter, publisher, collector, bot) parameter_values storage with the same name and meaning. Changed parameter_values_map, parameter_values -> param_key_values. Now we can use shared functions between all modules. Also this fix same name issues for various object types (class object vs dictionary types). It was misleading.
    - Added message if there is no data for preview (before application crash in this case)

- Web Application Manifest #685
    - Added manifest, icons and screenshots
    - localized to EN, CZ, SK
    - fixed naming of Taranis NG to be consistent

- Fixed missing Enter/Assess button #684
    - Fixed missing Enter/Assess button. Button was referenced by index and functionality hides incorrect object based on user rights.

- fontTools is ignoring global logging settings #683
    - Fix for fontTools module which is ignoring global logging settings and puts garbage into the logs

- Add WARNING_INTERVAL to non-RSS sources #680
    - Add WARNING_INTERVAL parameter to non-RSS OSINT sources

- Add WARNING_INTERVAL to RSS sources #679
    - Add WARNING_INTERVAL parameter to RSS OSINT sources

- Correct deprecated jwt.decode() in python-keycloak #674
    - There was change in jwt.decode() function by upgrading python-keycloak library

- Fixed error message in Bots (master_id) #673
    - Fixed error message in Bots: cannot access local variable 'master_id' where it is not associated with a value. It was caused previous commit.

- Fixed authentification for collectors when exists multiple nodes #672
    - Fixed verification for collectors in case when more nodes share the same API_KEY. Warning: "Collector ID does not match"

- Fixed Core logger wrong SSE prefix #671
    - Removed prefix (SSE) in logs that display on wrong places.

- Replace deprecated ExpandedPyMISP with PyMISP #669
    - Fix pymisp bump from 2.5.10 to 2.5.12

- Fix error in Bots: ModuleNotFoundError: No module named 'bs4' #668
    - Fix error in Bots: ModuleNotFoundError: No module named 'bs4' (BeautifulSoup) due moving print_news_item to news_item.py.

- Fix error in Presenters: ModuleNotFoundError: No module named 'bs4' #654
    - Fix error in Presenters: ModuleNotFoundError: No module named 'bs4' (BeautifulSoup) due moving print_news_item to news_item.py.

- Prefix in Collectors logs (proxy, fetch feed) #653
    - Add missing prefix for proxy property in Collectors log
    - Add to RSS collector Exception handling for fetch feed. This also add missing prefix in logs

- Fix Collector Content debug print & Tuple Error, Keycloak Auth #652
    - Fixed debug print for new item’s Content property (previously displayed as an array of strings; issue introduced in the last PR)
    - Fixed Keycloak authentication compatibility with the latest Keycloak versions
    - Fixed collector error: An unhandled exception occurred during scheduled collector run: '>' not supported between instances of 'tuple' and 'int'

- Improve log clarity in Check-if-modified #651
    - Fixed missing source name in Check-if-modified log message. In multithreaded execution, adjacent log lines made it difficult to associate messages with their respective sources.

- Fixed errors when starting or restarting the entire Taranis (delayed start, between containers) #643
    - Fixed connection error in "Bots/SSE" and "Collector/Report status" when starting or restarting the entire Taranis. Core is not ready yet, and we need to connect a little bit later. Now the start logs are error free.
    - Added to logs: "Awaiting initialization of CORE (timeout: 20s)" message to indicate background activity for delayed processes.

- Fix Bots schedulling and logger issues #642
    - Minor logger fixes for Bots.
    - Fixed Bots scheduling, until now they run only once at beginning (scheduler was being overwritten; threading added, same approach as in Collectors).
    - Bots SSE now remains active after losing Core connection or after unexpected crash (attempts reconnect every 30 seconds).
    - Removed "next run" info from the "Collection finished" message. Since the job is still running and the information contains old value -> this is misleading. This value is increased only after job exits.
    - Moved time_manager, log_manager to shared (no more same code for each module, duplicity, not updated versions)

- Improved logging #641
    - improved logging (again and hopefully correctly)
    - refactored some collectors

- Unified Configuration #636
    - Unified Global Configuration and My Assets module configuration. Now everything is under a single Configuration. All permissions and rights remain unchanged and work as expected.
    - Moved the Configuration menu item to the far right.
    - Fixed bug where external users couldn’t be edited without entering a password.
    - Corrected access rights to Settings.
    - Fixed typo

- Added coloring to OSINT sources records #635
    - Added coloring to OSINT sources records: Green - Ok, Gray - disabled, Red - error, Orange - not collected for N days
    - Added default value 30 days for "No new data warning interval in days (0 to disable)" parameter in collectors
    - Fix bug caused by #613 Add support for default values when creating new Collectors… Opening existing record add default values too

- Preparation for user settings table (Part 1) #627
    - preparation for user settings table (replacement for user profile)
    - remap hotkeys to user table (before to profile table)
    - hide OPTIONS requests in gunicorn core log

- Add support for default values when creating new Collectors, Bots … #613
    - Add support for default values when creating new Collectors, Publisher presets, Bot presets and Product types
    - Automatically select first node and first type on New action

- Improve web collector #612
    - Improve collector scheduling (cancel old to avoid parallel running of the same tasks)
    - Add check for changes
    - Better logs

- Fixed crash by creating external user #607
    - Creating external user was not working

- Add cascade delete to User, Organization and Word_list #604
    - Add cascade delete to User, Organization and Word_list to able delete these records without errors. Some deletion logic is still maintained by Taranis.
    - Fixed Issue #96: Deleting organization with associated accounts fails

- Remove yarm.lock file from doc directory #603
    - Remove yarm.lock file from doc directory due a lot of security alerts (npm will be used)
    - Docusaurus is still not used yet.
    - Removed 71/108 alerts

- Better whitespace processing in Title, Review when processing RSS, Web sources #602
    - Better whitespace processing in Title, Review when processing RSS, Web sources. Corrected also manual input
    - Title decreased to max 200 chars (based on readability and max length usage in real world) This avoid creating very long Titles that spam user screen
    - This update also correct nasty Title and Review line breaking in docker debug logging when text contains 'bad' chars

- CSP update #600
    - Added frame-src and frame-ancestor to CSP.

- Added messages to HTTP response status codes #601
    - Added messages to HTTP response status codes (were empty)
    - Fixed crash on reading empty EMAILS_LIMIT parameter

- Hide password in configuration #590
    - Fix issue #134 Hide password in configuration
    - based on key type name because it's dynamic building component

- Improved HTML sanitization, enhanced input validation across collectors (refactored shared functions) #589
    - Introduced a common module for functions shared across Docker containers.
    - Unified smart_truncate() function for all collectors (review field).
    - Replaced regex with BeautifulSoup for HTML sanitization.
    - Unified strip_html() function for all collectors.
    - Unified print_news_item() function for web and RSS collectors.
    - Improved input sanitization for manual input of news items (HTML tags, scripts, excessively long reviews, etc.).

- Added posibility manualy regenerate all parameters + Fix issue #572 #587
    - Added: possibility manually regenerate all parameters (just run in core: python db_migration.py regenerate)
    - Fixed: Issue #572: Error when manually run migration on the already latest version

- Email sender filtering #577
    - Added optional filtering for email collector based on sender of the email.
    - Added mailing list OSINT sources
    - Added EMAILS_LIMIT parameter in email collector (default off)

- Added custom labels for Pull requests (visible on github) #586
    - This is visible on on github pull requests screen

- Truncate on symbol Jinja filter #576
    - Truncates text on specific symbol

- Improve Tag Cloud words (handle accented characters, filter short words) #575
    - Added support for Tag Cloud words with accented characters (like über)
    - Filter short words (length < 3)
    - Fix issue #35 Tag cloud has troubles with umlauts and other characters

- Unify button order in news item screens #574
    - Unify buttons (delete) in same order as in main news item screen. Now it's same in Single news item detail, Aggregate Detail and News item detail screen.
    - Issue #39 Assess: Order of action buttons in CardAssess and NewsItemDetail differ

- Sorting of OSINT sources unintuitive #19 #573
    - OSINT sources are sorted a < z < A < Z. Ignorance of case is more intuitive in this case.

- Restructure custom Jinja filters #571
    - Restructure custom Jinja filters to seperate file and replace loading of individual filters with loading of all.
    - added regex string replace filter
    - sample Jinja2 templates for Mastodon post and spoiler

- Fixed #535 OSINT Source Groups selection #570
    - Fixed: #535 OSINT Source Groups selection: checkbox of last saved item is disabled
    - Fixed bad behavior when used: Select all and Item Selected

- Application settings #568
    - Added Application settings screen in Configuration. Here will be system settings that can customize Taranis functionality (no more .env variables)
    - Created first new settings: Date format, Time format that can be now implement in application
    - New setting: Open the Report Item selector in Read-Only mode
    - Fixed small hotkey crash

- Run regeneration for modules only in Upgrade mode and at Latest version #566
    - Avoid not necessary runs

- Small fix for #564 (regeneration for modules failed in some cases) #565
    - Fix regeneration for modules (Collectors, Bots..) There were cases when regeneration failed
    - Fix typo in file name

- Default bot creation #564
    - Added creation of default bot node.
    - Reflected in documentation.
    - Fix migrations
    - Removed unused env variable, fix mistakes

- Fixed and reworked broken hotkeys #554
    - Added new icons to hotkeys
    - Added missing shortcuts to hotkeys (they were defined in code but never on the screen)
    - Added missing description to hotkeys
    - Added reset button to hotkeys (in past there was no possibility to get back in case of some misconfiguration)
    - Fixed not working open source url shortcut in Assess
    - Fixed: don't overwrite shortcuts if user press Cancel in settings
    - Fixed duplicity keys errors for shortcuts with the same alias
    - Fixed error: this.card_items[this.pos] is undefined Fixed error: document.querySelectorAll(...)[this.pos] is undefined
    - Added support for uppercase letters in hotkeys (it was predefined but not possible to set)
    - Removed hotkey.key_code column (it was useless, more keys use the same code, we now store and compare real key name which is more unique. In past you can't define for example 'r' and 'R')
    - Small speedup in hotkeys initialization
    - This commit make working definition/setting of hotkeys. There can be still problem if and how they work. I also fix some errors/bugs on some shortcuts that i found when i test it.

- Fixed API keys authetification #553
    - Fixed checking of API keys in CORE. To this moment all modules were checking against Collector node key - wrong. Bots, Publisher, Presenter and Remote node access can have different keys!
    - Fixed checking of API keys in SSE. To this moment was all checking against Bots node key - wrong. Remote node access can have different key!
    - Unify API_KEY and ACCESS_KEY. Now we can use one functionality for all modules. No extra verification functions, code...
    - In remote_access and remote_node tables was replaced access_key column with api_key
    - Fixed Bots authentication (was broken by big CORE migration in past)
    - Fix publishers preset type error (publisher_type)
    - Improved debug and error logs in Bots and overall in code (API calls)
    - Fixed remote news item attribute creation (never worked)
    - Removed useless initializing another instance of TaranisLogger in Bots core API
    - Added sleep time 20 sec in Bots start (Bots failed to initialize and run, Core was not ready yet) Collectors decreased time from 30 to 20 seconds
    - Update some error codes (400 -> 503)
    - Better error handling in remote node connection

- Mastodon publisher #528
    - Added Mastodon publisher

- Fixed error in Presenter: default_value: Field may not be null. #547
    - This error is caused by #546 Added posibility "refresh" parameters for Presenter, Collector, Bot, and Publisher and their products

- Added posibility "refresh" parameters for Presenter, Collector, Bot, and Publisher and their products #546
    - Added cascade delete for Parameter, Presenter, Collector, Bot and Publisher tables
    - Added cascade delete for Parameter_Values tables: osint_source_parameter_value, bot_preset_parameter_value, publisher_preset_parameter_value
    - Added a "refresh" functionality for parameters in Presenter, Collector, Bot and Publisher. This can be called in Migration process. It was not possible to this time - you had to delete nodes (and all data) to reflect the new changes. Existing records then miss some new parameters that can cause errors in logs or missing functionality.
    - Added default_value to Parameter table. In this moment it's only used for automatic creating of new parameters that are added by migration process. In future we add these default values to GUI.

- Fixed lost data refresh in Analyze screen #532
    - Fixed: lost data refresh in Analyze screen after pre-clicking in e.g Publish screen and back
    - Fixed not working search in Assets. Crash with error message: TypeError: this.$root is undefined
    - Removed non using event: force-reindex

- Added baseSeverity attribute to "only CVSS number" compatibility mode #525
    - Added baseSeverity calculation to "only CVSS number" functionality
    - Don't show error in logs if CVSS is empty
    - Better error message also with source string

- Improved CVSS #522
    - support for CVSS 2.0, 3.0 and 4.0 - output is standardized CVSS JSON
    - basic support in templates
    - front-end only validates if the CVSS vector is not malformed, calculator is not implemented

- Remote node connection errors #524
    - Fixed crash (KeyError: 0) on some actions caused by last SqlAlchemy migration
    - Fixed crash on creating remote groups for report items
    - Fixed endless loop when you try connect to remote node with bad SSE link (both servers are after overloaded)
    - Added better logging to SSE (messages)
    - Fixed bug when you create News Item Data and Updated column don't reflect current time
    - Fixed find_by_hash function for News items that was not working
    - Fixed find_by_uuid function for Report items that was not working
    - Fixed add_remote_report_items function that was not working. It's still unfinished from the past but don't crash now and create all passed data on remote side. This needs to be finished someday!

- fix minor bug in string evaluation #521
    - proxy string evaluation:
    - add empty string to the condition

- Improve proxy for collectors #520
    - Improved and unified proxy handling for collectors and implemented in Web and RSS collectors. Others might follow. Removed code related to ftp proxy, never made sense and it is not even supported by browsers anymore.

- Change some datetime format in debug logs #514
    - Changed datetime format in debug logs inside not_modified functionality. (YYYY-MM-DD HH:MM). No need to display microseconds, seconds. Better readability.

- Improve RSS Collector #504
    - Fixed intervals and formatting of few OSINT sources
    - Improved RSS Collector
    - added docstrings

- Small fixes (warnings, table selection, linting, README) #513
    - Fix warnings on app start: Fall back to translate the keypath with 'en' locale.
    - Allow select text in data table (for copying) and add hand cursor
    - Removed python linting for 3.10
    - Updated Python version in README

- Improve OSINT all file generation #503
    - Improved OSINT all file generation with sorting
    - Few sources improved

- OSINT sources #499
    - Various OSINT sources ready to be imported to Taranis-NG.

- bump Python version to 3.13 #501
    - For linting and for build of src/shared. Also use latest Ubuntu.

- Added a remove button to products to remove report items #500
    - Added a remove button to products to remove report items.
    - Added tooltips for remove buttons.
    - Fixed error: AttributeError: 'OptionEngine' object has no attribute 'execute' (Flask migration).
    - Renamed showDeletePopup to showMsgBox due to its more generic meaning, not just for deleting.
    - Changed the text message for removing items (delete › remove) as it was misleading.

- fix send_file #498
    - Flask send_file changed keyword arguments, see pallets/flask#4667

- Fixed crash on remote node actions #490
    - Could not update remote node
    - Could not delete remote node

- Fix CRLF #489
    - Fix mixed line endings. All files should be LF now.
    - Added pre-commit hook which fixes this automatically.
    - Made print used by prestart_core.sh reliable

- Add Selenium version to logs #488
    - Add Selenium version to logs (useful to identify possible problems in old versions of selenium)
    - Sort Imports, From
    - In this time is fixed error "Failed to open new tab - no browser is open" in Chrome driver (Selenium bump)

- Improve CORE logging #487
    - Added solving clue message in error case when Collector ID file is missing
    - Enhanced error handling by elevating logging levels to error and including response details conditionally.
    - Introduced read_collector_config_id method in CoreApi for reading collector configuration ID. Refactored existing methods to use the new config ID reader.
    - Improved exception handling with logger.exception for detailed error logs.
    - Increase space between levelname and message in gunicorn logs
    - Change space between levelname and message in Taranis logs (' - ' > ' ')

- Fix migration and bump Python version #484
    - This just fixes the migration which removes Atom collector and also thanks to new tweepy version released,
    - bumps Python version for collectors and publishers. Also SQLAlchemy does not have to be ignored by dependabot anymore.

- Fix and Enhance Logging in CORE #476
    - Fixed a bug where only partial data was logged due to an issue with string concatenation
    - Removed duplicity timestamps from Gunicorn logs
    - Excluded debug KeepAlive records from Gunicorn logs (e.g., "Closing connection.", "/isalive")
    - Added query strings to Gunicorn logs (very useful for debugging)
    - Added colors to the Gunicorn logs (better readability)
    - Censored sensitive information (e.g., JWT, API keys) in Gunicorn logs
    - Added DocStrings

- Remove ATOM collector (duplicity functionality) #466
    - Atom collector functionality moved to RSS collector (has support for it)
    - Existing Atom sources will be automatically migrated
    - Removed unused code
    - This PR replace and enhance: WIP Remove Atom Collector #465

- SQLAlchemy migration 1.4.54 -> 2.0.36 #450
    - Migrate to latest SqlAlchemy

- "Clear" user data (Core migration fix) #447
    - "Clear" user data. In last big update we broke this. It's due get_jwt_claims() functionality was removed
    - from latest version of flask_jwt and by migration process was all user data mixed with jwt service data.

- Upgrade Core part1 #430
    - Upgrade: Python  (3.10 -> 3.13), Alpine (3.14-3.20)
    - Migrate libraries to latest working versions and fix broken functionality (Manage..)
    - Fixed Collector node creating (Error: missing 1 required positional argument: 'id')
    - Move Collector, Presenter, Publisher & Bot configurations to shared. This helps us for future work like
        - add new parameters with updates, refresh old parameters etc.. Currently this is not possible, only with recreating
        - new node and deleting old but at cost of data loose.
    - Create Default Collector node even if Collector docker is offline
    - Automatic Collector node creation is tuned up, better logs, timeout processing, hints whats going on..
    - Better loading CVE, CPE, CWE files (progress bar)
    - Code documentation

- Fix date time format for web collector #435
    - Now it can parse dates with text prefixes, detect DDMM MMDD formats if DD > 12, month names..

- Fixed: Invalid JWT: Not enough segments on Logout #434
    - The reconnectSSE function attempts to reconnect on error. Avoid attempting to reconnect to SSE with cleared credentials.

- Add license #431
    - Add license to modified code from FIRST.ORG

- Fixed logout issues #429
    - Fixed automatic logout problem after session timeout
    - Fixed error: TypeError: this.logout is not a function
    - Fixed error: TypeError: this.sseConnection is undefined

- Fix various problem with SSE #424
    - Fix Error 404. When you click on Report title, title_prefix you get error 404 Not found on background. This is because API support only Integer IDs. This change add support also for strings ID type. Now start working (lock, unlock) also for title, title_prefix fields, for "updated" needs more changes in code flow.
    - Fix old problem on not updating Attributes via SSE
    - Fix updating value_description field
    - Added debug messages in Core for SSE publish events

- Upgrade Vue to latest V2 + bump other modules #418
    - Upgrade Vue to latest V2 version (2.7.16) + all other modules
    - Removed not used NPM modules (faster, smaller build of node_modules)
    - This helps us to prepare for future Vue3 upgrade

- Update requirements.txt in core #423
    - Slightly newer version of gevent for core. It will not build anymore because of the old gevent version and produces issue

- Fix import csv (Word lists), Add possibility skip unwanted columns #417
    - Fix import csv files for single column values. There was problem with import of Word lists. When you select only single column import crash. Also there is no need import also description data in this case.
    - Added support to skip unwanted columns

- Fix 2 warnings, Speed up GUI build #416
    - Fix warning: The package-lock.json file was created with an old version of npm, old lockfile so supplemental metadata must be fetched from the registry. This is a one-time fix-up, please be patient.
    - package-lock.json was build with old version. Now runs GUI build much more faster! (no need conversion)
    - Fix warning: the attribute version is obsolete, it will be ignored, please remove it to avoid potential confusion (docker-compose-platforms.yml)

- Reflect NCSC-NL's Taranis3 current state in Readme #415

---

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

---

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

---

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

---

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

---

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

---

## [v21.11.1] - 2021-11-19

### Added
* Added collector management to manage.py

### Changed
* Docker readme: Fix URLs/Ports with switch to HTTPS by @sebix
* Tidied up word lists
* Re-worked proxy handling for the RSS collector
* Fixed issues with collector node and OSINT source status models and schemas

---

## [v21.10.6] - 2021-11-10

### Added
- added sample word block list for tag cloud

### Changed
- more verbose logging in the RSS collector
- usability fixes in collectors
- fixed asset group updates
- improved default templates for products

---

## [v21.10.5] - 2021-11-09

### Added
- authors of _Product templates_ may now use the new `Configuration -> Product types` help screen, which lists all the fields defined in a chosen _Report item type_. This simplifies the development of new product templates.

### Changed
- GUI and RSS collector fixes

---

## [v21.10.4] - 2021-11-08

### Added
- keycloak container (not enabled yet)

### Changed
- gui: fix news item group operations
- gui: bundle fonts
- gui: upgrade for security (breaks minor stuff, will be fixed in a later release)
- web collector: minor improvements

---

## [v21.10.3] - 2021-11-08

### Changed
- minor fixes and improvements across the entire project
- security patches for third party libraries
- docker:
   - deployment now includes Traefik as a reverse proxy for more convenient deployment (supports self generated, pre-uploaded, and letsencrypt certificates)
   - collectors container minimised
- complete rewrite of web collector: more robust, better support for various selectors, upgrade to selenium 4.0.0

---

## [v21.10.2] - 2021-09-25

### Added
- sample templates for products (PDF, HTML, TXT, MISP)

### Changed
- multiple usability fixes across the product

---

## [v21.10.1] - 2021-09-25

### Added
- Initial release of Taranis NG

### Changed
- Merged multiple Taranis NG repositories into one for easier understanding and management of the project


[v25.12.1]: https://github.com/SK-CERT/Taranis-NG/releases/tag/v25.12.1
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

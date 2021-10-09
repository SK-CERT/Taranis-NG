# TaranisNG

Taranis NG is an OSINT gathering and analysis tool for CSIRT teams and organisations. It allows osint gathering, analysis and reporting; team-to-team collaboration; and contains a user portal for simple self asset management.

Taranis crawls various **data sources** such as web sites or tweets to gather unstructured **news items**. These are processed by analysts to create structured **report items**, which are used to create **products** such as PDF files, which are finally **published**.

| Type      | Name                 | Description                           |
| :-------- | :------------------- | :------------------------------------ |
| Collector | web                  | crawl web sites                       |
|           | twitter              | receive tweets                        |
|           | email                | read e-mails                          |
|           | atom                 | read atom feeds                       |
|           | rss                  | read RSS feeds                        |
|           | slack                | read [Slack](https://slack.com/) messages |
|           | manual entry         | enter news item manually              |
|           | scheduled tasks      | populate feed automatically           |
| Presenter | pdf                  | create a PDF file                     |
|           | text                 | create plain text from template       |
|           | html                 | create HTML from template             |
|           | misp                 | create [MISP](https://misp-project.org/) event JSON |
| Publisher | email                | send e-mail                           |
|           | ftp                  | upload to FTP                         |
|           | misp                 | create MISP event                     |
|           | twitter              | create tweet                          |
|           | wordpress            | publish to [WordPress](https://wordpress.org/) |
| Bot       | analyst              | extract attributes from text by regular expressions |
|           | grouping             | group similar items in the news feed  |
|           | wordlist\_updater    | update word lists used for matching   |

Taranis NG was developed by [SK-CERT](https://www.sk-cert.sk/) with a help from wide CSIRT community, and is released under terms of the [European Union Public Licence](https://eupl.eu/1.2/en/).

Resources: [CHANGELOG](CHANGELOG.md), [LICENSE](LICENSE.md).

## Directory structure

- src/ - TaranisNG source code:
  - [Core](src/core/) is the REST API, the central component of Taranis NG
  - [GUI](src/gui/) is the web user interface
  - [Collectors](src/collectors/) retrieve OSINT information from various sources (such as web, twitter, email, atom, rss, slack, and more) and create **news items**.
  - [Presenters](src/presenters/) convert **report items** to **products** such as PDF.
  - [Publishers](src/publishers/) upload the **products** to external places such as e-mail, a WordPress web site, etc.
  - [Bots](src/bots/) are used for automated data processing. Think of them as robotic analysts.
  - [Common](src/common/) is a shared directory for core, publishers, collectors, presenters.
- [ansible/](ansible/) - Playbooks, roles, files and inventory to support easy deployment through Ansible
- [docker/](docker/) - Support files for Docker image creation and example docker-compose file

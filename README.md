# Taranis NG

Taranis NG is an OSINT gathering and analysis tool for CSIRT teams and
organisations. It allows osint gathering, analysis and reporting; team-to-team
collaboration; and contains a user portal for simple self asset management.

Taranis crawls various **data sources** such as web sites or tweets to gather
unstructured **news items**. These are processed by analysts to create
structured **report items**, which are used to create **products** such as PDF
files, which are finally **published**.

Taranis supports **team-to-team collaboration**, and includes a light weight
**self service asset management** which automatically links to the advisories
that mention vulnerabilities in the software.

| Type      | Name                 | Description                           |
| :-------- | :------------------- | :------------------------------------ |
| Collector | web                  | crawl web sites                       |
|           | twitter              | receive tweets                        |
|           | email                | read e-mails                          |
|           | rss                  | read RSS, Atom feeds                  |
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

This is just a taste of its features:

- crawl the raw data using various collectors, perhaps located in different environments.
- process even those javascript-generated web pages with advanced data extraction techniques
- create different analyses with completely customizable report item types
- generate many different products with help of product templates
- easily publish to different channels
- time is money: collaborate with other teams by sharing interesting data. Each partnership can be configured and customized.
- split the work responsibilities any way you like, or have multiple teams process partially overlapping data using advanced role and permission system
- use wordlists for filtering and highlighting
- publish the self-service asset management portal to your constituency and allow them to set various notification profiles for those times when a vulnerability hits their product.

<a id="requirements">Hardware requirements</a>: make sure to have at least 2 GB of RAM, 2 CPU cores and 5 GB of disk
storage available for running, 20 GB of disk storage if you want to build the
project from scratch.

Taranis NG was developed by [SK-CERT](https://www.sk-cert.sk/) with a help from
wide CSIRT community, and is released under terms of the [European Union Public
Licence](https://eupl.eu/1.2/en/).

Resources: [CHANGELOG](CHANGELOG.md), [LICENSE](LICENSE.md).

## Directory structure

- src/ - Taranis NG source code:
  - [Core](src/core/) is the REST API, the central component of Taranis NG
  - [GUI](src/gui/) is the web user interface
  - [Collectors](src/collectors/) retrieve OSINT information from various sources (such as web, twitter, email, atom, rss, slack, and more) and create **news items**.
  - [Presenters](src/presenters/) convert **report items** to **products** such as PDF.
  - [Publishers](src/publishers/) upload the **products** to external places such as e-mail, a WordPress web site, etc.
  - [Bots](src/bots/) are used for automated data processing. Think of them as robotic analysts.
- [ansible/](ansible/) - Playbooks, roles, files and inventory to support easy deployment through Ansible
- [docker/](docker/) - Support files for Docker image creation and example docker-compose file

## Architecture

<img src="https://raw.githubusercontent.com/SK-CERT/Taranis-NG/main/doc/static/img/taranis-ng-block-diagram.png?sanitize=true&raw=true" />

## Getting started with Docker installation

Currently, the best way to deploy is via Docker. For more information, see [docker/README.md](docker/README.md).

When your Taranis NG instance is up and running, visit your instance by
navigating to [https://localhost:4443](https://localhost:4443/) using your web
browser. **The default credentials are `user` / `user` and `admin` / `admin`.**

### Connecting to collectors, presenters, and publishers

After installation, you have to connect the core application with collectors,
presenters, and publishers. There is no limit to how many of these you have.
The default docker installation deploys one instance of each for you automatically.

Adding a collector node: TL;DR: no action needed. Longer version: This is done automatically on startup if no collectors are defined, unless you define `SKIP_DEFAULT_COLLECTOR=true` environment variable. To verify: Log in as an `admin`, then navigate to Configuration -> Collectors nodes. You should see `Default Docker Collector` in the list.

Adding a presenter node: Log in as an `admin`, then navigate to Configuration
-> Presenters nodes. Click `Add new`. Enter any name and description. For URL,
enter `http://presenters/` and for key, enter `supersecret` (or whatever
password you chose during the installation). Click `Save`.

Adding a publisher node: repeat the process at Configuration -> Publishers
nodes. Fill in the fields. For URL, enter `http://publishers/`. Don't forget to
set the password.

### Altering the roles (optional)

If you don't wish to use separate accounts for user and admin, or have other
ideas about how the responsibilities should be split, visit Configuration ->
Roles. Edit the roles to your liking, for example by adding the executive
permissions to the Admin role. If you change the roles to yourself, don't
forget to log out and log back in.

### Adding sources to collect

Visit Configuration -> OSINT Sources. Click `Add new`. Select the collectors
node that you just created and then you should be able to see all the
collectors it has registered. Pick one (for instance the RSS collector), and
you will be able to enter all the necessary details. Finally, click `Save`.

In a few minutes, you should see freshly collected data in the Assess menu,
which is normally available to the account user / user.

### Splitting the sources into groups, and revisiting the permissions (optional)

Visit Configuration -> OSINT Source Groups to customize the groups, in which
the results are being presented. Click `Add new`, then put the various
sources you've created into different groups.

If you want to restrict the access, go to Configuration -> ACLs, and create
a new ACL by clicking `Add new`. You can pick any particular item type
(Collector, Delegation, OSINT Source, OSINT Source Group, Product Type, Report
Item, Report Item Type, Word List) and then grant *see*, *access*, or *modify*
access types to everyone, selected users, or selected roles.

### Uploading the CPE, CWE and CVE dictionaries

In order to simplify the process of writing advisories, you can have CPE, CWE
dictionaries and a current list of CVEs preloaded in Taranis NG.

1. Download the official CPE dictionary from
[nvd.nist.gov/products/cpe](https://nvd.nist.gov/products/cpe) in gz format.

2. Upload the dictionary to the proper path, and import into the database
```bash
zcat official-cpe-dictionary_v2.3.xml.gz | \
    docker exec -i taranis-ng-core-1 python manage.py dictionary --upload-cpe
```

3. Download the official CVE list from
[cve.mitre.org/data/downloads/](https://cve.mitre.org/data/downloads/index.html)
in xml.gz format.

4. Upload the dictionary to the proper path, and import into the database
```bash
zcat allitems.xml.gz | \
    docker exec -i taranis-ng-core-1 python manage.py dictionary --upload-cve
```

5. Download the official CWE list from
[cwe.mitre.org/data/downloads.html](https://cwe.mitre.org/data/downloads.html)
in xml.zip format.

6. Upload the dictionary to the proper path, and import into the database
```bash
zcat cwec_latest.xml.zip | \
    docker exec -i taranis-ng-core-1 python manage.py dictionary --upload-cwe
```

Some Linux distributions might provide gzcat instead of zcat.

### Using the default stop lists for better tag cloud

1. Visit Configuration -> Word Lists.
2. Open the default word lists (starting with `Default ...`).
3. Choose a word list URL or use the default URL present in the standard installation.
4. Under Words, click `Download from URL`.
5. Check whether the CSV file has a header or not, then click `Download from URL`. Choose which column has the value and description.
6. Optionally, you can check `Delete existing words` option to remove any previous words in the list.
7. Finally, if you are satisfied with the configuration, click `Import`.
8. The word list will be imported and you can now save it, to be applied.

## About...

This project was inspired by [Taranis3](https://github.com/NCSC-NL/taranis3),
a great tool made by NCSC-NL. Currently, NCSC-NL has a new tool for producing advisories,
with a different approach to communicating with the world. There was no funding to maintain or
further develop NCSC-NL's Taranis3.

It aims to become a next generation of this category of tools. The project was made in collaboration
with a wide group of European CSIRT teams who are developers and users of Taranis3, and would not be
possible without their valuable input especially during the requirements collection phase.
The architecture and design of new Taranis NG is a collective brain child of this community.

This project has been co-funded by European Regional Development Fund as part of [Operational Programme Integrated Infrastructure (OPII)](https://www.opii.gov.sk/opii-en/titulka-en).

Further development has been co-funded by “Connecting Europe Facility – Cybersecurity Digital Service Infrastructure Maintenance and Evolution of Core Service Platform Cooperation Mechanism for CSIRTs – MeliCERTes Facility” (SMART 2018/1024).

Further development is being co-funded by European Commission through the Connecting Europe Facility action entitled "Joint Threat Analysis Network", action number 2020-EU-IA-0260.

## Learn more...

Before the new developer and user documentation becomes available, we invite you
to have a look at the
[Taranis NG - original requirements.pdf](https://github.com/SK-CERT/Taranis-NG/blob/main/doc/static/Taranis%20NG%20-%20original%20requirements.pdf)
for detailed description of the features of the first release, its internal
architecture, and general design goals of the project.

Please note that the version available today may already contain new features
and changes, which are not documented in the requirements PDF.

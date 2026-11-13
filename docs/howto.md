# Advanced configuration how-to

**Audience:** administrators of an already initialized Taranis NG instance.

**Status:** optional customization reference, not part of installation. The
canonical Docker guide includes the complete path through the first collected
item and product preview.

### Table of contents

- [Altering the roles](#_toc1)
- [Splitting the sources into groups, and revisiting the permissions](#_toc3)
- [Customizing stop lists](#_toc4)
- [Management script - configure accounts, roles, nodes and dictionaries via commandline](#_toc5)
- [Using AI in Taranis NG](#_toc6)
- [Citing sources in reports and products](#_toc7)
- [Reports and products in several languages](#_toc8)
- [Products: what is published, in which languages, formats and channels](#_toc9)

# <a id="_toc1"></a>Altering the roles

If you don't wish to use separate accounts for user and admin, or have other
ideas about how the responsibilities should be split, visit Configuration ->
Roles. Edit the roles to your liking, for example by adding the executive
permissions to the Admin role. If you change the roles to yourself, don't
forget to log out and log back in.

# <a id="_toc3"></a>Splitting the sources into groups, and revisiting the permissions

Visit Configuration -> OSINT Source Groups to customize the groups, in which
the results are being presented. Click `Add new`, then put the various
sources you've created into different groups.

If you want to restrict the access, go to Configuration -> ACLs, and create
a new ACL by clicking `Add new`. You can pick any particular item type
(Collector, OSINT Source, OSINT Source Group, Product, Report Item Type, Word List) and then grant *see*, *access*, or *modify*
access types to everyone, selected users, or selected roles. An ACL on a product (a product
preset, see [Products](#_toc9)) covers the products published with it.

# <a id="_toc4"></a>Customizing stop lists

A fresh database may not contain an active default stop-word list. Confirm that
the expected list exists, has the correct language and URL, and contains words
before relying on the tag cloud.

The source distribution provides GUI-importable language files under
`resources/wordlists/*_complete.csv`. Each UTF-8, semicolon-delimited file has
the `value;description` header expected by **Import from CSV** and represents
one language category. See `resources/wordlists/README.md` for the complete
category-to-file mapping.

These are operator-side files in the source checkout. Do not copy them into the
Core container's `/app` directory. When running Compose commands from
`docker/`, find them under `../resources/wordlists/`.

1. Visit Configuration -> Word Lists.
2. Open the intended word list, or create `Multilingual tag-cloud stop words`.
3. Enable `Use for stop words` so the saved entries filter the tag cloud.
4. Add a category for each required language, using the category names in the
   word-list resource guide.
5. Under the category's Words table, click `Import from CSV` and select the
   matching `*_complete.csv` file.
6. Leave `File has header` enabled for the supplied files. The named `value`
   and `description` columns are detected automatically; then click `Import`.
7. Optionally select `Delete existing words` when replacing that category.
8. Repeat for the other language categories and save the word list.

# <a id="_toc5"></a>Management script - configure accounts, roles, nodes and dictionaries via commandline

Taranis NG core container comes with a simple management script that may be used to set up and configure the instance without manual interaction with the database.

Run the management script through the Core Compose service from the `docker/`
directory:

```bash
docker compose exec core python manage.py [COMMAND] [PARAMETERS]
```

The account command accepts passwords on the command line, where a shell or
process monitor may record them. Prefer the account administration UI for
password changes. Docker secret files do not rotate application-account
passwords stored in PostgreSQL.

Currently, you may manage the following:

| Command     | Description | Parameters |
|-------------|-------------|------------|
| `account`     | (WIP) List, create, edit and delete user accounts. | `--list`, `-l` : list all user accounts<br /> `--create`, `-c` : create a new user account<br /> `--edit`, `-e` : edit an existing user account<br /> `--delete`, `-d` : delete a user account<br /> `--username` : specify the username<br /> `--name` : specify the user's name<br /> `--password` : specify the user's password<br /> `--roles` : specify a list of roles, divided by a comma (`,`), that the user belongs to |
| `role`     | (WIP) List, create, edit and delete user roles. | `--list`, `-l` : list all roles<br /> `--filter`, `-f` : filter roles by their name or description<br /> `--create`, `-c` : create a new role<br /> `--edit`, `-e` : edit an existing role<br /> `--delete`, `-d` : delete a role<br /> `--id` : specify the role id (in combination with `--edit` or `--delete`)<br /> `--name` : specify the role name<br /> `--description` : specify the role description (default is `""`)<br /> `--permissions` : specify a list of permissions, divided with a comma (`,`), that the role would allow |
| `collector, bot`     | (WIP) List, create, edit, delete and update nodes. | `--list`, `-l` : list all nodes<br /> `--create`, `-c` : create a new node<br /> `--edit`, `-e` : edit an existing node<br /> `--delete`, `-d` : delete a node<br /> `--update`, `-u` : re-initialize node<br /> `--all`, `-a` : update all nodes (in combination with `--update`)<br /> `--show-api-key` : show API key in plaintext (in combination with `--list`)<br /> `--id` : specify the node id (in combination with `--edit`, `--delete` or `--update`)<br /> `--name` : specify the node name<br /> `--description` : specify the collector description (default is `""`)<br /> `--api-url` : specify the collector node API url<br /> `--api-key` : specify the collector node API key |
| `dictionary`     | Update CPE, CWE and CVE dictionaries. | `--upload-cpe` : upload the CPE dictionary (expected on STDIN in XML format) to the path indicated by `CPE_UPDATE_FILE` environment variable, and update the database from that file.<br /> `--upload-cve` : upload the CVE dictionary (expected on STDIN in XML format) to the path indicated by `CVE_UPDATE_FILE` environment variable, and update the database from that file.<br /> `--upload-cwe` : upload the CWE dictionary (expected on STDIN in XML format) to the path indicated by `CWE_UPDATE_FILE` environment variable, and update the database from that file. |
| `apikey`     | List, create, enable, disable and delete API keys. Only a hash of each key is stored: the key is printed once, when it is created. API keys can also be managed in the GUI (**Configuration → Access Management → API keys**, and **User settings → API keys** for one's own). | `--list`, `-l` : list all API keys (never the keys themselves)<br /> `--create`, `-c` : create a new API key and print it<br /> `--enable` / `--disable` : enable or disable an API key<br /> `--delete`, `-d` : delete an API key<br /> `--id` : specify the API key id (in combination with `--enable`, `--disable` or `--delete`)<br /> `--name`, `-n` : specify the API key name, unique per user<br /> `--user`, `-u` : specify the username of the key's owner<br /> `--description` : what the key is for<br /> `--expires`, `-e` : specify the expiration datetime (`YYYY-MM-DD HH:MM`, server time zone)<br /> `--permissions` : limit the key to these permissions, divided by a comma (`,`)<br /> `--allowed-ips` : public IP addresses or CIDR ranges the key may be used from, divided by a comma (`,`) |


Here are some examples:

### Create a new role with a set of permissions

```bash
manage.py role \
    --create \
    --name "Custom role 1" \
    --description "Custom role with analysis and assessment access" \
    --permissions "ANALYZE_ACCESS, ANALYZE_CREATE, ANALYZE_UPDATE, \
    ANALYZE_DELETE, ASSESS_ACCESS, ASSESS_CREATE, ASSESS_UPDATE, \
    ASSESS_DELETE, MY_ASSETS_ACCESS, MY_ASSETS_CREATE"
```

Command output:

```
Role 'Custom role 1' with id 3 created.
```

### Role filter

```bash
manage.py role \
    --list \
    --filter "Custom role 1"
```

Command output:

```
Id: 3
	Name: Custom role 1
	Description: Custom role with analysis and assessment access
	Permissions: ['ANALYZE_ACCESS', 'ANALYZE_CREATE', 'ANALYZE_UPDATE', 'ANALYZE_DELETE', 'ASSESS_ACCESS', 'ASSESS_CREATE', 'ASSESS_UPDATE', 'ASSESS_DELETE', 'MY_ASSETS_ACCESS', 'MY_ASSETS_CREATE']
```

### Create a new [collector, bot] node

```bash
manage.py [collector, bot] \
    --create \
    --name "Docker [collector, bot]" \
    --description "A simple [collector, bot] hosted in a Docker container" \
    --api-url "http://[collectors, bots]" \
    --api-key "REPLACE_WITH_CURRENT_SATELLITE_KEY"
```

Command output:

```
[Collector, Bot] node 'Docker [collector, bot]' with id 1 created.
```

### Re-initialize a [collector, bot] node

```bash
manage.py [collector, bot] \
    --update \
    --name "Docker"
```

Command output:

```
[Collector, Bot] node 1 updated.
[Collector, Bot] node 2 updated.
Unable to update [collector, bot] node 3.
    Response: [401] ""
```

### Create a new user account

```bash
manage.py account \
    --create \
    --name "John Doe" \
    --username "test_user" \
    --password "REPLACE_WITH_STRONG_UNIQUE_PASSWORD" \
    --roles 3
```

Command output:

```
User 'test_user' created.
```


### Upload a CPE dictionary

In order to simplify the process of writing advisories, you can have a list of CPE, CVEs and CWE
preloaded in Taranis NG.

1. Download the official CPE dictionary from
[nvd.nist.gov/products/cpe](https://nvd.nist.gov/products/cpe) in gz format.

2. Upload the dictionary to the proper path, and import into the database
```bash
zcat official-cpe-dictionary_v2.3.xml.gz | \
    docker exec -i taranis-ng-core-1 python manage.py dictionary --upload-cpe
```

Command output:

```
Processed CPE items: 1000
Processed CPE items: 2000
...
Processed CPE items: 789704
Dictionary was uploaded.
```

### Upload a CVE dictionary

1. Download the official CVE list from
[cve.mitre.org/data/downloads/](https://cve.mitre.org/data/downloads/index.html)
in xml.gz format.

2. Upload the dictionary to the proper path, and import into the database
```bash
zcat allitems.xml.gz | \
    docker exec -i taranis-ng-core-1 python manage.py dictionary --upload-cve
```

### Upload a CWE dictionary

1. Download the official CWE list from
[cwe.mitre.org/data/downloads.html](https://cwe.mitre.org/data/downloads.html)
in xml.zip format.

2. Upload the dictionary to the proper path, and import into the database
```bash
zcat cwec_latest.xml.zip | \
    docker exec -i taranis-ng-core-1 python manage.py dictionary --upload-cwe
```

Some Linux distributions might provide gzcat instead of zcat.

### Create a new API key

```bash
manage.py apikey \
    --create \
    --name "My ApiKey" \
    --user "test_user"
```

Command output:

```
ApiKey 'My ApiKey' with id 3 created for user 'test_user'.
API key (shown only once): tnk_ZmV5B0Zq1c3Yk2hJ9c0wPq8u6TtR1vXx4Ae7sL2mN0o
```

Only a hash of the key is stored, so copy it now; it cannot be shown again. A script sends it
in the `Authorization` header and acts with the permissions of the key's owner:

```bash
curl -H "Authorization: ApiKey tnk_ZmV5B0Zq1c3Yk2hJ9c0wPq8u6TtR1vXx4Ae7sL2mN0o" \
    https://taranis.example.com/api/v1/assess/osint-source-groups
```

### Create a limited API key that expires

```bash
manage.py apikey \
    --create \
    --name "SOAR sync" \
    --user "soar" \
    --expires "2027-12-31 16:55" \
    --permissions "ASSESS_ACCESS,ANALYZE_ACCESS" \
    --allowed-ips "185.10.20.0/24,2a01:4f8::/32"
```

A limited key can do only what it is limited to and its owner can still do. An expiry, a
maximum lifetime and an IP allowlist can be required for every new key, and a site-wide IP
allowlist can be set for all of them, under **Configuration → Access Management → Security**.
When a key expires, its owner is notified (on the channels set up under **Notifications**),
once; the check runs every five minutes.

Only public addresses can be listed. Private (`10.0.0.0/8`, `172.16.0.0/12`,
`192.168.0.0/16`, `fc00::/7`), shared (`100.64.0.0/10`), loopback, link-local, multicast,
broadcast, documentation, benchmarking and other reserved ranges are refused, and so is any
range that reaches into one of them (such as `0.0.0.0/0`). IPv6 must be global unicast
(`2000::/3`).

IP allowlists are checked against the client address that the trusted reverse proxies
(`TRUSTED_PROXY_HOPS`, 1 for the bundled Traefik) report in `X-Forwarded-For`. Set it to the
real number of proxies in front of core, and do not let clients reach core except through
them: whoever talks to core directly can write that header and claim any address. A client
connecting over IPv6 through Docker's userland proxy shows up as the Docker bridge address
(e.g. `172.18.0.1`) unless IPv6 is enabled for the network (`enable_ipv6`). The API key
dialogs show the address core sees for you, so you can check it before relying on a list;
an address that is not public cannot be used for one.

### Disable or delete an API key

```bash
manage.py apikey --disable --name "SOAR sync" --user "soar"
manage.py apikey --delete --id 3
```

# <a id="_toc6"></a>Using AI in Taranis NG

This section outlines the integration of AI-enhanced functionality for generating report summaries.

Taranis NG can connect to an online large model from OpenAI, or your own local LLM API such as Ollama.
If you don’t have any, you can start a small AI model locally.

### Installation

This example demonstrates how to use **Ollama** with **Taranis NG**. Ollama is an open-source tool that enables running large language models (LLMs) locally. The scenario described targets Windows with Taranis NG running inside Docker Desktop. The procedure is similar for other operating systems.

1. Install Ollama by following the instructions at [ollama.com](https://ollama.com).
2. After installation, you can begin using LLMs by executing commands in the terminal.
3. Choose and download a model that fits your use case. (e.g. `llama3.2:3b`) using the command:
    ```bash
    ollama pull <MODELNAME>
    ```
4. To verify the setup, run:
    ```bash
    ollama run <MODELNAME>
    ```
    and review the output.

### Configuration

1. In Taranis NG, navigate to **Configuration → Local AI models**, then click **Add New**:

   * **Name**: `Ollama - <MODELNAME>`
   * **API Type**: `openai`
   * **API URL**:
     * Use `http://localhost:11434/v1` if Ollama runs directly on the host.
     * If Taranis NG is in Docker Desktop, use `http://host.docker.internal:11434/v1` instead of `localhost`.
   * **API Key**: Not required.
   * **Model**: `<MODELNAME>`

   Click **Save**. You may also configure ChatGPT or other models, provided they support the `openai` API type.

2. Navigate to **Configuration → Report Types**, then open the **Vulnerability Report** type.
   Locate the `Description` attribute and click **Edit**.
   From the `AI model` dropdown, select `Ollama - <MODELNAME>`. In the `AI Prompt` field, enter the following:

   ```
   List only software vulnerabilities based on established templates (see example 1, example 2, example 3). Do not add an introduction or conclusion, do not use bullets or numbering, or any markdown. Do not add recommendations or other unrelated text, only vulnerabilities.

   <example 1>
   Hikvision has released security updates for its portfolio of access points that fix a security vulnerability. The security vulnerability, identified as CVE-2025-39240, is based on insufficient user input validation and allows a remote, authenticated attacker with administrator privileges to execute malicious code, gain unauthorized access to sensitive data, make unauthorized changes to the system, and cause a denial of service by sending specially crafted packets.
   </example>

   <example 2>
   Security researchers have disclosed four security vulnerabilities in NDI PTZ (Network device interface pan-tilt-zoom) cameras from ValueHD, PTZOptics, multiCAM Systems, and SMTAV, three of which are rated critical. The most serious critical security vulnerability, CVE-2025-35451, is found in PTZOptics products (and likely other products based on ValueHD products) and involves the existence of a built-in ROOT user account with a default password, which could allow a remote, unauthenticated attacker to gain unauthorized access to the system, resulting in a complete breach of confidentiality, integrity, and availability of the system. Affected devices do not allow users to change the default password or disable SSH and telnet services. Other security vulnerabilities can be exploited to gain unauthorized access to sensitive data, make unauthorized changes to the system, cause denial of service, gain complete control over the system, and execute malicious code.
   </example>

   <example 3>
   Security researchers have disclosed information about two security vulnerabilities in GPS receivers from SinoTrack. The most serious security vulnerability, identified as CVE-2025-5485, involves inadequate implementation of security mechanisms and allows a remote, unauthenticated attacker to gain unauthorized access to the system by simply predicting the values needed to access the web interface, resulting in a complete breach of the confidentiality, integrity, and availability of the system. The second security vulnerability can be exploited to gain unauthorized access to sensitive data, make unauthorized changes to the system, cause denial of service, and gain complete control over the system. Exploitation of the vulnerability with the identifier CVE-2025-5484 requires user interaction.
   </example>
   ```

### Usage

1. In the **Analyze** module, create a new **Vulnerability Report**.
   Add one or more news items. Next to the `Description` attribute, a new **Auto Generate** button should appear.
   Click the button and wait for processing; the icon will change during execution. The AI will process the input using the defined prompt and return the generated text. You can edit the result before saving.

2. This process can be repeated for any report type, using custom AI prompts defined per attribute.

3. The quality of the result depends on both the prompt and the selected model. Experiment with different models and prompts to achieve optimal results for your specific use case.

# <a id="_toc7"></a>Citing sources in reports and products

Report text cites its sources by the **Link** attribute type: each link has a stable key, and a
citation is stored as a token such as `[#k3f9a2]`. Inserting, moving or deleting links never
changes what a citation points at.

- In the report dialog, the **Links** attribute lists the links numbered as they are cited. A
  **+** between two rows inserts a link there, and **Add from news items** adds the source URLs
  of the attached news items. Deleting a link that is cited asks first.
- Every text attribute (Text, Text Area, Rich Text) has a cite button that inserts a citation at
  the cursor. It lists the links by their tokens, and with more than 8 links it offers a search by
  URL or token. Under the field, each citation shows its token and the link it resolves to, and a
  citation of a deleted link is flagged. A default **Rich Text** attribute is available to add to
  report types.
- A product has links of its own, which its description cites the same way. Its cite button also
  offers the links of the product's reports; citing one copies it into the product's links.

When core hands a product to a presenter or to a public-web node, it renders every citation to a
plain number, `[1]`, `[2]`..., which indexes one list of sources. A link is numbered when the
text first cites it, reading the product description and then each report in the product's order
(its attributes in form order), so the text reads `[1]`, `[2]`, `[3]`...; the links no text cites
follow, the product's own links first, then those of each report. Equal URLs share one number,
and a translation is numbered by its own text. Templates get that
list as `data.product.links` (URL strings, `[1]` being the first); the texts in
`report_item.attrs` already contain the numbers. A citation of a link that no longer exists is
left out.

For a custom report type to support citations, give it an attribute of type **Link**. The
`a3c9f1d27b64` migration switched the existing attributes titled "Links" to that type and turned
the positional `[n]` citations of existing reports and product descriptions into tokens. Core
and public-web nodes must run the same version: a public-web node only shows the numbers core
rendered.

# <a id="_toc8"></a>Reports and products in several languages

An analyst writes a report in one language. Taranis keeps its translations next to it, made by
hand or by an AI model, and renders products and the public web in the language asked for. The
original always stays as written; a translation never replaces it.

Everything rendered in a language falls back the same way: the language asked for, then
English, then the original, whatever language that is in. A language that *is* the original's
language gets the original, never a translation.

### Report types

In **Configuration → Reports → Report Types**, edit a report type:

- **Language variants**: every language reports of this type should exist in, including the
  one they are usually written in.
- **AI provider for translation**: optional; without one, translations are written by hand.
- **Language of the labels**: the language the type's own texts (its name, description, group
  and field names) are written in. Set it: without it, the original labels are only the last
  fallback, so an English label translation would win over Czech labels on a Czech product.
- **Translate** on a field: whether reports translate its values. Only String, Text and Rich
  text fields can be translated; CVEs, dates, links, TLP and the other types read the same in
  every language.
- **Labels: {language}** tabs translate the type's own texts. The original is shown under each
  field, and the copy button next to it copies the original in for names that read the same.
  **Translate missing labels with AI** fills the empty ones.

### Constants of choice attributes

Enum, Radio and Multiple choice values are translated once, in configuration. In
**Configuration → Reports → Attributes**, edit the attribute: its **Translations** section has a
tab for each language of the report types using it (except their labels' language). Edit a
constant's translation there, or use **Translate missing with AI**. Reports keep storing the
original constant, so templates and filters that compare it keep working.

### Writing and translating a report

- A new report is written in your **Default language for reports/products** (user settings).
  The **Language of the report** select in the dialog's toolbar shows it and can change it
  before you save.
- Once it is saved, the report has a tab for each other language of its type. In a tab, type a
  translation, or use the AI buttons: per field, **Translate into {language}** for the tab, or
  **Translate whole report** in the toolbar, which runs in the background and shows its
  progress. A tab or the whole report gets only its empty and outdated fields filled; a
  translation a person wrote is replaced only from that field's own button, after confirming.
- A translation made by AI is marked **AI** until someone edits or reviews it. When it is right as
  it is, the check mark next to **AI** marks it reviewed without changing it; **Mark AI
  translations as reviewed** does so for the whole tab. A translation is marked **Outdated** when
  its original changed after it was made; reviewing an outdated AI translation confirms it for
  the current original. Fields another user is editing are not marked.
- Fields are locked per language while someone edits them, and the AI job skips a field that
  another user is editing.
- The Analyze and Products lists show names in the GUI's language, with the same fallback.
- Reports and products created before this feature have no language. They render exactly as
  before. Set the language in the toolbar to enable their translation tabs; Taranis does not
  guess it.

### Limiting what is sent to an AI provider

In **Configuration → Data providers → AI models**, **Highest TLP sent** limits which reports an
AI model may see: report translation, product title translation and **Auto Generate** refuse a
report above that TLP, or one whose TLP field is empty while a limit is set, and say why. New
models default to CLEAR; models that existed before have no limit until you set one. Reports
whose type has no TLP field are not checked, and neither are configuration texts (labels and
constants).

### Products

- A product's language is chosen with **Language of the product** in the dialog's toolbar, next
  to the state; a new product starts in your default language.
- The product has a tab for its own language and for each language of its reports' types, with
  its title and description per tab, as in a report: **Translate whole product** in the toolbar
  fills, with AI, the texts that have no translation or an outdated one the AI made, language
  after language with a progress bar; in a language tab, **Translate into {language}** does the
  same for that language, and **Mark AI translations as reviewed** keeps its AI texts as they are.
  A translation a person wrote is replaced only from that text's own button, after confirming; the
  check mark next to **AI** marks one text reviewed.
- **Show product preview** and **Download** render the open tab's language. **Publish** sends each
  delivery of the product preset in its own language (see [Products](#_toc9)).
- Notices under the tabs say what a language falls back on: reports without a translation into
  it, outdated translations (preview, download and publish ask to confirm them first), and each
  format of the product's preset that has no templates for it.

### Templates per language

In **Configuration → Presenters → Product Formats**, the **Default** tab holds all parameters and
**Language of the templates**, the language the default templates are written in. **Add
language** adds a tab with only the template paths for that language; a path left empty uses
the default one. A product is rendered with the templates of its language, then English, then
the default ones. A presenter without templates, such as JSON, has none of these settings.
Existing per-language product formats (for example `e-mail CZ` and `e-mail SK`) keep working; set
their template language, and a product rendered in another language warns about it.

For template authors, rendering in a language changes only additive fields, so existing
templates keep producing the same output:

- In the language rendered: `report_item.name`, `report_item.name_prefix`, the values of
  translated fields in `report_item.attrs`, and `data.product.title`.
- Unchanged: `report_item.type`, the `report_item.attrs` keys and the choice constants in it
  (conditions such as `attrs.impact == 'High'` keep working).
- New: `report_item.attrs_display` (the same keys with constants translated),
  `report_item.labels` (each key's field name in the language), `report_item.type_label`,
  `report_item.type_description_label` and `data.product.language`.

The JSON presenter's output has the same keys in every language, plus these fields.

### Public web

A public web's pages are in the page's language: `?lang=`, else the browser's language, else the
web's default (see **Languages** in **Configuration → Public Web**). Visitors switch to another of
the web's languages in the language menu at the top of the homepage and of each report (a web with
one language has none); the menu sets `?lang=`, which the page's links keep.

The page's language changes a report only where the report is translated into it: what is not
stays as written, with no English in between (unlike products and presenters), and outdated
translations are skipped. When a report is shown in another language than the page's, the page
says which. The report's own phrases (*More information*, *The vulnerability was publicly
disclosed*, its labels) are in the language the report is shown in, so a report nobody translated
reads entirely in the language it was written in, and only the page around it follows the visitor.
A bulletin whose reports are in different languages shows each one in its own.

### Upgrading

Remote presenter nodes must be upgraded before core: core sends presenters fields that older
nodes reject. Core and public-web nodes can be upgraded in either order.

# <a id="_toc9"></a>Products: what is published, in which languages, formats and channels

A **product** is the content: its title and description and the reports it collects. It keeps
its reports in the order its form lists them, which the drag handle or the arrows beside each
report change; presenters, the public web (its `?items=` numbers) and the citation numbers follow
that order. Three things decide how it is published:

- a **product format** is a presenter and its template: an e-mail, a JSON file, a PDF, a
  Mastodon post (Configuration -> Presenters -> Product Formats);
- a **publishing channel** is where a rendered product goes: an e-mail address, an SFTP server,
  a Mastodon account (Configuration -> Publishers -> Publishing Channels);
- a **product preset**, shown as a product in Configuration -> Products, says which languages
  of the product go in which formats to which channels, for example *Cyberfeed*.

A product picks a product preset, and **Publish** runs it. Each row of a preset is a language
and a format, and the channels they are sent to. *Cyberfeed* could have these rows:

- Czech, *Mastodon post* -> *Mastodon CZ* and *Mastodon SK*, and the mailing list;
- English, *Mastodon post* -> the mailing list;
- Slovak, *PDF* -> SFTP;
- Slovak, *HTML* -> SFTP.

A row without a language publishes the product in the language it is written in. A channel gets
each language and format on its own: the mailing list above gets two e-mails, one in Czech and
one in English, and the SFTP server two files. A row without a channel is only previewed. Each
language of each format is rendered once per publish, then sent to every channel it goes to. A
channel that fails does not stop the others; the notification names the deliveries that failed.

In the product dialog, every delivery of the chosen preset comes ticked, labelled with its
language: untick one to leave it out of this publish; the preset stays as it is. The publish
confirmation lists, for each language it sends, what that language falls back on (see
[Reports and products in several languages](#_toc8)). **Show product preview** and **Download**
render the open tab's language, with a menu of the formats when the preset has more than one.

A product preset can also show its published products on the **public web**: on every web, or only
on the webs it lists. The page of a published product is rendered with the report template of its
preset (Configuration -> Public Web -> Report templates); a preset without one shows only the
products that are vulnerability reports, with the built-in templates. A template can be limited
to chosen webs, so that each web has its own look: a web uses the template that lists it, else
the one for every web. The same tab lists the
built-in templates: they cannot be deleted, but those used for products and report items without
a template of their own can be switched off, so that only your own templates are used. Switching
off the vulnerability report template hides the products of every preset without a template; a
report item left with no template is not shown, and neither is a product left
with no item.
Who may see, edit and publish products is set by ACLs on their preset (item type *Product*).

A format or a channel that a preset uses, a web that one is restricted to, and a preset that
products use cannot be deleted until nothing uses them any more.

### Upgrading

The `72f1a157e289` migration renames product types to product formats and publisher presets to
publishing channels, and creates one preset per existing product format, named after it, with
that format and no channel, shown on every public web. Products keep their content, and the webs
they were limited to, and point at the preset of their old format. Which channels products used
to be sent to was never recorded, so assign the channels once in Configuration -> Products; until
then, **Publish** has nothing to send. Every delivery is in the product's own language until you
pick another. ACL entries on product types became entries on the matching presets, and every role
or user allowed to configure product types may configure presets. Roles and users keep their
rights under the new permission names (`CONFIG_PRODUCT_FORMAT_*`, `CONFIG_PUBLISHING_CHANNEL_*`,
`CONFIG_PRODUCT_PRESET_*`), ACL entries keep guarding the same presets (item type
`PRODUCT_PRESET`), and the API is at `/api/v1/config/product-formats`,
`/api/v1/config/publishing-channels` and `/api/v1/config/product-presets`. Presenter templates
get the format a product is rendered in as `data.product.product_format` and
`data.product.product_format_description`; custom templates that read `product_type` or
`product_type_description` have to be changed.

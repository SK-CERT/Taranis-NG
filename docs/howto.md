### Table of Contents

- [Altering the roles](#_toc1)
- [Adding sources to collect](#_toc2)
- [Splitting the sources into groups, and revisiting the permissions](#_toc3)
- [Using the default stop lists for better tag cloud](#_toc4)
- [Management script - configure accounts, roles, nodes and dictionaries via commandline](#_toc5)
- [Using AI in Taranis NG](#_toc6)

# <a id="_toc1"></a>Altering the roles

If you don't wish to use separate accounts for user and admin, or have other
ideas about how the responsibilities should be split, visit Configuration ->
Roles. Edit the roles to your liking, for example by adding the executive
permissions to the Admin role. If you change the roles to yourself, don't
forget to log out and log back in.

# <a id="_toc2"></a>Adding sources to collect

Visit Configuration -> OSINT Sources. Click `Add new`. Select the collectors
node that you just created and then you should be able to see all the
collectors it has registered. Pick one (for instance the RSS collector), and
you will be able to enter all the necessary details. Finally, click `Save`.

In a few minutes, you should see freshly collected data in the Assess menu,
which is normally available to the account user / user.

# <a id="_toc3"></a>Splitting the sources into groups, and revisiting the permissions

Visit Configuration -> OSINT Source Groups to customize the groups, in which
the results are being presented. Click `Add new`, then put the various
sources you've created into different groups.

If you want to restrict the access, go to Configuration -> ACLs, and create
a new ACL by clicking `Add new`. You can pick any particular item type
(Collector, Delegation, OSINT Source, OSINT Source Group, Product Type, Report
Item, Report Item Type, Word List) and then grant *see*, *access*, or *modify*
access types to everyone, selected users, or selected roles.

# <a id="_toc4"></a>Using the default stop lists for better tag cloud

1. Visit Configuration -> Word Lists.
2. Open the default word lists (starting with `Default ...`).
3. Choose a word list URL or use the default URL present in the standard installation.
4. Under Words, click `Download from URL`.
5. Check whether the CSV file has a header or not, then click `Download from URL`. Choose which column has the value and description.
6. Optionally, you can check `Delete existing words` option to remove any previous words in the list.
7. Finally, if you are satisfied with the configuration, click `Import`.
8. The word list will be imported and you can now save it, to be applied.

# <a id="_toc5"></a>Management script - configure accounts, roles, nodes and dictionaries via commandline

Taranis NG core container comes with a simple management script that may be used to set up and configure the instance without manual interaction with the database.

To run the management script, launch a shell inside of the docker container for the core component with this command:

```bash
docker exec -it [CONTAINER] python manage.py [COMMAND] [PARAMETERS]
```

Currently, you may manage the following:

| Command     | Description | Parameters |
|-------------|-------------|------------|
| `account`     | (WIP) List, create, edit and delete user accounts. | `--list`, `-l` : list all user accounts<br /> `--create`, `-c` : create a new user account<br /> `--edit`, `-e` : edit an existing user account<br /> `--delete`, `-d` : delete a user account<br /> `--username` : specify the username<br /> `--name` : specify the user's name<br /> `--password` : specify the user's password<br /> `--roles` : specify a list of roles, divided by a comma (`,`), that the user belongs to |
| `role`     | (WIP) List, create, edit and delete user roles. | `--list`, `-l` : list all roles<br /> `--filter`, `-f` : filter roles by their name or description<br /> `--create`, `-c` : create a new role<br /> `--edit`, `-e` : edit an existing role<br /> `--delete`, `-d` : delete a role<br /> `--id` : specify the role id (in combination with `--edit` or `--delete`)<br /> `--name` : specify the role name<br /> `--description` : specify the role description (default is `""`)<br /> `--permissions` : specify a list of permissions, divided with a comma (`,`), that the role would allow |
| `collector, bot`     | (WIP) List, create, edit, delete and update nodes. | `--list`, `-l` : list all nodes<br /> `--create`, `-c` : create a new node<br /> `--edit`, `-e` : edit an existing node<br /> `--delete`, `-d` : delete a node<br /> `--update`, `-u` : re-initialize node<br /> `--all`, `-a` : update all nodes (in combination with `--update`)<br /> `--show-api-key` : show API key in plaintext (in combination with `--list`)<br /> `--id` : specify the node id (in combination with `--edit`, `--delete` or `--update`)<br /> `--name` : specify the node name<br /> `--description` : specify the collector description (default is `""`)<br /> `--api-url` : specify the collector node API url<br /> `--api-key` : specify the collector node API key |
| `dictionary`     | Update CPE, CWE and CVE dictionaries. | `--upload-cpe` : upload the CPE dictionary (expected on STDIN in XML format) to the path indicated by `CPE_UPDATE_FILE` environment variable, and update the database from that file.<br /> `--upload-cve` : upload the CVE dictionary (expected on STDIN in XML format) to the path indicated by `CVE_UPDATE_FILE` environment variable, and update the database from that file.<br /> `--upload-cwe` : upload the CWE dictionary (expected on STDIN in XML format) to the path indicated by `CWE_UPDATE_FILE` environment variable, and update the database from that file. |
| `apikey`     | List, create and delete apikeys. | `--list`, `-l` : list all apikeys<br /> `--create`, `-c` : create a new apikey<br /> `--delete`, `-d` : delete a apikey<br /> `--name` : specify the apikey name<br /> `--user` : specify the user's name<br /> `--expires` : specify the apikey expiration datetime |


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
    --api-key "supersecret"
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
    --password "supersecret" \
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

### Create new ApiKey

```bash
manage.py apikey \
    --create \
    --name "My ApiKey"
```

### Create a new API key for a user with an expiration date

```bash
manage.py apikey \
    --create \
    --name "My ApiKey" \
    --user "test_user" \
    --expire "2022-12-31 16:55"
```

Command output:

```
ApiKey 'My ApiKey' with id 3 created.
```

# <a id="_toc6"></a>Using AI in Taranis NG

This section outlines the integration of AI-enhanced functionality for generating report summaries.

### Installation

This example demonstrates how to use **Ollama** with **Taranis NG**. Ollama is an open-source tool that enables running large language models (LLMs) locally. The scenario described targets Windows with Taranis NG running inside Docker Desktop. The procedure is similar for other operating systems.

1. Install Ollama by following the instructions at [ollama.com](https://ollama.com).
2. After installation, you can begin using LLMs by executing commands in the terminal.
3. Choose and download a model that fits your use case. (e.g. `llama2`) using the command:
    ```bash
    ollama pull llama2
    ```
    Choose a model that fits your use case.
4. To verify the setup, run:
    ```bash
    ollama run llama2
    ```
    and review the output.

### Configuration

1. In Taranis NG, navigate to **Configuration → AI Providers**, then click **Add New**:

   * **Name**: `Ollama - llama2`
   * **API Type**: `openai`
   * **API URL**:
     * Use `http://localhost:11434/v1` if Ollama runs directly on the host.
     * If Taranis NG is in Docker Desktop, use `http://host.docker.internal:11434/v1` instead of `localhost`.
   * **API Key**: Not required.
   * **Model**: `llama2`

   Click **Save**. You may also configure ChatGPT or other models, provided they support the `openai` API type.

2. Navigate to **Configuration → Report Types**, then open the **Vulnerability Report** type.
   Locate the `Description` attribute and click **Edit**.
   From the **AI Provider** dropdown, select `Ollama - llama2`. In the **AI Prompt** field, enter the following:

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

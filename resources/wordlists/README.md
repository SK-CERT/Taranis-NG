# Word-list resources

## Location after installation

These files are optional, client-side import resources. They stay under
`resources/wordlists/` in the checked-out Taranis NG repository; they are not
runtime files and do not need to be copied into `/app` in the Core container or
into a global system directory such as `/opt/taranisng`.

The canonical Docker installation starts from a repository checkout, so use
the `resources/wordlists/` CSV files from the repository root, or
`../resources/wordlists/` while your shell is in the `docker/` directory.
Published application images intentionally do not contain these operator-side
import files.

Each `*_complete.csv` file is one language category in the exact format used by
the GUI's **Import from CSV** action: a semicolon-delimited UTF-8 file with the
header `value;description`. The GUI imports words into one category at a time;
it does not import an entire word list or create categories from a JSON file.

Create a word list named `Multilingual tag-cloud stop words`, enable **Use for
stop words**, add the required language categories, and import the matching CSV
into each category. Importing all files yields 24 language categories.

| Category | CSV file |
| --- | --- |
| Arabic (ar) | `ar_complete.csv` |
| Bengali (bn) | `bn_complete.csv` |
| Chinese (zh) | `zh_complete.csv` |
| Czech (cs) | `cz_complete.csv` |
| Dutch (nl) | `nl_complete.csv` |
| English (en) | `en_complete.csv` |
| French (fr) | `fr_complete.csv` |
| German (de) | `de_complete.csv` |
| Hindi (hi) | `hi_complete.csv` |
| Indonesian (id) | `id_complete.csv` |
| Italian (it) | `it_complete.csv` |
| Japanese (ja) | `ja_complete.csv` |
| Korean (ko) | `ko_complete.csv` |
| Marathi (mr) | `mr_complete.csv` |
| Polish (pl) | `pl_complete.csv` |
| Portuguese (pt) | `pt_complete.csv` |
| Russian (ru) | `ru_complete.csv` |
| Slovak (sk) | `sk_complete.csv` |
| Spanish (es) | `es_complete.csv` |
| Thai (th) | `th_complete.csv` |
| Turkish (tr) | `tr_complete.csv` |
| Ukrainian (uk) | `uk_complete.csv` |
| Urdu (ur) | `ur_complete.csv` |
| Vietnamese (vi) | `vi_complete.csv` |

The multilingual data is derived from
[stopwords-iso](https://github.com/stopwords-iso/stopwords-iso) under its MIT
license; the upstream notice is retained in `STOPWORDS-ISO-LICENSE`. To
regenerate it from an audited checkout or archive:

```console
python3 resources/wordlists/build_multilingual_stopwords.py \
  /path/to/stopwords-iso.json
```

The generator merges any existing CSV entries before writing, preserving the
project's curated English, Czech, and Slovak words while adding the upstream
sets. Its output is deterministic and can be imported directly by the GUI.

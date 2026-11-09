"""Shared public-web web helpers: language resolution and translations."""

from urllib.parse import urlencode

from flask import g, request
from lib import config


def current_language() -> str:
    """The language chosen for the current request.

    See ``lib/web/site.py``; falls back to the shipped default language outside
    of a request context.
    """
    site = getattr(g, "site", None)
    return site.language if site is not None else config.default_language()


def chosen_language() -> str | None:
    """The language the visitor picked with ``?lang=``, which forms carry on; None otherwise."""
    site = getattr(g, "site", None)
    return site.language if site is not None and site.chosen else None


def language_name(code: str) -> str:
    """The name of a language in the current request's language.

    The catalogs name the languages the public web has catalogs for; any other is shown as its code.
    """
    return config.get_translations(current_language()).get("languages", {}).get(code) or code


def language_choices() -> list[dict[str, str | bool]]:
    """The languages a visitor can switch the page to: the web's, each named in itself.

    Each comes with this page's address in it (``?lang=``, which the page's links then keep), and
    says whether it is the one shown. Empty when the web offers just one language.
    """
    site = getattr(g, "site", None)
    languages = site.languages if site is not None else []
    if len(languages) < 2:  # noqa: PLR2004 - one language is nothing to choose from
        return []
    with_catalog = config.get_translations(current_language()).get("languages", {})
    query = [(key, value) for key, value in request.args.items(multi=True) if key != "lang"]
    choices: list[dict[str, str | bool]] = []
    for code in languages:
        # Named in its own catalog; every catalog names the languages that have one.
        name = config.get_translations(code)["languages"].get(code) if code in with_catalog else None
        name = name or language_name(code)
        choices.append(
            {
                "code": code,
                "name": name[:1].upper() + name[1:],
                "url": f"{request.script_root}{request.path}?{urlencode([*query, ('lang', code)])}",
                "current": code == current_language(),
            },
        )
    return choices


def translate_report(key: str, language: str | None = None) -> str | None:
    """Get the phrase for ``key`` from the ``report`` section of the conf/i18n translations.

    The phrase is part of a report, so it is in ``language``, the one the report (or one of its
    report items) is shown in: a report nobody translated into the page's language reads in the one
    it was written in, only the page around it in the page's language. Without a known language (a
    core without languages) it is the page's language; one without a catalog gets English.
    """
    page_translations = config.get_translations(current_language())
    language = language or current_language()
    # Every catalog names the languages that have one; anything else is not a catalog's name.
    translations = config.get_translations(language if language in page_translations["languages"] else config.DEFAULT_LANGUAGE)
    return translations["report"].get(key.lower())


def translate_ui(key: str) -> str | None:
    """Get the phrase for ``key`` from the ``interface`` section of conf/i18n.

    Uses the language chosen for the current request.
    """
    return config.get_translations(current_language())["interface"].get(key.lower())


def translate(key: str, language: str | None = None) -> str:
    """The ``t()`` of report templates: a ``report`` phrase, else an ``interface`` one, else the key itself.

    The report phrase is in ``language``, the one the part rendered is shown in (see
    :func:`translate_report`); an interface phrase belongs to the page, so it is in the page's.
    """
    return translate_report(key, language) or translate_ui(key) or key

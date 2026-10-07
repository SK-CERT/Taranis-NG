"""TagCloud model.

One row per day and word: how many news items stored that day contain the word. The dashboard
sums the rows of a period and shows the words most items contain, leaving out stopwords.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from model.news_item import NewsItemData

import datetime
import json
import re
import string
from collections import Counter

from managers.cache_manager import redis_client
from managers.db_manager import db
from managers.log_manager import logger
from marshmallow import post_load
from model.setting import Setting
from model.word_list import WordListEntry
from shared.common import TZ
from shared.schema.tag_cloud import GroupedWordsSchema, TagCloudSchema
from sqlalchemy import func, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import label

RETENTION_SETTING = "TAG_CLOUD_RETENTION_DAYS"
DEFAULT_RETENTION_DAYS = 7
MAX_RETENTION_DAYS = 365

TOP_WORDS = 100
CACHE_PREFIX = "tag-cloud:top:"
# A period that includes today changes with every stored batch.
CACHE_SECONDS_TODAY = 60
# Earlier days no longer change; a past period is cached until just after the nightly cleanup
# (00:01), which may remove its oldest day.
CACHE_PAST_UNTIL = datetime.time(0, 5)

MIN_WORD_LENGTH = 3
MAX_WORD_LENGTH = 40
_EDGE_PUNCTUATION = string.punctuation + "“”‘’«»–—…"  # noqa: RUF001 - typographic marks are the point
# Letters and digits in any script, joined by inner hyphens, dots or apostrophes.
_WORD = re.compile(r"[^\W_]+(?:[-.'][^\W_]+)*")
_HEX_RUN = re.compile(r"[0-9a-f]{16,}")


class NewTagCloudSchema(TagCloudSchema):
    """Schema for creating a new TagCloud instance."""

    @post_load
    def make_tag_cloud(self, data: dict, **kwargs) -> TagCloud:  # noqa: ANN003, ARG002
        """Create a TagCloud instance from the deserialized data.

        Args:
            data: Data to make attribute from
            **kwargs: Additional arguments.

        Returns:
            TagCloud attribute
        """
        return TagCloud(**data)


class TagCloud(db.Model):
    """Model representing a tag cloud entry: one day and word."""

    __table_args__ = (db.UniqueConstraint("collected", "word", name="uq_tag_cloud_collected_word"),)

    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(), nullable=False)
    word_quantity = db.Column(db.BigInteger, nullable=False)
    collected = db.Column(db.Date, nullable=False)

    def __init__(self, word: str, word_quantity: int, collected: datetime.date) -> None:
        """Initialize a TagCloud instance.

        :param word: The word for the tag cloud.
        :param word_quantity: The quantity of the word.
        :param collected: The date the word was collected.
        """
        self.id = None
        self.word = word
        self.word_quantity = word_quantity
        self.collected = collected

    @classmethod
    def add_words(cls, counts: Counter[str]) -> None:
        """Add to today's count of each word, in one statement however many words there are.

        The day and word are a unique key, so a word's row is incremented in place and two
        batches arriving together cannot both insert it. The upsert takes the words in sorted
        order, so concurrent batches wait for each other instead of deadlocking. It runs in a
        savepoint: when it fails the error is logged and the news items are stored all the
        same, since the tag cloud is not worth a batch. The caller commits.

        :param counts: How many news items each word appeared in.
        """
        if not counts:
            return
        words = list(counts)
        # Flushed first, so a failure to store the items is not taken for a tag cloud one.
        db.session.flush()
        try:
            with db.session.begin_nested():
                db.session.execute(
                    text(
                        "INSERT INTO tag_cloud (collected, word, word_quantity) "
                        "SELECT CAST(:collected AS date), v.word, v.quantity "
                        "FROM unnest(CAST(:words AS text[]), CAST(:quantities AS bigint[])) AS v(word, quantity) "
                        "ORDER BY v.word "
                        "ON CONFLICT (collected, word) DO UPDATE SET word_quantity = tag_cloud.word_quantity + EXCLUDED.word_quantity",
                    ),
                    {"collected": datetime.datetime.now(TZ).date(), "words": words, "quantities": [counts[word] for word in words]},
                )
        except SQLAlchemyError:
            logger.exception("Tag cloud not updated; the news items are stored all the same")

    @classmethod
    def get_grouped_words(cls, number_of_days: int) -> list[dict]:
        """Retrieve grouped words using the legacy relative-day interval.

        :param number_of_days: The number of days ago to filter the tag cloud.
        :return: List of grouped words with their quantities.
        """
        date_to = datetime.datetime.now(TZ).date()
        date_from = date_to - datetime.timedelta(days=number_of_days)
        return cls.get_grouped_words_between(date_from, date_to)

    @classmethod
    def get_grouped_words_between(cls, date_from: datetime.date, date_to: datetime.date) -> list[dict]:
        """Retrieve grouped words collected in an inclusive date interval, cached in Redis.

        A period that includes today is cached for a minute. Earlier days no longer change, so a
        past period is cached until just after the nightly cleanup; there only a stopword edit
        shows up late. Without Redis the words come straight from the database.

        :param date_from: First collection date to include.
        :param date_to: Last collection date to include.
        :return: List of grouped words with their quantities.
        """
        key = f"{CACHE_PREFIX}{date_from.isoformat()}:{date_to.isoformat()}"
        cached = cls._cached_words(key)
        if cached is not None:
            return cached
        grouped_words = cls._query_grouped_words(date_from, date_to)
        cls._cache_words(key, grouped_words, cls._cache_seconds(date_to, datetime.datetime.now(TZ)))
        return grouped_words

    @classmethod
    def _query_grouped_words(cls, date_from: datetime.date, date_to: datetime.date) -> list[dict]:
        stopwords = WordListEntry.stopwords_subquery()
        grouped_words = (
            db.session.query(TagCloud.word, label("word_quantity", func.sum(TagCloud.word_quantity)))
            .filter(TagCloud.collected >= date_from)
            .filter(TagCloud.collected <= date_to)
            # Words are stored lowercase, as the stopwords come from the subquery.
            .filter(TagCloud.word.notin_(stopwords))
            .group_by(TagCloud.word)
            .order_by(db.desc("word_quantity"))
            .limit(TOP_WORDS)
            .all()
        )
        grouped_words_schema = GroupedWordsSchema(many=True)
        return grouped_words_schema.dump(grouped_words)

    @staticmethod
    def _cache_seconds(date_to: datetime.date, now: datetime.datetime) -> int:
        if date_to >= now.date():
            return CACHE_SECONDS_TODAY
        after_cleanup = datetime.datetime.combine(now.date(), CACHE_PAST_UNTIL, tzinfo=now.tzinfo)
        if now >= after_cleanup:
            after_cleanup += datetime.timedelta(days=1)
        return max(CACHE_SECONDS_TODAY, int((after_cleanup - now).total_seconds()))

    @staticmethod
    def _cached_words(key: str) -> list[dict] | None:
        try:
            value = redis_client.get(key)
        except Exception:
            # A cache is not worth failing the dashboard over.
            logger.exception("Could not read the cached tag cloud")
            return None
        return json.loads(value) if value else None

    @staticmethod
    def _cache_words(key: str, grouped_words: list[dict], seconds: int) -> None:
        try:
            redis_client.set(key, json.dumps(grouped_words), ex=seconds)
        except Exception:
            logger.exception("Could not cache the tag cloud")

    @classmethod
    def retention_days(cls) -> int:
        """How many days back the tag cloud keeps, from the TAG_CLOUD_RETENTION_DAYS setting.

        The settings API stores any text, so a value that is not a whole number falls back to
        the default, and any other is kept between 1 and 365 days.

        :return: The retention in days.
        """
        value = Setting.get_setting(None, RETENTION_SETTING, str(DEFAULT_RETENTION_DAYS))
        try:
            days = int(str(value).strip())
        except ValueError:
            return DEFAULT_RETENTION_DAYS
        return min(max(days, 1), MAX_RETENTION_DAYS)

    @classmethod
    def oldest_date(cls, today: datetime.date) -> datetime.date:
        """The first day the tag cloud still holds.

        :param today: Today's date.
        :return: The oldest date kept.
        """
        return today - datetime.timedelta(days=cls.retention_days())

    @classmethod
    def delete_words(cls) -> None:
        """Delete the days older than the retention."""
        limit = cls.oldest_date(datetime.datetime.now(TZ).date())
        cls.query.filter(cls.collected < limit).delete()
        db.session.commit()

    @staticmethod
    def _is_word(token: str) -> bool:
        if not MIN_WORD_LENGTH <= len(token) <= MAX_WORD_LENGTH or _HEX_RUN.fullmatch(token):
            return False
        if not any(character.isalpha() for character in token):
            return False
        if "." not in token:
            return True
        # Versions (openssl-3.0.7-27.el9) and dotted abbreviations (e.g) are not topics.
        return not any(character.isdigit() for character in token) and any(len(part) >= MIN_WORD_LENGTH for part in token.split("."))

    @classmethod
    def words(cls, news_item_data: NewsItemData) -> set[str]:
        """The distinct words of a news item that count towards the tag cloud.

        Words are the whitespace-separated chunks of the title, review and content, stripped of
        surrounding punctuation, that are made of letters and digits joined by inner hyphens,
        dots or apostrophes (cve-2026-1234, zero-day, node.js, don't). A chunk holding anything
        else - a URL, an e-mail address, a path, a CVSS vector, an identifier like x86_64 - is
        left out whole rather than glued into a word no other item shares. So are numbers,
        versions, hashes, and words shorter than 3 or longer than 40 characters.

        :param news_item_data: The news item data containing title, review, and content.
        :return: The words, each counted once however often it appears.
        """
        text_parts = (news_item_data.title or "", news_item_data.review or "", news_item_data.content_plaintext)
        words = set()
        for chunk in " ".join(text_parts).lower().replace("’", "'").split():  # noqa: RUF001 - typographic apostrophe
            token = chunk.strip(_EDGE_PUNCTUATION)
            if _WORD.fullmatch(token) and cls._is_word(token):
                words.add(token)
        return words

    @classmethod
    def generate_tag_cloud_words(cls, news_item_data: NewsItemData) -> None:
        """Count the words of one news item in today's tag cloud. The caller commits.

        :param news_item_data: The news item data containing title, review, and content.
        """
        cls.add_words(Counter(cls.words(news_item_data)))

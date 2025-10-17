"""TagCloud model."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from model.news_item import NewsItemData

import datetime
import re

from managers.db_manager import db
from marshmallow import post_load
from model.word_list import WordListEntry
from sqlalchemy import func
from sqlalchemy.sql import label

from shared.common import TZ
from shared.schema.tag_cloud import GroupedWordsSchema, TagCloudSchema


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
    """Model representing a tag cloud entry."""

    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String())
    word_quantity = db.Column(db.BigInteger)
    collected = db.Column(db.Date)

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
    def add_tag_clouds(cls, tag_clouds: list[TagCloud]) -> None:
        """Add a list of TagCloud instances to the database.

        :param tag_clouds: List of TagCloud instances.
        """
        for tag_cloud in tag_clouds:
            word = TagCloud.query.filter_by(word=tag_cloud.word, collected=tag_cloud.collected).first()
            if word is not None:
                word.word_quantity += 1
            else:
                db.session.add(tag_cloud)
        db.session.commit()

    @classmethod
    def get_grouped_words(cls, number_of_days: int) -> list[dict]:
        """Retrieve grouped words from the tag cloud for a specific day.

        :param number_of_days: The number of days ago to filter the tag cloud.
        :return: List of grouped words with their quantities.
        """
        day_filter = (datetime.datetime.now(TZ) - datetime.timedelta(days=number_of_days)).date()
        stopwords = WordListEntry.stopwords_subquery()
        grouped_words = (
            db.session.query(TagCloud.word, label("word_quantity", func.sum(TagCloud.word_quantity)))
            .filter(TagCloud.collected == day_filter)
            .filter(func.lower(TagCloud.word).notin_(stopwords))
            .group_by(TagCloud.word)
            .order_by(db.desc("word_quantity"))
            .limit(100)
            .all()
        )
        grouped_words_schema = GroupedWordsSchema(many=True)
        return grouped_words_schema.dump(grouped_words)

    @classmethod
    def delete_words(cls) -> None:
        """Delete words from the tag cloud that are older than a specified limit."""
        limit_days = 7
        limit = (datetime.datetime.now(TZ) - datetime.timedelta(days=limit_days)).date()
        cls.query.filter(cls.collected < limit).delete()
        db.session.commit()

    @staticmethod
    def unwanted_chars(news_item_data: NewsItemData) -> tuple[str, str, str]:
        """Remove unwanted characters from the news item data.

        :param news_item_data: The news item data containing title, review, and content.
        :return: Cleaned title, review, and content.
        """
        # \u00C0-\u024F is for accented characters, Latin-1 + Latin Extended-A + B
        search = re.compile(r"[^a-z0-9\u00C0-\u024F\s-]")
        title = search.sub("", news_item_data.title.lower())
        review = search.sub("", news_item_data.review.lower())
        content = search.sub("", news_item_data.content_plaintext.lower())
        return title, review, content

    @staticmethod
    def create_tag_cloud(word: str) -> TagCloud:
        """Create a TagCloud instance for a given word.

        :param word: The word to create a tag cloud for.
        :return: A TagCloud instance.
        """
        collected = datetime.datetime.now(TZ).date()
        return TagCloud(word, 1, collected)

    @staticmethod
    def news_item_words(title: str, review: str, content: str) -> tuple[list[str], list[str], list[str]]:
        """Extract words from the news item data.

        :param title: The title of the news item.
        :param review: The review of the news item.
        :param content: The content of the news item.
        :return: Lists of words from the title, review, and content.
        """
        re_split = re.compile(r"\s+")
        min_length = 2
        news_item_title_words = [word for word in re_split.split(title) if len(word) > min_length]
        news_item_review_words = [word for word in re_split.split(review) if len(word) > min_length]
        news_item_content_words = [word for word in re_split.split(content) if len(word) > min_length]
        return news_item_title_words, news_item_review_words, news_item_content_words

    @staticmethod
    def news_items_words(
        title: str,
        review: str,
        content: str,
        news_items_title_words: list[str],
        news_items_review_words: list[str],
        news_items_content_words: list[str],
    ) -> tuple[list[str], list[str], list[str]]:
        """Aggregate words from multiple news items.

        :param title: The title of the news item.
        :param review: The review of the news item.
        :param content: The content of the news item.
        :param news_items_title_words: List to store title words.
        :param news_items_review_words: List to store review words.
        :param news_items_content_words: List to store content words.
        :return: Aggregated lists of words from titles, reviews, and contents.
        """
        news_item_title_words, news_item_review_words, news_item_content_words = TagCloud.news_item_words(title, review, content)
        news_items_title_words.extend(news_item_title_words)
        news_items_review_words.extend(news_item_review_words)
        news_items_content_words.extend(news_item_content_words)
        return news_items_title_words, news_items_review_words, news_items_content_words

    @classmethod
    def generate_tag_cloud_words(cls, news_item_data: NewsItemData) -> None:
        """Generate tag cloud words from news item data.

        :param news_item_data: The news item data containing title, review, and content.
        """
        news_items_title_words = []
        news_items_review_words = []
        news_items_content_words = []
        tag_cloud_words = []

        title, review, content = TagCloud.unwanted_chars(news_item_data)

        news_items_title_words, news_items_review_words, news_items_content_words = TagCloud.news_items_words(
            title,
            review,
            content,
            news_items_title_words,
            news_items_review_words,
            news_items_content_words,
        )
        news_items_words = news_items_title_words + news_items_review_words + news_items_content_words

        tag_cloud_words = [TagCloud.create_tag_cloud(word) for word in set(news_items_words)]

        cls.add_tag_clouds(tag_cloud_words)

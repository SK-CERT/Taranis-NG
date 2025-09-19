"""News item model."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from model.remote import RemoteNode
    from model.user import User
    from sqlalchemy.orm import Query

import base64
import uuid
from datetime import datetime, timedelta
from http import HTTPStatus

from managers.db_manager import db
from marshmallow import fields, post_load
from model.acl_entry import ACLEntry
from model.osint_source import OSINTSource, OSINTSourceGroup
from model.tag_cloud import TagCloud
from sqlalchemy import and_, func, or_, orm

from shared.common import TZ, remove_empty_html_tags, simplify_html_text, smart_truncate, strip_html
from shared.schema.acl_entry import ItemType
from shared.schema.news_item import NewsItemAggregateSchema, NewsItemAttributeSchema, NewsItemDataSchema, NewsItemRemoteSchema, NewsItemSchema


class NewsItemAttribute(db.Model):
    """News item attribute model.

    Attributes:
        id (int): ID
        key (str): Key
        value (str): Value
        binary_mime_type (str): Binary MIME type
        binary_data (bytes): Binary data
        created (datetime): Created
        remote_node_id (int): Remote node ID
        remote_user (str): Remote user
    """

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(), nullable=False)
    value = db.Column(db.String(), nullable=False)
    binary_mime_type = db.Column(db.String())
    binary_data = orm.deferred(db.Column(db.LargeBinary))
    created = db.Column(db.DateTime, default=datetime.now)

    remote_node_id = db.Column(db.Integer, db.ForeignKey("remote_node.id"), nullable=True)
    remote_user = db.Column(db.String())

    def __init__(self, key: str, value: str, binary_mime_type: str, binary_value: str | None = None) -> None:
        """Initialize news item attribute."""
        # self.id = id
        self.id = None
        self.key = key
        self.value = value
        self.binary_mime_type = binary_mime_type
        self.binary_data = base64.b64decode(binary_value) if binary_value else None

    @classmethod
    def find(cls, attribute_id: int) -> NewsItemAttribute:
        """Find news item attribute.

        Args:
            attribute_id: Attribute ID
        Returns:
            News item attribute
        """
        return db.session.get(cls, attribute_id)


class NewNewsItemAttributeSchema(NewsItemAttributeSchema):
    """New news item attribute schema."""

    @post_load
    def make(self, data: dict, **kwargs) -> NewsItemAttribute:  # noqa: ANN003, ARG002
        """Make news item attribute.

        Args:
            data: Data to make news item attribute from
            **kwargs: Additional arguments.

        Returns:
            News item attribute
        """
        return NewsItemAttribute(**data)


class NewsItemData(db.Model):
    """News item data model.

    Attributes:
        id (int): News item data ID
        hash (str): News item data hash
        title (str): News item title
        review (str): News item review
        source (str): News item source
        link (str): News item link
        published (str): News item published
        updated (datetime): News item updated
        attributes (list[NewsItemAttribute]): News item attributes
        osint_source_id (str): OSINT source ID
        remote_source (str): Remote source
    """

    id = db.Column(db.String(64), primary_key=True)
    hash = db.Column(db.String())

    title = db.Column(db.String())
    review = db.Column(db.String())
    author = db.Column(db.String())
    source = db.Column(db.String())
    link = db.Column(db.String())
    language = db.Column(db.String())
    content = db.Column(db.String())

    collected = db.Column(db.DateTime)
    published = db.Column(db.String())
    updated = db.Column(db.DateTime)

    attributes = db.relationship("NewsItemAttribute", secondary="news_item_data_news_item_attribute", lazy="selectin")

    osint_source_id = db.Column(db.String, db.ForeignKey("osint_source.id"), nullable=True)
    osint_source = db.relationship("OSINTSource")
    remote_source = db.Column(db.String())

    def __init__(
        self,
        id: str,  # noqa: A002
        hash: str,  # noqa: A002
        title: str,
        review: str,
        source: str,
        link: str,
        published: str,
        author: str,
        collected: datetime,
        content: str,
        osint_source_id: str,
        attributes: list[NewsItemAttribute],
    ) -> None:
        """Initialize news item data."""
        if id is None:
            self.id = str(uuid.uuid4())
        else:
            self.id = id
        self.hash = hash
        self.title = title
        self.review = review
        self.source = source
        self.link = link
        self.published = published
        self.author = author
        self.collected = collected
        self.content = content
        self.attributes = attributes
        self.osint_source_id = osint_source_id
        self.updated = datetime.now(TZ)

    @classmethod
    def allowed_with_acl(cls, news_item_data_id: str, user: User, see: bool, access: bool, modify: bool) -> bool:
        """Check if user is allowed to access news item data.

        Args:
            news_item_data_id: News item data ID
            user: User
            see: See permission
            access: Access permission
            modify: Modify permission
        Returns:
            True if user is allowed to access news item data, False otherwise
        """
        news_item_data = db.session.get(cls, news_item_data_id)
        if news_item_data.remote_source is not None:
            return True
        query = db.session.query(NewsItemData.id).distinct().group_by(NewsItemData.id).filter(NewsItemData.id == news_item_data_id)

        query = query.join(OSINTSource, NewsItemData.osint_source_id == OSINTSource.id)

        query = query.outerjoin(
            ACLEntry,
            or_(
                and_(NewsItemData.osint_source_id == ACLEntry.item_id, ACLEntry.item_type == ItemType.OSINT_SOURCE),
                and_(OSINTSource.collector_id == ACLEntry.item_id, ACLEntry.item_type == ItemType.COLLECTOR),
            ),
        )

        query = ACLEntry.apply_query(query, user, see, access, modify)

        return query.scalar() is not None

    @classmethod
    def identical(cls, hash_string: str) -> bool:
        """Check if news item data is identical.

        Args:
            hash_string (str): Hash string
        Returns:
            True if news item data is identical, False otherwise
        """
        return db.session.query(db.exists().where(NewsItemData.hash == hash_string)).scalar()

    @classmethod
    def find_by_hash(cls, hash_string: str) -> NewsItemData | None:
        """Find news item data by hash.

        Args:
            hash_string (str): Hash string
        Returns:
            News item data
        """
        return cls.query.filter(NewsItemData.hash == hash_string).first()

    @classmethod
    def count_all(cls) -> int:
        """Count all news items.

        Returns:
            Number of news items
        """
        return cls.query.count()

    @classmethod
    def latest_collected(cls) -> str:
        """Get latest collected news item.

        Returns:
            Latest collected news item
        """
        news_item_data = cls.query.order_by(db.desc(NewsItemData.collected)).limit(1).all()
        if len(news_item_data) > 0:
            return news_item_data[0].collected.strftime("%d.%m.%Y - %H:%M")
        return ""

    @classmethod
    def get_all_news_items_data(cls, limit: str) -> dict:
        """Get all news items data.

        Args:
            limit (str): Limit
        Returns:
            All news items data
        """
        limit = datetime.strptime(limit, "%d.%m.%Y - %H:%M").replace(tzinfo=TZ)
        news_items_data = cls.query.filter(cls.collected >= limit).all()
        news_items_data_schema = NewsItemDataSchema(many=True)
        return news_items_data_schema.dump(news_items_data)

    @classmethod
    def attribute_value_identical(cls, news_item_data_id: int, value: str) -> bool:
        """Check if attribute value is identical.

        Args:
            news_item_data_id (int): ID
            value (str): Value
        Returns:
            True if attribute value is identical, False otherwise
        """
        return (
            NewsItemAttribute.query.join(NewsItemDataNewsItemAttribute)
            .join(NewsItemData)
            .filter(NewsItemData.id == news_item_data_id)
            .filter(NewsItemAttribute.value == value)
            .scalar()
        )

    @classmethod
    def update_news_item_attributes(cls, news_item_id: int, attributes: list[NewsItemAttribute]) -> None:
        """Update news item attributes.

        Args:
            news_item_id (int): News item ID
            attributes (list[NewsItemAttribute]): Attributes
        """
        news_item = cls.query.filter_by(id=news_item_id).first()

        attributes_schema = NewNewsItemAttributeSchema(many=True)
        attributes = attributes_schema.load(attributes)

        for attribute in attributes:
            if not cls.attribute_value_identical(news_item_id, attribute.value):
                news_item.attributes.append(attribute)
                db.session.commit()

    @classmethod
    def get_for_sync(cls, last_synced: datetime, osint_sources: list[OSINTSource]) -> tuple[dict, datetime]:
        """Get news items for sync.

        Args:
            last_synced (datetime): Last synced
            osint_sources (list[OSINTSource]): OSINT sources
        Returns:
            News items for sync
        """
        osint_source_ids = set()
        for osint_source in osint_sources:
            osint_source_ids.add(osint_source.id)

        last_sync_time = datetime.now(TZ)
        query = cls.query.filter(
            NewsItemData.updated >= last_synced,
            NewsItemData.updated <= last_sync_time,
            NewsItemData.osint_source_id.in_(osint_source_ids),
        )

        news_items = query.all()
        news_item_remote_schema = NewsItemRemoteSchema(many=True)
        for news_item in news_items:
            total_relevance = NewsItem.get_total_relevance(news_item.id)
            if total_relevance > 0:
                news_item.relevance = 1
            elif total_relevance < 0:
                news_item.relevance = -1
            else:
                news_item.relevance = 0

        items = news_item_remote_schema.dump(news_items)

        return items, last_sync_time


class NewNewsItemDataSchema(NewsItemDataSchema):
    """New news item data schema.

    Attributes:
        attributes: News item attributes
    """

    attributes = fields.Nested(NewNewsItemAttributeSchema, many=True)

    @post_load
    def make(self, data: dict, **kwargs) -> NewsItemData:  # noqa: ANN003, ARG002
        """Make news item data.

        Args:
            data: Data to make news item data from
            **kwargs: Additional arguments.

        Returns:
            News item data
        """
        return NewsItemData(**data)


class NewsItem(db.Model):
    """News item model.

    Attributes:
        id: News item ID
        read: Read
        important: Important
        likes: Likes
        dislikes: Dislikes
        relevance: Relevance
        news_item_data_id: News item data ID
        news_item_data: News item data
        news_item_aggregate_id: News item aggregate ID
    """

    id = db.Column(db.Integer, primary_key=True)

    read = db.Column(db.Boolean, default=False)
    important = db.Column(db.Boolean, default=False)

    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)
    relevance = db.Column(db.Integer, default=0)

    news_item_data_id = db.Column(db.String, db.ForeignKey("news_item_data.id"))
    news_item_data = db.relationship("NewsItemData", lazy="selectin")

    news_item_aggregate_id = db.Column(db.Integer, db.ForeignKey("news_item_aggregate.id"))

    @classmethod
    def find(cls, news_item_id: int) -> NewsItem:
        """Find news item.

        Args:
            news_item_id (int): News item ID
        Returns:
            News item
        """
        return db.session.get(cls, news_item_id)

    @classmethod
    def get_all_with_data(cls, news_item_data_id: int) -> list[NewsItem]:
        """Get all news items with data.

        Args:
            news_item_data_id (int): News item data ID
        Returns:
            All news items with data
        """
        return cls.query.filter_by(news_item_data_id=news_item_data_id).all()

    @classmethod
    def get_detail_json(cls, news_item_data_id: int) -> dict:
        """Get news item detail JSON.

        Args:
            news_item_data_id (int): News item data ID
        Returns:
            News item detail JSON
        """
        news_item = db.session.get(cls, news_item_data_id)
        news_item_schema = NewsItemSchema()
        return news_item_schema.dump(news_item)

    @classmethod
    def get_total_relevance(cls, news_item_data_id: int) -> int:
        """Get total relevance.

        Args:
            news_item_data_id (int): News item data ID
        Returns:
            Total relevance
        """
        query = db.session.query(NewsItem.relevance).filter(NewsItem.news_item_data_id == news_item_data_id)
        result = query.all()
        total_relevance = 0
        for row in result:
            total_relevance += int(row[0])

        return total_relevance

    @classmethod
    def get_all_by_group_and_source_query(cls, group_id: int, source_id: int, time_limit: datetime) -> Query:
        """Get all news items by group and source query.

        Args:
            group_id (int): Group ID
            source_id (int): Source ID
            time_limit (datetime): Time limit
        Returns:
            All news items by group and source query
        """
        query = cls.query.join(NewsItemData, NewsItemData.id == NewsItem.news_item_data_id)
        query = query.filter(NewsItemData.osint_source_id == source_id, NewsItemData.collected >= time_limit)
        query = query.join(NewsItemAggregate, NewsItemAggregate.id == NewsItem.news_item_aggregate_id)
        return query.filter(NewsItemAggregate.osint_source_group_id == group_id)

    @classmethod
    def allowed_with_acl(cls, news_item_id: int, user: User, see: bool, access: bool, modify: bool) -> bool:
        """Check if user is allowed to access news item.

        Args:
            news_item_id (int): News item ID
            user (User): User
            see (bool): See permission
            access (bool): Access permission
            modify (bool): Modify permission
        Returns:
            True if user is allowed to access news item, False otherwise
        """
        news_item = db.session.get(cls, news_item_id)
        if news_item.news_item_data.remote_source is not None:
            return True
        query = db.session.query(NewsItem.id).distinct().group_by(NewsItem.id).filter(NewsItem.id == news_item_id)

        query = query.join(NewsItemData, NewsItem.news_item_data_id == NewsItemData.id)
        # LEFT JOIN because when deleting Osint sources -> SET NULL to News items -> ACL right fails
        query = query.outerjoin(OSINTSource, NewsItemData.osint_source_id == OSINTSource.id)
        query = query.outerjoin(
            ACLEntry,
            or_(
                and_(NewsItemData.osint_source_id == ACLEntry.item_id, ACLEntry.item_type == ItemType.OSINT_SOURCE),
                and_(OSINTSource.collector_id == ACLEntry.item_id, ACLEntry.item_type == ItemType.COLLECTOR),
            ),
        )

        query = ACLEntry.apply_query(query, user, see, access, modify)

        return query.scalar() is not None

    @classmethod
    def get_acl_status(cls, news_item_id: int, user: User) -> tuple[bool, bool, bool]:
        """Get ACL status.

        Args:
            news_item_id (int): News item ID
            user (User): User
        Returns:
             tuple[bool, bool, bool]: Whether the user has see, access and modify permissions.
        """
        news_item = db.session.get(cls, news_item_id)
        if news_item.news_item_data.remote_source is not None:
            return True, True, True
        query = (
            db.session.query(
                NewsItem.id,
                func.count().filter(ACLEntry.id > 0).label("acls"),
                func.count().filter(ACLEntry.see.is_(True)).label("see"),
                func.count().filter(ACLEntry.access.is_(True)).label("access"),
                func.count().filter(ACLEntry.modify.is_(True)).label("modify"),
            )
            .distinct()
            .group_by(NewsItem.id)
            .filter(NewsItem.id == news_item_id)
        )

        query = query.join(NewsItemData, NewsItem.news_item_data_id == NewsItemData.id)
        query = query.outerjoin(OSINTSource, NewsItemData.osint_source_id == OSINTSource.id)

        query = query.outerjoin(
            ACLEntry,
            or_(
                and_(NewsItemData.osint_source_id == ACLEntry.item_id, ACLEntry.item_type == ItemType.OSINT_SOURCE),
                and_(OSINTSource.collector_id == ACLEntry.item_id, ACLEntry.item_type == ItemType.COLLECTOR),
            ),
        )

        query = ACLEntry.apply_query(query, user, see=False, access=False, modify=False)

        result = query.all()
        see = result[0].see > 0 or result[0].acls == 0
        access = result[0].access > 0 or result[0].acls == 0
        modify = result[0].modify > 0 or result[0].acls == 0

        return see, access, modify

    def vote(self, data: dict, user_id: int) -> None:
        """Vote.

        Args:
            data (dict): Data
            user_id (int): User ID
        """
        if "vote" in data:
            self.news_item_data.updated = datetime.now(TZ)
            vote = NewsItemVote.find(self.id, user_id)
            if vote is None:
                vote = NewsItemVote(self.id, user_id)
                db.session.add(vote)

            if data["vote"] > 0:
                if vote.like is True:
                    self.likes -= 1
                    self.relevance -= 1
                    vote.like = False
                else:
                    self.likes += 1
                    self.relevance += 1
                    vote.like = True
                    if vote.dislike is True:
                        self.dislikes -= 1
                        self.relevance += 1
                        vote.dislike = False
            elif vote.dislike is True:
                self.dislikes -= 1
                self.relevance += 1
                vote.dislike = False
            else:
                self.dislikes += 1
                self.relevance -= 1
                vote.dislike = True
                if vote.like is True:
                    self.likes -= 1
                    self.relevance -= 1
                    vote.like = False

    @classmethod
    def update(cls, news_item_id: int, data: dict, user_id: int) -> tuple[str, dict, int]:
        """Update.

        Args:
            news_item_id (int): ID
            data (dict): Data
            user_id (int): User ID
        Returns:
            tuple[str, dict, int]: Success message, data and status code
        """
        news_item = cls.find(news_item_id)

        news_item.update_status(data, user_id)

        NewsItemAggregate.update_status(news_item.news_item_aggregate_id)
        db.session.commit()

        if "vote" in data:
            return "success", {news_item.news_item_data.osint_source_id}, HTTPStatus.OK
        return "success", {}, HTTPStatus.OK

    def update_status(self, data: dict, user_id: int) -> None:
        """Update status.

        Args:
            data (dict): Data
            user_id (int): User ID
        """
        self.vote(data, user_id)

        if "read" in data:
            self.read = not self.read

        if "important" in data:
            self.important = not self.important

    @classmethod
    def delete(cls, news_item_id: int) -> tuple[str, int]:
        """Delete.

        Args:
            news_item_id (int): News item ID
        Returns:
            tuple[str, int]: Success message and status code
        """
        news_item = cls.find(news_item_id)
        if NewsItemAggregate.action_allowed([{"type": "AGGREGATE", "id": news_item.news_item_aggregate_id}]) is False:
            return "aggregate_in_use", HTTPStatus.INTERNAL_SERVER_ERROR
        aggregate_id = news_item.news_item_aggregate_id
        aggregate = NewsItemAggregate.find(aggregate_id)
        aggregate.news_items.remove(news_item)
        NewsItemVote.delete_all(news_item_id)
        db.session.delete(news_item)
        NewsItemAggregate.update_status(aggregate_id)
        db.session.commit()

        return "success", HTTPStatus.OK

    @classmethod
    def delete_only(cls, news_item: NewsItem) -> None:
        """Delete only.

        Args:
            news_item (NewsItem): News item
        """
        NewsItemVote.delete_all(news_item.id)
        db.session.delete(news_item)


class NewsItemVote(db.Model):
    """News item vote model.

    Attributes:
        id: ID
        like: Like
        dislike: Dislike
        news_item_id: News item ID
        user_id: User ID
        remote_node_id: Remote node ID
        remote_user: Remote user
    """

    id = db.Column(db.Integer, primary_key=True)
    like = db.Column(db.Boolean)
    dislike = db.Column(db.Boolean)
    news_item_id = db.Column(db.Integer, db.ForeignKey("news_item.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    remote_node_id = db.Column(db.Integer, db.ForeignKey("remote_node.id"), nullable=True)
    remote_user = db.Column(db.String())

    def __init__(self, news_item_id: int, user_id: int) -> None:
        """Initialize news item vote."""
        self.id = None
        self.news_item_id = news_item_id
        self.user_id = user_id
        self.like = False
        self.dislike = False

    @classmethod
    def find(cls, news_item_id: int, user_id: int) -> NewsItemVote:
        """Find news item vote.

        Args:
            news_item_id (int): News item ID
            user_id (int): User ID
        Returns:
            News item vote
        """
        return cls.query.filter_by(news_item_id=news_item_id, user_id=user_id).first()

    @classmethod
    def delete_all(cls, news_item_id: int) -> None:
        """Delete all.

        Args:
            news_item_id (int): News item ID
        """
        votes = cls.query.filter_by(news_item_id=news_item_id).all()
        for vote in votes:
            db.session.delete(vote)

    @classmethod
    def delete_for_remote_node(cls, news_item_id: int, remote_node_id: int) -> int:
        """Delete for remote node.

        Args:
            news_item_id (int): News item ID
            remote_node_id (int): Remote node ID
        Returns:
            int: 1 if like, -1 if dislike, 0 otherwise
        """
        vote = cls.query.filter_by(news_item_id=news_item_id, remote_node_id=remote_node_id).first()
        if vote is not None:
            db.session.delete(vote)
            if vote.like is True:
                return 1
            return -1
        return 0


class NewsItemAggregate(db.Model):
    """News item aggregate model.

    Attributes:
        id: ID
        title: Title
        description: Description
        created: Created
        read: Read
        important: Important
        likes: Likes
        dislikes: Dislikes
        relevance: Relevance
        comments: Comments
        osint_source_group_id: OSINT source group ID
        news_items: News items
        news_item_attributes: News item attributes
    """

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String())
    description = db.Column(db.String())

    created = db.Column(db.DateTime)

    read = db.Column(db.Boolean, default=False)
    important = db.Column(db.Boolean, default=False)

    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)
    relevance = db.Column(db.Integer, default=0)

    comments = db.Column(db.String(), default="")

    osint_source_group_id = db.Column(db.String, db.ForeignKey("osint_source_group.id"))

    news_items = db.relationship("NewsItem", lazy="joined")

    news_item_attributes = db.relationship("NewsItemAttribute", secondary="news_item_aggregate_news_item_attribute", lazy="selectin")

    @classmethod
    def find(cls, news_item_aggregate_id: int) -> NewsItemAggregate:
        """Find news item aggregate.

        Args:
            news_item_aggregate_id (int): News item aggregate ID
        Returns:
            News item aggregate
        """
        return db.session.get(cls, news_item_aggregate_id)

    @classmethod
    def get_by_group(cls, group_id: int, filters: dict, offset: int, limit: int, user: User) -> tuple[list[NewsItemAggregate], int]:
        """Get by group.

        Args:
            group_id (int): Group ID
            filters (dict): Filter
            offset (int): Offset
            limit (int): Limit
            user (User): User
        Returns:
            tuple[list[NewsItemAggregate], int]: News item aggregates and total count
        """
        query = cls.query.distinct().group_by(NewsItemAggregate.id)

        query = query.filter(NewsItemAggregate.osint_source_group_id == group_id)

        query = query.join(NewsItem, NewsItem.news_item_aggregate_id == NewsItemAggregate.id)
        query = query.join(NewsItemData, NewsItem.news_item_data_id == NewsItemData.id)
        query = query.outerjoin(OSINTSource, NewsItemData.osint_source_id == OSINTSource.id)

        query = query.outerjoin(
            ACLEntry,
            or_(
                and_(NewsItemData.osint_source_id == ACLEntry.item_id, ACLEntry.item_type == ItemType.OSINT_SOURCE),
                and_(OSINTSource.collector_id == ACLEntry.item_id, ACLEntry.item_type == ItemType.COLLECTOR),
            ),
        )

        query = ACLEntry.apply_query(query, user, see=True, access=False, modify=False)

        if "search" in filters and filters["search"] != "":
            search_string = "%" + filters["search"].lower() + "%"
            query = query.join(
                NewsItemAggregateSearchIndex,
                NewsItemAggregate.id == NewsItemAggregateSearchIndex.news_item_aggregate_id,
            ).filter(NewsItemAggregateSearchIndex.data.like(search_string))

        if "read" in filters and filters["read"].lower() == "true":
            query = query.filter(NewsItemAggregate.read.is_(False))

        if "important" in filters and filters["important"].lower() == "true":
            query = query.filter(NewsItemAggregate.important.is_(True))

        if "relevant" in filters and filters["relevant"].lower() == "true":
            query = query.filter(NewsItemAggregate.likes > 0)

        if "in_analyze" in filters and filters["in_analyze"].lower() == "true":
            query = query.join(ReportItemNewsItemAggregate, NewsItemAggregate.id == ReportItemNewsItemAggregate.news_item_aggregate_id)

        if "range" in filters and filters["range"] != "ALL":
            date_limit = datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0)  # "TODAY"
            if filters["range"] == "WEEK":
                date_limit -= timedelta(days=date_limit.weekday())
            elif filters["range"] == "MONTH":
                date_limit = date_limit.replace(day=1)
            query = query.filter(NewsItemAggregate.created >= date_limit)

        if "sort" in filters:
            if filters["sort"] == "DATE_DESC":
                query = query.order_by(db.desc(NewsItemAggregate.created), db.desc(NewsItemAggregate.id))

            elif filters["sort"] == "DATE_ASC":
                query = query.order_by(db.asc(NewsItemAggregate.created), db.asc(NewsItemAggregate.id))

            elif filters["sort"] == "RELEVANCE_DESC":
                query = query.order_by(db.desc(NewsItemAggregate.relevance), db.desc(NewsItemAggregate.id))

            elif filters["sort"] == "RELEVANCE_ASC":
                query = query.order_by(db.asc(NewsItemAggregate.relevance), db.asc(NewsItemAggregate.id))

        return query.offset(offset).limit(limit).all(), query.count()

    @classmethod
    def get_by_group_json(cls, group_id: int, filters: dict, offset: int, limit: int, user: User) -> dict:
        """Get by group JSON.

        Args:
            group_id (int): Group ID
            filters (dict): Filter
            offset (int): Offset
            limit (int): Limit
            user (User): User
        Returns:
            dict: News item aggregates JSON
        """
        news_item_aggregates, count = cls.get_by_group(group_id, filters, offset, limit, user)
        for news_item_aggregate in news_item_aggregates:
            news_item_aggregate.me_like = False
            news_item_aggregate.me_dislike = False
            for news_item in news_item_aggregate.news_items:
                see, access, modify = NewsItem.get_acl_status(news_item.id, user)
                news_item.see = see
                news_item.access = access
                news_item.modify = modify
                vote = NewsItemVote.find(news_item.id, user.id)
                if vote is not None:
                    news_item.me_like = vote.like
                    news_item.me_dislike = vote.dislike
                else:
                    news_item.me_like = False
                    news_item.me_dislike = False

                if news_item.me_like is True:
                    news_item_aggregate.me_like = True

                if news_item.me_dislike is True:
                    news_item_aggregate.me_dislike = True

            news_item_aggregate.in_reports_count = ReportItemNewsItemAggregate.count(news_item_aggregate.id)

        news_item_aggregate_schema = NewsItemAggregateSchema(many=True)
        items = news_item_aggregate_schema.dump(news_item_aggregates)
        for aggregate in items:
            for news_item in aggregate["news_items"][:]:
                if news_item["see"] is False:
                    aggregate["news_items"].remove(news_item)

        return {"total_count": count, "items": items}

    @classmethod
    def create_new_for_all_groups(cls, news_item_data: NewsItemData) -> None:
        """Create new for all groups.

        Args:
            news_item_data (NewsItemData): News item data
        """
        groups = OSINTSourceGroup.get_all_with_source(news_item_data.osint_source_id)
        for group in groups:
            news_item = NewsItem()
            news_item.news_item_data = news_item_data
            db.session.add(news_item)

            aggregate = NewsItemAggregate()
            aggregate.title = news_item_data.title
            aggregate.description = news_item_data.review
            aggregate.created = news_item_data.collected
            aggregate.osint_source_group_id = group.id
            aggregate.news_items.append(news_item)
            db.session.add(aggregate)

            NewsItemAggregateSearchIndex.prepare(aggregate)

    @classmethod
    def create_new_for_group(cls, news_item_data: NewsItemData, osint_source_group_id: int) -> None:
        """Create new for group.

        Args:
            news_item_data (NewsItemData): News item data
            osint_source_group_id (int): OSINT source group ID
        """
        news_item = NewsItem()
        news_item.news_item_data = news_item_data
        db.session.add(news_item)

        aggregate = NewsItemAggregate()
        aggregate.title = news_item_data.title
        aggregate.description = news_item_data.review
        aggregate.created = news_item_data.collected
        aggregate.osint_source_group_id = osint_source_group_id
        aggregate.news_items.append(news_item)
        db.session.add(aggregate)

        NewsItemAggregateSearchIndex.prepare(aggregate)

    @classmethod
    def add_news_items(cls, news_items_data_list: list[dict]) -> set[int]:
        """Add news items.

        Args:
            news_items_data_list (list[dict]): News items data list
        Returns:
            set[int]: OSINT source IDs
        """
        news_item_data_schema = NewNewsItemDataSchema(many=True)
        news_items_data = news_item_data_schema.load(news_items_data_list)
        osint_source_ids = set()

        for news_item_data in news_items_data:
            if not NewsItemData.identical(news_item_data.hash):
                db.session.add(news_item_data)
                cls.create_new_for_all_groups(news_item_data)
                osint_source_ids.add(news_item_data.osint_source_id)

                TagCloud.generate_tag_cloud_words(news_item_data)

        db.session.commit()

        for source_id in osint_source_ids:
            OSINTSource.update_collected(source_id)

        return osint_source_ids

    @classmethod
    def add_news_item(cls, news_item_data: NewsItemData) -> dict[int]:
        """Add news item.

        Args:
            news_item_data (NewsItemData): News item data
        Returns:
            dict[int]: OSINT source IDs
        """
        news_item_data_schema = NewNewsItemDataSchema()
        news_item_data = news_item_data_schema.load(news_item_data)
        if not news_item_data.id:
            news_item_data.id = str(uuid.uuid4())
        if not news_item_data.hash:
            news_item_data.hash = news_item_data.id
        # sanitize news item from user manual input
        news_item_data.title = smart_truncate(strip_html(news_item_data.title), 200)
        news_item_data.review = smart_truncate(strip_html(news_item_data.review))
        news_item_data.content = remove_empty_html_tags(simplify_html_text(news_item_data.content))
        news_item_data.author = strip_html(news_item_data.author)
        db.session.add(news_item_data)
        cls.create_new_for_all_groups(news_item_data)
        TagCloud.generate_tag_cloud_words(news_item_data)
        db.session.commit()

        return {news_item_data.osint_source_id}

    @classmethod
    def reassign_to_new_groups(cls, osint_source_id: int, default_group_id: int) -> None:
        """Reassign to new groups.

        Args:
            osint_source_id (int): OSINT source ID
            default_group_id (int): Default group ID
        """
        time_limit = datetime.now(TZ) - timedelta(days=7)
        news_items_query = NewsItem.get_all_by_group_and_source_query(default_group_id, osint_source_id, time_limit)
        for news_item in news_items_query:
            news_item_data = news_item.news_item_data
            aggregate = NewsItemAggregate.find(news_item.news_item_aggregate_id)
            aggregate.news_items.remove(news_item)
            NewsItemVote.delete_all(news_item.id)
            db.session.delete(news_item)
            NewsItemAggregate.update_status(aggregate.id)
            cls.create_new_for_all_groups(news_item_data)
            db.session.commit()

    @classmethod
    def add_remote_news_items(cls, news_items_data_list: list[dict], remote_node: RemoteNode, osint_source_group_id: int) -> None:
        """Add remote news items.

        Args:
            news_items_data_list (list[dict]): News items data list
            remote_node (RemoteNode): Remote node
            osint_source_group_id (int): OSINT source group ID
        """
        news_item_data_schema = NewNewsItemDataSchema(many=True)
        news_items_data = news_item_data_schema.load(news_items_data_list)

        news_item_data_ids = set()
        for news_item_data in news_items_data:
            news_item_data.remote_source = remote_node.name
            for attribute in news_item_data.attributes:
                attribute.remote_node_id = remote_node.id
                attribute.remote_user = remote_node.name

            original_news_item = NewsItemData.find_by_hash(news_item_data.hash)

            if original_news_item is None:
                db.session.add(news_item_data)
                cls.create_new_for_group(news_item_data, osint_source_group_id)
                news_item_data_ids.add(str(news_item_data.id))
            else:
                original_news_item.updated = datetime.now(TZ)
                for attribute in original_news_item.attributes[:]:
                    if attribute.remote_node_id == remote_node.id:
                        original_news_item.attributes.remove(attribute)
                        db.session.delete(attribute)

                original_news_item.attributes.extend(news_item_data.attributes)
                news_item_data_ids.add(str(original_news_item.id))

        db.session.commit()

        aggregate_ids = set()
        for i, news_item_data_id in enumerate(news_item_data_ids):
            news_items = NewsItem.get_all_with_data(news_item_data_id)
            for news_item in news_items:
                had_relevance = NewsItemVote.delete_for_remote_node(news_item.id, remote_node.id)
                news_item.relevance -= had_relevance
                if had_relevance > 0:
                    news_item.likes -= 1
                elif had_relevance < 0:
                    news_item.dislikes -= 1

                if news_items_data_list[i]["relevance"] != 0:
                    vote = NewsItemVote(news_item.id, None)
                    vote.remote_node_id = remote_node.id
                    vote.remote_user = remote_node.name
                    if news_items_data_list[i]["relevance"] > 0:
                        vote.like = True
                        news_item.relevance += 1
                        news_item.likes += 1
                    else:
                        vote.dislike = True
                        news_item.relevance -= 1
                        news_item.dislikes += 1

                    db.session.add(vote)

                aggregate_ids.add(news_item.news_item_aggregate_id)

        db.session.commit()

        for aggregate_id in aggregate_ids:
            cls.update_status(aggregate_id)

        db.session.commit()

    @classmethod
    def update(cls, news_item_aggregate_id: int, data: dict, user: User) -> tuple[str, set[int], int]:
        """Update.

        Args:
            news_item_aggregate_id (int): ID
            data (dict): Data
            user (User): User
        Returns:
            Success message, OSINT source IDs and status code
        """
        aggregate = cls.find(news_item_aggregate_id)

        all_important = True
        for news_item in aggregate.news_items:
            if news_item.important is False:
                all_important = False

        osint_source_ids = set()

        for news_item in aggregate.news_items:
            if NewsItem.allowed_with_acl(news_item.id, user, see=False, access=False, modify=True):
                if "vote" in data:
                    osint_source_ids.add(news_item.news_item_data.osint_source_id)
                    news_item.vote(data, user.id)

                if "read" in data:
                    news_item.read = not aggregate.read

                if "important" in data:
                    news_item.important = not all_important

        if "title" in data:
            aggregate.title = data["title"]

        if "description" in data:
            aggregate.description = data["description"]

        if "comments" in data:
            aggregate.comments = data["comments"]

        NewsItemAggregate.update_status(aggregate.id)
        NewsItemAggregateSearchIndex.prepare(aggregate)

        db.session.commit()

        return "success", osint_source_ids, HTTPStatus.OK

    @classmethod
    def delete(cls, news_item_aggregate_id: int, user: User) -> tuple[str, int]:
        """Delete.

        Args:
            news_item_aggregate_id (int): News item aggregate ID
            user (User): User
        Returns:
            Success message and status code
        """
        if cls.action_allowed([{"type": "AGGREGATE", "id": news_item_aggregate_id}]) is False:
            return "aggregate_in_use", HTTPStatus.INTERNAL_SERVER_ERROR

        aggregate = cls.find(news_item_aggregate_id)
        for news_item in aggregate.news_items:
            if NewsItem.allowed_with_acl(news_item.id, user, see=False, access=False, modify=True):
                aggregate.news_items.remove(news_item)
                NewsItem.delete_only(news_item)

        NewsItemAggregate.update_status(aggregate.id)

        db.session.commit()

        return "success", HTTPStatus.OK

    @classmethod
    def action_allowed(cls, items: list[dict]) -> bool:
        """Check if action is allowed.

        Args:
            items (list[dict]): Items
        Returns:
            True if action is allowed, False otherwise
        """
        aggregate_ids = set()
        for item in items:
            if item["type"] == "AGGREGATE":
                aggregate_ids.add(item["id"])
            else:
                news_item = NewsItem.find(item["id"])
                aggregate_ids.add(news_item.news_item_aggregate_id)

        return not any(ReportItemNewsItemAggregate.assigned(aggregate_id) for aggregate_id in aggregate_ids)

    @classmethod
    def group_action(cls, data: dict, user: User) -> tuple[str, set[int], HTTPStatus]:
        """Group action.

        Args:
            data (dict): Data
            user (User): User
        Returns:
            Success message, OSINT source IDs and status code
        """
        osint_source_ids = set()

        if data["action"] == "GROUP":
            if not cls.action_allowed(data["items"]):
                return "aggregate_in_use", osint_source_ids, HTTPStatus.INTERNAL_SERVER_ERROR
            cls.group_aggregate(data["items"], user)
        elif data["action"] == "UNGROUP":
            if not cls.action_allowed(data["items"]):
                return "aggregate_in_use", osint_source_ids, HTTPStatus.INTERNAL_SERVER_ERROR
            cls.ungroup_aggregate(data["items"], user)
        else:
            news_items = set()
            processed_aggregates = set()
            for item in data["items"]:
                if item["type"] == "AGGREGATE":
                    aggregate = NewsItemAggregate.find(item["id"])
                    news_items.update(aggregate.news_items)
                    processed_aggregates.add(aggregate)
                else:
                    news_item = NewsItem.find(item["id"])
                    aggregate = NewsItemAggregate.find(news_item.news_item_aggregate_id)
                    news_items.add(news_item)
                    processed_aggregates.add(aggregate)

            news_items = list(news_items)
            for news_item in news_items[:]:
                if not NewsItem.allowed_with_acl(news_item.id, user, see=False, access=False, modify=True):
                    news_items.remove(news_item)

            status_data = {}
            if data["action"] == "LIKE":
                status_data["vote"] = 1
            elif data["action"] == "DISLIKE":
                status_data["vote"] = -1

            all_important = True
            all_read = True
            for news_item in news_items:
                if news_item.important is False:
                    all_important = False
                if news_item.read is False:
                    all_read = False

            for news_item in news_items:
                if "vote" in status_data:
                    news_item.vote(status_data, user.id)
                    osint_source_ids.add(news_item.news_item_data.osint_source_id)

                if data["action"] == "IMPORTANT":
                    news_item.important = not all_important

                if data["action"] == "READ":
                    news_item.read = not all_read

            cls.update_aggregates(processed_aggregates)
            db.session.commit()

        return "success", osint_source_ids, HTTPStatus.OK

    @classmethod
    def group_action_delete(cls, data: dict, user: User) -> tuple[str, HTTPStatus]:
        """Group action delete.

        Args:
            data (dict): Data
            user (User): User
        Returns:
            Success message and status code
        """
        if cls.action_allowed(data["items"]):
            processed_aggregates = set()
            for item in data["items"]:
                if item["type"] == "AGGREGATE":
                    aggregate = NewsItemAggregate.find(item["id"])
                    for news_item in aggregate.news_items:
                        if NewsItem.allowed_with_acl(news_item.id, user, see=False, access=False, modify=True):
                            aggregate.news_items.remove(news_item)
                            NewsItem.delete_only(news_item)

                    processed_aggregates.add(aggregate)
                else:
                    news_item = NewsItem.find(item["id"])
                    if NewsItem.allowed_with_acl(news_item.id, user, see=False, access=False, modify=True):
                        aggregate = NewsItemAggregate.find(news_item.news_item_aggregate_id)
                        aggregate.news_items.remove(news_item)
                        NewsItem.delete_only(news_item)
                        processed_aggregates.add(aggregate)

            cls.update_aggregates(processed_aggregates)
            db.session.commit()
            return "", HTTPStatus.OK
        return "aggregate_in_use", HTTPStatus.INTERNAL_SERVER_ERROR

    @classmethod
    def group_aggregate(cls, items: list[dict], user: User) -> None:
        """Group aggregate.

        Args:
            items (list[dict]): Items
            user (User): User
        """
        new_aggregate = NewsItemAggregate()
        processed_aggregates = set()
        group_id = None
        for item in items:
            if item["type"] == "AGGREGATE":
                aggregate = NewsItemAggregate.find(item["id"])
                group_id = aggregate.osint_source_group_id
                if new_aggregate.title is None:
                    new_aggregate.title = aggregate.title
                    new_aggregate.description = aggregate.description
                    new_aggregate.created = aggregate.created

                for news_item in aggregate.news_items[:]:
                    if user is None or NewsItem.allowed_with_acl(news_item.id, user, see=False, access=False, modify=True):
                        new_aggregate.news_items.append(news_item)
                        aggregate.news_items.remove(news_item)

                processed_aggregates.add(aggregate)
            else:
                news_item = NewsItem.find(item["id"])
                if user is None or NewsItem.allowed_with_acl(news_item.id, user, see=False, access=False, modify=True):
                    aggregate = NewsItemAggregate.find(news_item.news_item_aggregate_id)
                    group_id = aggregate.osint_source_group_id
                    if new_aggregate.title is None:
                        new_aggregate.title = news_item.news_item_data.title
                        new_aggregate.description = news_item.news_item_data.review
                        new_aggregate.created = news_item.news_item_data.collected
                    new_aggregate.news_items.append(news_item)
                    aggregate.news_items.remove(news_item)
                    processed_aggregates.add(aggregate)

        new_aggregate.osint_source_group_id = group_id
        db.session.add(new_aggregate)
        db.session.commit()

        NewsItemAggregate.update_status(new_aggregate.id)
        NewsItemAggregateSearchIndex.prepare(new_aggregate)

        cls.update_aggregates(processed_aggregates)

        db.session.commit()

    @classmethod
    def ungroup_aggregate(cls, items: list[dict], user: User) -> None:
        """Ungroup aggregate.

        Args:
            items (list[dict]): Items
            user (User): User
        """
        processed_aggregates = set()
        for item in items:
            if item["type"] == "AGGREGATE":
                aggregate = NewsItemAggregate.find(item["id"])
                group_id = aggregate.osint_source_group_id
                for news_item in aggregate.news_items[:]:
                    if NewsItem.allowed_with_acl(news_item.id, user, see=False, access=False, modify=True):
                        aggregate.news_items.remove(news_item)
                        cls.create_single_aggregate(news_item, group_id)

                processed_aggregates.add(aggregate)
            else:
                news_item = NewsItem.find(item["id"])
                if NewsItem.allowed_with_acl(news_item.id, user, see=False, access=False, modify=True):
                    aggregate = NewsItemAggregate.find(news_item.news_item_aggregate_id)
                    group_id = aggregate.osint_source_group_id
                    aggregate.news_items.remove(news_item)
                    processed_aggregates.add(aggregate)
                    cls.create_single_aggregate(news_item, group_id)

        cls.update_aggregates(processed_aggregates)

        db.session.commit()

    @classmethod
    def update_aggregates(cls, aggregates: list[NewsItemAggregate]) -> None:
        """Update aggregates.

        Args:
            aggregates (list[NewsItemAggregate]): Aggregates
        """
        for aggregate in aggregates:
            if len(aggregate.news_items) == 0:
                NewsItemAggregateSearchIndex.remove(aggregate)
                db.session.delete(aggregate)
            else:
                NewsItemAggregateSearchIndex.prepare(aggregate)
                NewsItemAggregate.update_status(aggregate.id)

    @classmethod
    def create_single_aggregate(cls, news_item: NewsItem, group_id: int) -> None:
        """Create single aggregate.

        Args:
            news_item (NewsItem): News item
            group_id (int): Group ID
        """
        new_aggregate = NewsItemAggregate()
        new_aggregate.title = news_item.news_item_data.title
        new_aggregate.description = news_item.news_item_data.review
        new_aggregate.created = news_item.news_item_data.collected
        new_aggregate.news_items.append(news_item)
        new_aggregate.osint_source_group_id = group_id
        db.session.add(new_aggregate)
        db.session.commit()

        NewsItemAggregateSearchIndex.prepare(new_aggregate)
        NewsItemAggregate.update_status(new_aggregate.id)

    @classmethod
    def update_status(cls, aggregate_id: int) -> None:
        """Update status.

        Args:
            aggregate_id (int): Aggregate ID
        """
        aggregate = cls.find(aggregate_id)

        if len(aggregate.news_items) == 0:
            NewsItemAggregateSearchIndex.remove(aggregate)
            db.session.delete(aggregate)
        else:
            aggregate.relevance = 0
            aggregate.read = True
            aggregate.important = False
            aggregate.likes = 0
            aggregate.dislikes = 0
            for news_item in aggregate.news_items:
                aggregate.relevance += news_item.relevance
                aggregate.likes += news_item.likes
                aggregate.dislikes += news_item.dislikes

                if news_item.important is True:
                    aggregate.important = True

                if news_item.read is False:
                    aggregate.read = False

    @classmethod
    def get_news_items_aggregate(cls, source_group_id: int, limit: datetime) -> list[NewsItemAggregate]:
        """Get news items aggregate.

        Args:
            source_group_id (int): Source group ID
            limit (datetime): Limit
        Returns:
            News item aggregates
        """
        limit = datetime.strptime(limit["limit"], "%d.%m.%Y - %H:%M").replace(tzinfo=TZ)
        news_item_aggregates = cls.query.filter(cls.osint_source_group_id == source_group_id).filter(cls.created > limit).all()
        news_item_aggregate_schema = NewsItemAggregateSchema(many=True)
        return news_item_aggregate_schema.dumps(news_item_aggregates)

    @classmethod
    def get_news_items_aggregate_by_source_group(cls, source_group_id: int) -> list[NewsItemAggregate]:
        """Get news items aggregate by source group.

        Args:
            source_group_id (int): Source group ID
        Returns:
            list[NewsItemAggregate]: News item aggregates
        """
        return cls.query.filter(cls.osint_source_group_id == source_group_id).all()


class NewsItemAggregateSearchIndex(db.Model):
    """News item aggregate search index model.

    Attributes:
        id: ID
        data: Data
        news_item_aggregate_id: News item aggregate ID
    """

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String)
    news_item_aggregate_id = db.Column(db.Integer, db.ForeignKey("news_item_aggregate.id"))

    @classmethod
    def remove(cls, aggregate: NewsItemAggregate) -> None:
        """Remove.

        Args:
            aggregate (NewsItemAggregate): Aggregate
        """
        search_index = cls.query.filter_by(news_item_aggregate_id=aggregate.id).first()
        if search_index is not None:
            db.session.delete(search_index)
            db.session.commit()

    @classmethod
    def prepare(cls, aggregate: NewsItemAggregate) -> None:
        """Prepare.

        Args:
            aggregate (NewsItemAggregate): Aggregate
        """
        search_index = cls.query.filter_by(news_item_aggregate_id=aggregate.id).first()
        if search_index is None:
            search_index = NewsItemAggregateSearchIndex()
            search_index.news_item_aggregate_id = aggregate.id
            db.session.add(search_index)

        data = aggregate.title
        data += " " + aggregate.description
        data += " " + aggregate.comments

        for news_item in aggregate.news_items:
            data += " " + news_item.news_item_data.title
            data += " " + news_item.news_item_data.review
            data += " " + strip_html(news_item.news_item_data.content)
            data += " " + news_item.news_item_data.author
            data += " " + news_item.news_item_data.link

            for attribute in news_item.news_item_data.attributes:
                data += " " + attribute.value

        search_index.data = data.lower()
        db.session.commit()


class NewsItemDataNewsItemAttribute(db.Model):
    """News item data news item attribute model.

    Attributes:
        news_item_data_id: News item data ID
        news_item_attribute_id: News item attribute ID
    """

    news_item_data_id = db.Column(db.String, db.ForeignKey("news_item_data.id"), primary_key=True)
    news_item_attribute_id = db.Column(db.Integer, db.ForeignKey("news_item_attribute.id"), primary_key=True)

    @classmethod
    def find(cls, attribute_id: int) -> NewsItemAttribute | None:
        """Find news item attribute data.

        Args:
            attribute_id (int): Attribute ID
        Returns:
            News item attribute
        """
        return cls.query.filter(NewsItemDataNewsItemAttribute.news_item_attribute_id == attribute_id).scalar()


class NewsItemAggregateNewsItemAttribute(db.Model):
    """News item aggregate news item attribute model.

    Attributes:
        news_item_aggregate_id: News item aggregate ID
        news_item_attribute_id: News item attribute ID
    """

    news_item_aggregate_id = db.Column(db.Integer, db.ForeignKey("news_item_aggregate.id"), primary_key=True)
    news_item_attribute_id = db.Column(db.Integer, db.ForeignKey("news_item_attribute.id"), primary_key=True)


class ReportItemNewsItemAggregate(db.Model):
    """Report item news item aggregate model.

    Attributes:
        report_item_id: Report item ID
        news_item_aggregate_id: News item aggregate ID
    """

    report_item_id = db.Column(db.Integer, db.ForeignKey("report_item.id"), primary_key=True)
    news_item_aggregate_id = db.Column(db.Integer, db.ForeignKey("news_item_aggregate.id"), primary_key=True)

    @classmethod
    def assigned(cls, aggregate_id: int) -> bool:
        """Check if assigned.

        Args:
            aggregate_id (int): Aggregate ID
        Returns:
            bool: True if assigned, False otherwise
        """
        return db.session.query(db.exists().where(ReportItemNewsItemAggregate.news_item_aggregate_id == aggregate_id)).scalar()

    @classmethod
    def count(cls, aggregate_id: int) -> int:
        """Count.

        Args:
            aggregate_id (int): Aggregate ID
        Returns:
            int: Count
        """
        return cls.query.filter_by(news_item_aggregate_id=aggregate_id).count()

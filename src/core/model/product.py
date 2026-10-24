"""Product model."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from model.product import Product
    from model.user import User

from datetime import datetime, timedelta

import sqlalchemy
from managers import content_language, translation_status
from managers.db_manager import db
from managers.link_references import normalize_links
from marshmallow import fields, post_load
from model.acl_entry import ACLEntry
from model.public_web import PublicWeb
from model.report_item import ReportItem
from model.report_item_type import ReportItemType
from model.setting import Setting
from model.state import (
    StateDefinition,
    StateEntityTypeEnum,
    StateEnum,
    StateManager,
)
from model.tag import Tag, product_tag, set_item_tags
from model.translation import ORIGIN_AI, ORIGIN_MANUAL, PRODUCT_FIELDS, ProductTranslation, sql_source_hash
from shared.common import TZ
from shared.log_manager import logger
from shared.schema.acl_entry import ItemType
from shared.schema.product import ProductPresentationSchema, ProductSchemaBase
from shared.schema.report_item import ReportItemIdSchema
from sqlalchemy import and_, func, or_, orm
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql.expression import cast


class NewProductSchema(ProductSchemaBase):
    """New product schema.

    Attributes:
        report_items: List of report items
    """

    report_items = fields.Nested(ReportItemIdSchema, many=True)
    # Translated titles, {language: {"title": ..., "origin": "ai" | "manual"}}; saved with the product.
    translations = fields.Dict(load_default=None, allow_none=True)

    @post_load
    def make(self, data: dict, **kwargs) -> Product:  # noqa: ARG002, ANN003
        """Create a new product.

        Args:
            data: Product data
            **kwargs: Additional keyword arguments from marshmallow

        Returns:
            Product: New product
        """
        return Product(**data)


class Product(db.Model):
    """Product model.

    Attributes:
        id: Product id
        title: Product title
        description: Product description
        created: Product creation date
        product_type_id: Product type id
        product_type: Product type
        user_id: User id
        user: User
        report_items: List of report items
        links: The product's own sources ([{"key", "url"}]) in citation order; the description
            cites them by key (see managers.link_references)
        language: The language the product is written in (ISO 639-1); None while not set
        translation_rows: Its title and description translated into other languages
    """

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())
    # JSONB, not JSON: product queries use SELECT DISTINCT, and Postgres has no equality for json.
    links = db.Column(JSONB, nullable=False, default=list, server_default=sqlalchemy.text("'[]'"))

    language = db.Column(db.String(8), nullable=True)

    created = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now)

    product_type_id = db.Column(db.Integer, db.ForeignKey("product_type.id"))
    product_type = db.relationship("ProductType")

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", foreign_keys=[user_id])
    updated_by = db.Column(db.String)

    state_id = db.Column(db.Integer, db.ForeignKey("state.id"), nullable=True)
    state = db.relationship(StateDefinition, lazy="select")  # must be "select" to avoid join issues in get()

    report_items = db.relationship("ReportItem", secondary="product_report_item")
    public_webs = db.relationship(PublicWeb, secondary="product_public_web")

    translation_rows = db.relationship(
        ProductTranslation,
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    # The admin tags people put on it; the built-in ones are worked out (see translation_status).
    tags = db.relationship(Tag, secondary=product_tag, viewonly=True, lazy="selectin")

    def __init__(
        self,
        id: int,
        title: str,
        description: str,
        product_type_id: int,
        state_id: int,
        report_items: list[ReportItem],
        public_web_ids: list[int] | None = None,
        links: list[dict] | None = None,
        language: str | None = None,
        translations: dict | None = None,
    ) -> None:
        """Initialize a product.

        Raises:
            ValueError: If the language is not an ISO 639-1 code.
        """
        if id != -1:
            self.id = id
        else:
            self.id = None

        self.title = title
        self.description = description
        self.links = normalize_links(links)
        self.language = content_language.clean_language(language)
        # Applied by add_product / update_product, which know who wrote them.
        self.submitted_translations = translations
        self.product_type_id = product_type_id
        self.state_id = state_id
        self.subtitle = ""
        self.tag = ""

        self.report_items = []
        for report_item in report_items:
            self.report_items.append(ReportItem.find(report_item.id))

        self.public_webs = []
        if public_web_ids:
            for web_id in public_web_ids:
                web = PublicWeb.find(web_id)
                if web:
                    self.public_webs.append(web)

    @orm.reconstructor
    def reconstruct(self) -> None:
        """Reconstruct a product."""
        self.subtitle = self.description
        self.tag = "mdi-file-pdf-outline"
        self.submitted_translations = None

    @property
    def translations(self) -> dict[str, dict]:
        """Translated title and description for the edit form.

        Returns:
            dict[str, dict]: ``{language: {field: state}}``, each state holding value, origin,
                version, outdated, user and last_updated.
        """
        translations: dict[str, dict] = {}
        for row in self.translation_rows:
            translations.setdefault(row.language, {})[row.field] = row.to_dict(getattr(self, row.field, None))
        return translations

    @property
    def tag_ids(self) -> list[int]:
        """The ids of the admin tags on the product."""
        return [tag.id for tag in self.tags]

    @property
    def translation_status(self) -> dict[str, str]:
        """Its title's translation status per language, as built-in tag keys (see managers/translation_status.py)."""
        return translation_status.product_status(self)

    @property
    def title_translations(self) -> dict[str, dict[str, str]]:
        """Translated titles per language, for lists that show the GUI's language.

        Returns:
            dict[str, dict[str, str]]: ``{language: {"title": ...}}``.
        """
        return {row.language: {"title": row.value} for row in self.translation_rows if row.field == "title" and row.value}

    def apply_translations(self, translations: dict | None, user_id: int | None) -> None:
        """Store the submitted translations; a language or field left out or emptied is removed.

        Args:
            translations (dict | None): ``{language: {field: {"value": ..., "origin": ...}}}`` for
                the fields in PRODUCT_FIELDS; None keeps them.
            user_id (int | None): Who saves them.

        Raises:
            ValueError: If a language is not an ISO 639-1 code or is the product's own.
        """
        if translations is None:
            return
        if not isinstance(translations, dict):
            msg = "Product translations must map languages to texts"
            raise ValueError(msg)  # noqa: TRY004 - callers report ValueError as a bad request
        wanted: dict[tuple[str, str], tuple[str, str]] = {}
        for code, entry in translations.items():
            language = content_language.clean_language(code)
            texts = {field: text for field, text in (entry.items() if isinstance(entry, dict) else ()) if field in PRODUCT_FIELDS}
            for field, text in texts.items():
                value = text.get("value") if isinstance(text, dict) else None
                if language is None or not isinstance(value, str) or not value.strip():
                    continue
                if language == self.language:
                    msg = f"The product is written in {content_language.language_name(language)}; it cannot also be translated into it"
                    raise ValueError(msg)
                origin = ORIGIN_AI if text.get("origin") == ORIGIN_AI else ORIGIN_MANUAL
                wanted[language, field] = (value.strip(), origin)

        for row in list(self.translation_rows):
            if (row.language, row.field) not in wanted:
                self.translation_rows.remove(row)
        for (language, field), (value, origin) in wanted.items():
            row = next((row for row in self.translation_rows if row.language == language and row.field == field), None)
            if row is None:
                row = ProductTranslation(language=language, field=field, value="", version=0)
                self.translation_rows.append(row)
            # An unchanged text keeps its source fingerprint, so it still shows as outdated.
            if row.value != value or row.origin != origin or not row.version:
                row.write(value, getattr(self, field), origin, user_id)

    @classmethod
    def count_by_states(cls) -> dict:
        """Count products by their states.

        Returns:
            dict: Dictionary with state names as keys and counts as values
        """
        try:
            state_counts = {}
            result = (
                db.session.query(
                    cls.state_id,
                    db.func.count(cls.id).label("count"),
                    StateDefinition.display_name,
                    StateDefinition.color,
                    StateDefinition.icon,
                )
                .outerjoin(StateDefinition, StateDefinition.id == cls.state_id)
                .group_by(
                    cls.state_id,
                    StateDefinition.display_name,
                    StateDefinition.color,
                    StateDefinition.icon,
                )
                .order_by(db.asc(func.count(cls.id)))
                .all()
            )
            for _state_id, count, display_name, color, icon in result:
                disp = "no_state" if display_name is None else display_name
                col = "#9E9E9E" if color is None else color
                ico = "mdi-help" if icon is None else icon

                state_counts[disp] = {
                    "count": count,
                    "display_name": disp,
                    "color": col,
                    "icon": ico,
                }
            return state_counts

        except Exception as error:
            # Fallback if state system not available
            logger.exception(f"Error counting products by states: {error}")
            return {}

    @classmethod
    def find(cls, product_id: int) -> Product:
        """Find a product.

        Args:
            product_id: Product id
        Returns:
            Product: Product
        """
        return db.session.get(cls, product_id)

    @classmethod
    def get_detail_json(cls, product_id: int) -> dict:
        """Get product detail.

        Args:
            product_id: Product id
        Returns:
            dict: Product detail
        """
        product = db.session.get(cls, product_id)
        if product:
            product.public_web_ids = [web.id for web in product.public_webs]
            # get_json() marks every report item of a product the user may see as
            # accessible; the GUI's report cards only open the detail dialog when
            # card.access is true, so the detail payload must carry the same flags.
            for report_item in product.report_items:
                report_item.see = True
                report_item.access = True
                report_item.modify = True
        products_schema = ProductPresentationSchema()
        return products_schema.dump(product)

    @classmethod
    def get(cls, filter: dict, offset: int, limit: int, user: User) -> tuple[list, int]:
        """Get products.

        Args:
            filter: Filter
            offset: Offset
            limit: Limit
            user: User
        Returns:
            list: List of products
            int: Number of products
        """
        query = (
            db.session.query(
                Product,
                func.count().filter(ACLEntry.id > 0).label("acls"),
                func.count().filter(ACLEntry.access.is_(True)).label("access"),
                func.count().filter(ACLEntry.modify.is_(True)).label("modify"),
            )
            .distinct()
            .group_by(Product.id)
        )
        query = query.outerjoin(
            ACLEntry,
            and_(
                cast(Product.product_type_id, sqlalchemy.String) == ACLEntry.item_id,
                ACLEntry.item_type == ItemType.PRODUCT_TYPE,
            ),
        )
        query = ACLEntry.apply_query(query, user, see=True, access=False, modify=False)

        if "search" in filter and filter["search"] != "":
            search_string = "%" + filter["search"] + "%"
            query = query.filter(
                or_(
                    Product.title.ilike(search_string),
                    Product.description.ilike(search_string),
                    # A product is found by its title in any language.
                    sqlalchemy.exists().where(
                        and_(ProductTranslation.product_id == Product.id, ProductTranslation.value.ilike(search_string)),
                    ),
                ),
            )

        if "published" in filter:
            published_state = StateDefinition.get_by_name(StateEnum.PUBLISHED.value)
            if published_state:
                if filter["published"].lower() == "true":
                    query = query.filter(Product.state_id == published_state.id)
                else:
                    query = query.filter(or_(Product.state_id != published_state.id, Product.state_id.is_(None)))

        if "range" in filter:
            date_limit = datetime.now(tz=TZ)
            if filter["range"] == "TODAY":
                date_limit = date_limit.replace(hour=0, minute=0, second=0, microsecond=0)

            if filter["range"] == "WEEK":
                date_limit = date_limit.replace(day=date_limit.day - date_limit.weekday(), hour=0, minute=0, second=0, microsecond=0)

            if filter["range"] == "MONTH":
                date_limit = date_limit.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            if filter["range"] == "LAST_7_DAYS":
                date_limit = date_limit - timedelta(days=7)

            if filter["range"] == "LAST_31_DAYS":
                date_limit = date_limit - timedelta(days=31)

            if filter["range"] == "DATE":
                date_limit = datetime.fromisoformat(filter["date_from"])
                date_to = datetime.fromisoformat(filter["date_to"])
                query = query.filter(Product.created <= date_to)

            query = query.filter(Product.created >= date_limit)

        query = cls._filter_tags_and_translation(query, filter)

        if "sort" in filter:
            if filter["sort"] == "DATE_DESC":
                query = query.order_by(db.desc(Product.created))

            elif filter["sort"] == "DATE_ASC":
                query = query.order_by(db.asc(Product.created))

        return query.offset(offset).limit(limit).all(), query.count()

    @classmethod
    def _filter_tags_and_translation(cls, query: orm.Query, filter: dict) -> orm.Query:
        """Narrow the list to products with any of ``filter["tags"]``, and by their title's translation status.

        ``filter["translation"]`` is ``needs`` or ``unreviewed`` (with ``translation_language``),
        or ``not_set`` for products whose language is not set.
        """
        tag_ids = filter.get("tags")
        if tag_ids:
            query = query.filter(sqlalchemy.exists().where(product_tag.c.product_id == Product.id, product_tag.c.tag_id.in_(tag_ids)))
        kind = filter.get("translation")
        if kind == "not_set":
            return query.filter(Product.language.is_(None))
        language = filter.get("translation_language")
        if kind in ("needs", "unreviewed") and language:
            query = query.filter(cls.translation_condition(language, needs=kind == "needs"))
        return query

    @staticmethod
    def translation_condition(language: str, *, needs: bool) -> sqlalchemy.ColumnElement[bool]:
        """SQL for a product that one of its reports' types offers in ``language`` and whose texts ...

        - with ``needs``: have no current translation into it (missing or outdated): its title, or
          its description when it has one;
        - otherwise: have a current translation into it that AI made and nobody has reviewed since.

        Args:
            language (str): ISO 639-1 code.
            needs (bool): Which of the two.

        Returns:
            The condition.
        """
        link = orm.aliased(ProductReportItem)
        report = orm.aliased(ReportItem)
        report_type = orm.aliased(ReportItemType)
        row = orm.aliased(ProductTranslation)
        offered = and_(
            Product.language.isnot(None),
            Product.language != language,
            sqlalchemy.exists().where(
                link.product_id == Product.id,
                report.id == link.report_item_id,
                report_type.id == report.report_item_type_id,
                report_type.languages.contains([language]),
            ),
        )

        def current(field: str, source: sqlalchemy.ColumnElement) -> list:
            return [
                row.product_id == Product.id,
                row.language == language,
                row.field == field,
                func.coalesce(row.value, "") != "",
                row.source_hash == sql_source_hash(source),
            ]

        if needs:
            untranslated_description = and_(
                func.coalesce(Product.description, "") != "",
                ~sqlalchemy.exists().where(*current("description", Product.description)),
            )
            return and_(offered, or_(~sqlalchemy.exists().where(*current("title", Product.title)), untranslated_description))
        ai_made = [sqlalchemy.exists().where(*current(field, getattr(Product, field)), row.origin == ORIGIN_AI) for field in PRODUCT_FIELDS]
        return and_(offered, or_(*ai_made))

    @classmethod
    def get_json(cls, filter: dict, offset: int, limit: int, user: User) -> dict:
        """Get products.

        Args:
            filter: Filter
            offset: Offset
            limit: Limit
            user: User
        Returns:
            dict: {total_count, items}
        """
        results, count = cls.get(filter, offset, limit, user)
        products = []
        for result in results:
            product = result.Product
            product.see = True
            product.access = result.access > 0 or result.acls == 0
            product.modify = result.modify > 0 or result.acls == 0
            product.report_items_count = len(product.report_items)
            product.public_web_ids = [web.id for web in product.public_webs]
            products.append(product)

            for report_item in product.report_items:
                report_item.see = True
                report_item.access = True
                report_item.modify = True

        products_schema = ProductPresentationSchema(many=True)
        return {"total_count": count, "items": products_schema.dump(products)}

    @classmethod
    def get_published(cls, limit: int, web_id: int | None = None) -> list[Product]:
        """Get the most recently published products, newest first.

        No user/ACL context — intended for trusted node access to the public feed.

        Args:
            limit: Maximum number of products to return.
            web_id: Public-web id to filter for. Products with no selected
                webs are considered global and included for every web.

        Returns:
            list[Product]: Published products ordered by creation date descending.
        """
        published = StateDefinition.get_by_name(StateEnum.PUBLISHED.value)
        if not published:
            return []
        query = cls.query.filter(cls.state_id == published.id)

        if web_id is not None:
            query = (
                query.outerjoin(ProductPublicWeb, ProductPublicWeb.product_id == cls.id)
                .filter(or_(ProductPublicWeb.public_web_id.is_(None), ProductPublicWeb.public_web_id == web_id))
                .distinct()
            )

        return query.order_by(db.desc(cls.created)).limit(limit).all()

    @classmethod
    def _auto_complete_reports_on_publish(cls, product_id: int, new_state_id: int, user: User) -> None:
        """Auto-complete non-FINAL reports when product is published.

        When a product transitions to a FINAL state (e.g., "published"), this method
        automatically marks all non-FINAL reports in that product as FINAL (e.g., "completed").
        This cascades the completion state to mark associated news items as read.

        Args:
            product_id: The product ID being updated
            new_state_id: The new state ID of the product
            user: The user performing the state change

        Returns:
            None
        """
        try:
            # Check if cascade states feature is enabled
            if not StateManager.is_cascade_states_enabled(user):
                return

            # Check if product is transitioning to a FINAL state
            if not StateManager.is_final_state(new_state_id, StateEntityTypeEnum.PRODUCT.value):
                return

            # Get all reports in this product
            product = Product.find(product_id)
            if not product or not product.report_items:
                return

            # Get the FINAL state for REPORT_ITEM
            final_state = StateDefinition.get_final_state(StateEntityTypeEnum.REPORT_ITEM.value)
            if not final_state:
                return

            # Auto-complete all non-FINAL reports
            for report_item in product.report_items:
                # Check if this report is in a non-FINAL state
                if not StateManager.is_final_state(report_item.state_id, StateEntityTypeEnum.REPORT_ITEM.value):
                    # Update the report to FINAL state
                    update_data = {"update": True, "state_id": final_state.id}
                    ReportItem.update_report_item(report_item.id, update_data, user)

        except Exception as error:
            logger.exception(f"Failed to auto-complete reports on product publish: {error}")

    @classmethod
    def _auto_complete_added_reports(
        cls,
        product_state_id: int,
        user: User,
        added_report_item_ids: set[int],
    ) -> None:
        """Auto-complete newly-added non-FINAL reports when the product is already FINAL.

        This closes the gap left by ``_auto_complete_reports_on_publish``, which only
        fires on a product *state change*. When a report is added to a product that
        is *already* in a FINAL state (e.g. already published), the product's state
        does not change, so the existing cascade is skipped. This method completes
        only the newly-added non-FINAL reports, mirroring the publish cascade for
        the add-to-published-product path.

        Args:
            product_id: The product ID being updated
            product_state_id: The current state ID of the product
            user: The user performing the update
            added_report_item_ids: IDs of report items newly attached in this update

        Returns:
            None
        """
        try:
            # Check if cascade states feature is enabled
            if not StateManager.is_cascade_states_enabled(user):
                return

            # Only act when the product is already in a FINAL state.
            if not StateManager.is_final_state(product_state_id, StateEntityTypeEnum.PRODUCT.value):
                return

            if not added_report_item_ids:
                return

            # Get the FINAL state for REPORT_ITEM
            final_state = StateDefinition.get_final_state(StateEntityTypeEnum.REPORT_ITEM.value)
            if not final_state:
                return

            # Auto-complete only newly-added non-FINAL reports.
            for report_item_id in added_report_item_ids:
                report_item = ReportItem.find(report_item_id)
                if not report_item:
                    continue
                if not StateManager.is_final_state(report_item.state_id, StateEntityTypeEnum.REPORT_ITEM.value):
                    update_data = {"update": True, "state_id": final_state.id}
                    ReportItem.update_report_item(report_item.id, update_data, user)

        except Exception as error:
            logger.exception(f"Failed to auto-complete newly-added reports on product update: {error}")

    @classmethod
    def add_product(cls, product_data: dict, user: User) -> Product:
        """Add a product.

        Args:
            product_data: Product data
            user: User
        Returns:
            Product: New product

        Raises:
            ValueError: If ``tag_ids`` names a tag that cannot be put on products.
        """
        tag_ids = Tag.assignable(StateEntityTypeEnum.PRODUCT.value, product_data.get("tag_ids"))
        product_schema = NewProductSchema()
        product = product_schema.load(product_data)

        product.user_id = user.id
        product.updated_by = user.name
        if product.language is None:
            product.language = cls._author_language(user)
        product.apply_translations(product.submitted_translations, user.id)
        db.session.add(product)
        if tag_ids:
            db.session.flush()
            set_item_tags(StateEntityTypeEnum.PRODUCT.value, product.id, tag_ids, user.id)
        db.session.commit()

        # A product can be created straight in a FINAL state (e.g. published) with its reports
        # attached; those reports are completed just as if they had been added to it later.
        if user and product.report_items:
            cls._auto_complete_added_reports(product.state_id, user, {report_item.id for report_item in product.report_items})

        return product

    @classmethod
    def update_product(cls, product_id: int, product_data: dict, user: User) -> None:
        """Update a product.

        Args:
            product_id: Product id
            product_data: Product data; ``tag_ids`` left out keeps the product's tags
            user: User of who is updating

        Raises:
            ValueError: If ``tag_ids`` names a tag that cannot be put on products, or the
                language is one the product is already translated into.
        """
        # Left out, the tags stay as they are.
        tag_ids = Tag.assignable(StateEntityTypeEnum.PRODUCT.value, product_data["tag_ids"]) if "tag_ids" in product_data else None
        product_schema = NewProductSchema()
        product = product_schema.load(product_data)

        original_product = Product.find(product_id)
        old_state_id = original_product.state_id
        # Capture existing report-item ids before reassignment so the cascade
        # can target only newly-added reports (Option B: a report added to an
        # already-published product should be auto-completed too).
        existing_report_item_ids = {ri.id for ri in original_product.report_items} if original_product.report_items else set()
        original_product.title = product.title
        original_product.description = product.description
        if product.language is not None and product.language != original_product.language:
            translated = {row.language for row in original_product.translation_rows}
            if product.submitted_translations is None and product.language in translated:
                msg = f"The product is already translated into {content_language.language_name(product.language)}"
                raise ValueError(msg)
            original_product.language = product.language
        original_product.apply_translations(product.submitted_translations, user.id if user else None)
        original_product.links = product.links
        original_product.product_type_id = product.product_type_id
        original_product.state_id = product.state_id
        original_product.report_items = []
        original_product.report_items.extend(product.report_items)
        original_product.public_webs = []
        original_product.public_webs.extend(product.public_webs)
        original_product.updated_at = datetime.now(TZ)
        original_product.updated_by = user.name
        if tag_ids is not None:
            set_item_tags(StateEntityTypeEnum.PRODUCT.value, product_id, tag_ids, user.id if user else None)

        db.session.commit()

        # Handle cascade state changes for reports:
        #  - When the product's state changed toward FINAL, complete all non-FINAL reports.
        #  - When the product is already in a FINAL state and new reports were added,
        #    complete only those newly-added non-FINAL reports.
        added_report_item_ids = {ri.id for ri in product.report_items} - existing_report_item_ids if product.report_items else set()
        if user and added_report_item_ids:
            cls._auto_complete_added_reports(product.state_id, user, added_report_item_ids)
        if user and old_state_id != product.state_id:
            cls._auto_complete_reports_on_publish(product_id, product.state_id, user)

    @staticmethod
    def _author_language(user: User) -> str | None:
        """The language a new product of ``user`` is written in: their content language setting.

        Args:
            user (User): The author.

        Returns:
            str | None: ISO 639-1 code, or None when the setting holds no valid code.
        """
        try:
            return content_language.clean_language(Setting.get_setting(user, "CONTENT_DEFAULT_LANGUAGE", ""))
        except ValueError:
            return None

    @classmethod
    def delete(cls, id: int) -> None:
        """Delete product by id.

        Args:
            id: Product id
        """
        product = db.session.get(cls, id)
        if product is not None:
            db.session.delete(product)
            db.session.commit()


class ProductReportItem(db.Model):
    """Product report item model.

    Attributes:
        product_id: Product id
        report_item_id: Report item id
    """

    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), primary_key=True)
    report_item_id = db.Column(db.Integer, db.ForeignKey("report_item.id"), primary_key=True)


class ProductPublicWeb(db.Model):
    """Product to PublicWeb mapping for targeted publication."""

    product_id = db.Column(db.Integer, db.ForeignKey("product.id", ondelete="CASCADE"), primary_key=True)
    public_web_id = db.Column(db.Integer, db.ForeignKey("public_web.id", ondelete="CASCADE"), primary_key=True)

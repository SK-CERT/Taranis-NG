"""PublicWebTemplate model: the report templates public-web renders products with.

A template belongs either to a product preset (the page, homepage entry and RSS text of
its products) or to a report item type (one item block on the page, reusable across
product presets). A product or item without a template of its own is rendered with the
built-in templates shipped in ``shared.public_web_templates``; public-web shows a product
whose product preset has no template only when it is a vulnerability report.

A template applies to the webs it lists, or to every web when it lists none. A product
preset or report item type can so have one template for every web and others for chosen
webs, as long as no two of them claim the same web: a web uses the one that lists it, else
the one for every web, else the built-in.

The built-in templates cannot be deleted, but those public-web falls back on can be switched
off (``PublicWebBuiltinTemplate``), so that only custom templates are used.

Templates are checked when they are saved, so a mistake is reported in the form rather
than on the public page: the source must compile against the filters public-web
provides, and a product template must extend one of the built-in bases.
"""

from __future__ import annotations

from datetime import datetime
from http import HTTPStatus

from jinja2 import TemplateSyntaxError, nodes
from jinja2.sandbox import SandboxedEnvironment
from managers.db_manager import db
from model.product_preset import ProductPreset
from model.public_web import PublicWeb
from model.report_item_type import ReportItemType
from shared.common import TZ
from shared.public_web_templates import DEFAULTS, FILTER_NAMES, PRODUCT_BASES, builtin_sources
from shared.schema.public_web_template import PublicWebTemplatePresentationSchema, PublicWebTemplateSchema
from sqlalchemy import or_, orm, true


class TemplateValidationError(ValueError):
    """A template that cannot be saved; the message is meant for the form."""


def _environment() -> SandboxedEnvironment:
    """An environment that knows the names of public-web's filters (their behaviour does not matter here)."""
    environment = SandboxedEnvironment()
    environment.filters.update(dict.fromkeys(FILTER_NAMES, lambda value, *_args, **_kwargs: value))
    return environment


def validate_source(source: str, *, product_template: bool) -> None:
    """Check that a template compiles, and that a product template extends a built-in base.

    Raises:
        TemplateValidationError: With the line number for a syntax error or an unknown filter.
    """
    environment = _environment()
    try:
        tree = environment.parse(source)
        environment.compile(source)
    except TemplateSyntaxError as error:
        line = f" on line {error.lineno}" if error.lineno else ""
        msg = f"Template error{line}: {error.message}"
        raise TemplateValidationError(msg) from error

    if product_template:
        bases = [
            node.template.value
            for node in tree.find_all(nodes.Extends)
            if isinstance(node.template, nodes.Const) and isinstance(node.template.value, str)
        ]
        if not any(base in PRODUCT_BASES for base in bases):
            msg = f'A product template must start with {{% extends "{PRODUCT_BASES[0]}" %}} (or "{PRODUCT_BASES[1]}").'
            raise TemplateValidationError(msg)


def _check_claims(target: str, webs: list[PublicWeb], others: list[PublicWebTemplate]) -> None:
    """Refuse a template whose webs another template of the same target already claims.

    A target has at most one template for every web (none listed), and at most one for each web.

    Raises:
        TemplateValidationError: Naming the other template and the web they both claim.
    """
    mine = {web.id: web for web in webs}
    for other in others:
        theirs = set(other.public_web_ids)
        if not mine and not theirs:
            msg = f"That {target} already has a template for every web: '{other.name}'."
            raise TemplateValidationError(msg)
        shared = sorted(web.name or str(web.id) for web_id, web in mine.items() if web_id in theirs)
        if shared:
            msg = f"That {target} already has a template for {', '.join(shared)}: '{other.name}'."
            raise TemplateValidationError(msg)


class PublicWebTemplateWeb(db.Model):
    """A public web a report template applies to (none listed: every web)."""

    __tablename__ = "public_web_template_web"

    public_web_template_id = db.Column(db.Integer, db.ForeignKey("public_web_template.id", ondelete="CASCADE"), primary_key=True)
    # A web a template is restricted to cannot be deleted: dropping the last one would turn the
    # template into one for every web.
    public_web_id = db.Column(db.Integer, db.ForeignKey("public_web.id"), primary_key=True)


class PublicWebTemplate(db.Model):
    """A report template of the public web, for one product preset or one report item type.

    Attributes:
        id: Unique identifier.
        name: Name shown in the configuration list.
        product_preset_id: The product preset whose products' page this template renders.
        report_item_type_id: The report item type whose block this template renders.
        source: The Jinja source.
        require_tlp_clear: Product templates only; when False, a product with no TLP at
            all may be shown. Any TLP a product does carry must always be public.
        updated_at: When it was last saved.
        updated_by: Who saved it last.
        webs: The webs it applies to; none listed means every web.
    """

    __table_args__ = (
        db.CheckConstraint(
            "(product_preset_id IS NULL) <> (report_item_type_id IS NULL)",
            name="ck_public_web_template_one_target",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False, default="")
    # Not unique: a product preset (or type) may have a template for every web and others for
    # chosen webs; _checked() keeps them from claiming the same web.
    product_preset_id = db.Column(
        db.Integer,
        db.ForeignKey("product_preset.id", ondelete="CASCADE"),
        nullable=True,
    )
    report_item_type_id = db.Column(
        db.Integer,
        db.ForeignKey("report_item_type.id", ondelete="CASCADE"),
        nullable=True,
    )
    source = db.Column(db.Text(), nullable=False, default="")
    require_tlp_clear = db.Column(db.Boolean(), nullable=False, default=True, server_default=true())
    updated_at = db.Column(db.DateTime)
    updated_by = db.Column(db.String())

    product_preset = db.relationship(ProductPreset, viewonly=True)
    report_item_type = db.relationship(ReportItemType, viewonly=True)
    webs = db.relationship(PublicWeb, secondary="public_web_template_web", lazy="selectin")

    def __init__(
        self,
        name: str = "",
        product_preset_id: int | None = None,
        report_item_type_id: int | None = None,
        source: str = "",
        require_tlp_clear: bool = True,
        id: int | None = None,  # noqa: A002, ARG002
    ) -> None:
        """Initialize a template (the id is assigned by the database)."""
        self.id = None
        self.name = name
        self.product_preset_id = product_preset_id
        self.report_item_type_id = report_item_type_id
        self.source = source
        self.require_tlp_clear = require_tlp_clear
        self.target_title = ""

    @property
    def public_web_ids(self) -> list[int]:
        """The ids of the webs it applies to; empty: every web."""
        return sorted(web.id for web in self.webs)

    @property
    def web_names(self) -> list[str]:
        """The names of the webs it applies to, for the configuration list; empty: every web."""
        return sorted(web.name or str(web.id) for web in self.webs)

    @orm.reconstructor
    def reconstruct(self) -> None:
        """Fill the presentation fields."""
        if self.product_preset_id is not None:
            self.target_title = self.product_preset.name if self.product_preset else ""
        else:
            self.target_title = self.report_item_type.title if self.report_item_type else ""
        self.title = self.name
        self.subtitle = self.target_title
        self.tag = "mdi-file-code-outline"

    # -- queries -----------------------------------------------------------

    @classmethod
    def find(cls, template_id: int) -> PublicWebTemplate | None:
        """Get a template by id."""
        return db.session.get(cls, template_id)

    @classmethod
    def get_all(cls) -> list[PublicWebTemplate]:
        """Every template, for public-web nodes."""
        return cls.query.order_by(cls.id).all()

    @classmethod
    def get_all_json(cls, search: str | None = None) -> dict:
        """The templates for the configuration list, and the webs a template can be restricted to."""
        query = cls.query
        if search:
            search_string = f"%{search}%"
            query = query.filter(or_(cls.name.ilike(search_string), cls.source.ilike(search_string)))
        templates = query.order_by(db.asc(cls.name)).all()
        webs = PublicWeb.query.order_by(db.asc(PublicWeb.name), db.asc(PublicWeb.id)).all()
        return {
            "total_count": len(templates),
            "items": PublicWebTemplatePresentationSchema(many=True).dump(templates),
            "public_webs": [{"id": web.id, "name": web.name or str(web.id)} for web in webs],
        }

    @staticmethod
    def node_json(template: PublicWebTemplate) -> dict:
        """What public-web needs of a template."""
        return {
            "id": template.id,
            "name": template.name,
            "product_preset_id": template.product_preset_id,
            "report_item_type_id": template.report_item_type_id,
            "source": template.source,
            "require_tlp_clear": bool(template.require_tlp_clear),
            # Empty: every web.
            "public_web_ids": template.public_web_ids,
        }

    # -- changes -----------------------------------------------------------

    @classmethod
    def _checked(cls, data: dict, template_id: int | None = None) -> tuple[PublicWebTemplate, list[PublicWeb]]:
        """Load submitted data and check it can be saved; returns the template and the webs it lists.

        Raises:
            TemplateValidationError: When the target is missing, a web it lists does not exist,
                another template of the target claims one of its webs, or the source is invalid.
        """
        loaded = PublicWebTemplateSchema().load(data)
        web_ids = list(dict.fromkeys(loaded.pop("public_web_ids", None) or []))
        template = cls(**loaded)
        if (template.product_preset_id is None) == (template.report_item_type_id is None):
            msg = "Choose either a product preset or a report item type for the template."
            raise TemplateValidationError(msg)
        if template.product_preset_id is not None:
            if db.session.get(ProductPreset, template.product_preset_id) is None:
                msg = "The product preset does not exist."
                raise TemplateValidationError(msg)
            others = cls.query.filter(cls.product_preset_id == template.product_preset_id, cls.id != template_id).all()
            target = "product preset"
        else:
            if db.session.get(ReportItemType, template.report_item_type_id) is None:
                msg = "The report item type does not exist."
                raise TemplateValidationError(msg)
            others = cls.query.filter(cls.report_item_type_id == template.report_item_type_id, cls.id != template_id).all()
            target = "report item type"
        webs = []
        for web_id in web_ids:
            web = PublicWeb.find(web_id)
            if web is None:
                msg = f"Public web {web_id} does not exist."
                raise TemplateValidationError(msg)
            webs.append(web)
        _check_claims(target, webs, others)
        validate_source(template.source, product_template=template.product_preset_id is not None)
        if template.report_item_type_id is not None:
            # TLP is decided per product; an item template has no say.
            template.require_tlp_clear = True
        return template, webs

    @classmethod
    def add(cls, data: dict, user_name: str) -> PublicWebTemplate:
        """Create a template.

        Raises:
            TemplateValidationError: When it cannot be saved (see :meth:`_checked`).
        """
        template, webs = cls._checked(data)
        template.webs = webs
        template.updated_at = datetime.now(TZ)
        template.updated_by = user_name
        db.session.add(template)
        db.session.commit()
        return template

    @classmethod
    def update(cls, template_id: int, data: dict, user_name: str) -> PublicWebTemplate | None:
        """Update a template; None when it does not exist.

        Raises:
            TemplateValidationError: When it cannot be saved (see :meth:`_checked`).
        """
        stored = cls.find(template_id)
        if stored is None:
            return None
        template, webs = cls._checked(data, template_id)
        stored.name = template.name
        stored.product_preset_id = template.product_preset_id
        stored.report_item_type_id = template.report_item_type_id
        stored.source = template.source
        stored.require_tlp_clear = template.require_tlp_clear
        stored.webs = webs
        stored.updated_at = datetime.now(TZ)
        stored.updated_by = user_name
        db.session.commit()
        return stored

    @classmethod
    def delete(cls, template_id: int) -> tuple[dict, HTTPStatus]:
        """Delete a template."""
        template = cls.find(template_id)
        if template is None:
            return {"error": "Template not found"}, HTTPStatus.NOT_FOUND
        db.session.delete(template)
        db.session.commit()
        return {"message": "Template deleted"}, HTTPStatus.OK


class PublicWebBuiltinTemplate(db.Model):
    """Whether public-web falls back on a built-in template (``shared.public_web_templates.DEFAULTS``).

    A built-in without a row is on, so a new one is used until someone switches it off. Only the
    built-ins in ``DEFAULTS`` can be switched off; the base layout and the macros cannot.

    Attributes:
        name: The built-in's loader name, ``builtin/<file>``.
        enabled: Whether public-web uses it.
        updated_at: When it was last switched.
        updated_by: Who switched it last.
    """

    __tablename__ = "public_web_builtin_template"

    name = db.Column(db.String(), primary_key=True)
    enabled = db.Column(db.Boolean(), nullable=False, default=True, server_default=true())
    updated_at = db.Column(db.DateTime)
    updated_by = db.Column(db.String())

    @classmethod
    def disabled(cls) -> list[str]:
        """The built-ins switched off, for public-web nodes."""
        names = [row.name for row in cls.query.filter(cls.enabled.is_(False)).all()]
        return sorted(name for name in names if name in DEFAULTS)

    @classmethod
    def get_all_json(cls) -> dict:
        """Every built-in with its source and whether it is on, for the configuration list.

        Returns:
            dict: ``{"items": [{"name", "source", "can_disable", "enabled", "updated_at", "updated_by"}]}``,
            ``name`` being what ``extends`` and ``import`` refer to.
        """
        rows = {row.name: row for row in cls.query.all()}
        items = []
        for name, source in builtin_sources().items():
            row = rows.get(name)
            can_disable = name in DEFAULTS
            items.append(
                {
                    "name": name,
                    "source": source,
                    "can_disable": can_disable,
                    "enabled": not can_disable or row is None or bool(row.enabled),
                    "updated_at": row.updated_at.strftime("%d.%m.%Y - %H:%M") if row is not None and row.updated_at else None,
                    "updated_by": row.updated_by if row is not None else None,
                },
            )
        return {"items": items}

    @classmethod
    def set_enabled(cls, name: str, enabled: bool, user_name: str) -> PublicWebBuiltinTemplate:
        """Switch a built-in on or off.

        Raises:
            TemplateValidationError: When there is no such built-in, or it cannot be switched off.
        """
        if name not in builtin_sources():
            msg = f"There is no built-in template '{name}'."
            raise TemplateValidationError(msg)
        if name not in DEFAULTS:
            msg = f"The built-in template '{name}' cannot be switched off: custom templates build on it."
            raise TemplateValidationError(msg)
        row = db.session.get(cls, name)
        if row is None:
            row = cls(name=name)
            db.session.add(row)
        row.enabled = bool(enabled)
        row.updated_at = datetime.now(TZ)
        row.updated_by = user_name
        db.session.commit()
        return row

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from managers.log_manager import logger

db = SQLAlchemy()
migrate = Migrate()


def initialize(app):
    db.init_app(app)
    migrate.init_app(app, db)
    db.create_all()
    try:
        pre_seed()
    except Exception:
        logger.log_debug_trace("Pre Seed failed")


def pre_seed():
    pre_seed_source_groups()
    logger.log_debug("Source groups seeded")

    pre_seed_roles()
    logger.log_debug("Roles seeded")

    pre_seed_attributes()
    logger.log_debug("Attributes seeded")

    pre_seed_report_items()
    logger.log_debug("Report items seeded")

    pre_seed_wordlists()
    logger.log_debug("Wordlists seeded")

    pre_seed_default_user()
    logger.log_debug("Default users seeded")


def pre_seed_source_groups():
    from model.osint_source import OSINTSourceGroup
    import uuid

    default_group = OSINTSourceGroup(
        str(uuid.uuid4()),
        "Default",
        "Default group for uncategorized OSINT sources",
        True,
        [],
    )

    db.session.add(default_group)
    db.session.commit()


def pre_seed_roles():
    from model.role import Role
    from model.permission import Permission

    default_user_permissions = [
        {"id": "ASSESS_ACCESS"},
        {"id": "ASSESS_CREATE"},
        {"id": "ASSESS_UPDATE"},
        {"id": "ASSESS_DELETE"},
        {"id": "ANALYZE_ACCESS"},
        {"id": "ANALYZE_CREATE"},
        {"id": "ANALYZE_UPDATE"},
        {"id": "ANALYZE_DELETE"},
        {"id": "PUBLISH_ACCESS"},
        {"id": "PUBLISH_CREATE"},
        {"id": "PUBLISH_UPDATE"},
        {"id": "PUBLISH_DELETE"},
        {"id": "PUBLISH_PRODUCT"},
    ]
    admin_permissions = [{"id": perm.id} for perm in Permission.get_all()]

    if not db.session.query(Role).filter_by(name="Admin").first():
        Role.add_new(
            {
                "id": "",
                "name": "Admin",
                "description": "Administrator role",
                "permissions": admin_permissions,
            }
        )
    if not db.session.query(Role).filter_by(name="User").first():
        Role.add_new(
            {
                "id": "",
                "name": "User",
                "description": "Basic user role",
                "permissions": default_user_permissions,
            }
        )


def pre_seed_attributes():
    from model.attribute import Attribute

    base_attr = {
        "id": -1,
        "name": "Text",
        "description": "Simple text box",
        "type": "STRING",
        "default_value": "",
        "validator": "NONE",
        "validator_parameter": "",
        "attribute_enums": [],
        "attribute_enums_total_count": 0,
    }

    if not db.session.query(Attribute).filter_by(name="Text").first():
        attr = {
            **{"name": "Text", "description": "Simple text box", "type": "STRING"},
            **base_attr,
        }
        Attribute.add_attribute(attr)

    if not db.session.query(Attribute).filter_by(name="Text Area").first():
        attr = {
            **{"name": "Text Area", "description": "Simple text area", "type": "TEXT"},
            **base_attr,
        }
        Attribute.add_attribute(attr)

    if not db.session.query(Attribute).filter_by(name="TLP").first():
        attr = {
            **{
                "name": "TLP",
                "description": "Traffic Light Protocol element",
                "type": "TLP",
            },
            **base_attr,
        }
        Attribute.add_attribute(attr)

    if not db.session.query(Attribute).filter_by(name="CPE").first():
        attr = {
            **{
                "name": "CPE",
                "description": "Common Platform Enumeration element",
                "type": "CPE",
            },
            **base_attr,
        }
        Attribute.add_attribute(attr)

    if not db.session.query(Attribute).filter_by(name="CVSS").first():
        attr = {
            **{
                "name": "CVSS",
                "description": "Common Vulnerability Scoring System element",
                "type": "CVSS",
            },
            **base_attr,
        }
        Attribute.add_attribute(attr)

    if not db.session.query(Attribute).filter_by(name="CVE").first():
        attr = {
            **{
                "name": "CVE",
                "description": "Common Vulnerabilities and Exposures element",
                "type": "CVE",
            },
            **base_attr,
        }
        Attribute.add_attribute(attr)

    if not db.session.query(Attribute).filter_by(name="Date").first():
        attr = {
            **{"name": "Date", "description": "Date picker", "type": "DATE"},
            **base_attr,
        }
        Attribute.add_attribute(attr)

    if not db.session.query(Attribute).filter_by(name="Confidentiality").first():
        attr_enum = [
            {"id": 0, "name": "UNRESTRICTED", "description": ""},
            {"id": 1, "name": "CLASSIFIED", "description": ""},
            {"id": 2, "name": "CONFIDENTIAL", "description": ""},
            {"id": 3, "name": "SECRET", "description": ""},
            {"id": 4, "name": "TOP SECRET", "description": ""},
        ]
        attr = {
            **{
                "name": "Confidentiality",
                "description": "Radio box for confidentiality level",
                "type": "RADIO",
                "attribute_enums": attr_enum,
                "attribute_enums_total_count": len(attr_enum),
            },
            **base_attr,
        }
        Attribute.add_attribute(attr)

    if not db.session.query(Attribute).filter_by(name="Impact").first():
        attr_enum = [
            {
                "id": 0,
                "name": "Malicious code execution affecting overall confidentiality, integrity, and availability of the system",
                "description": "",
            },  # noqa
            {"id": 1, "name": "Malicious code execution", "description": ""},
            {"id": 2, "name": "Denial of service", "description": ""},
            {"id": 3, "name": "Privilege escalation", "description": ""},
            {"id": 4, "name": "Information exposure", "description": ""},
            {"id": 5, "name": "Unauthorized access to the system", "description": ""},
            {"id": 6, "name": "Unauthorized change in system", "description": ""},
        ]
        attr = {
            **{
                "name": "Impact",
                "description": "Combo box for impact level",
                "type": "ENUM",
                "attribute_enums": attr_enum,
                "attribute_enums_total_count": len(attr_enum),
            },
            **base_attr,
        }
        Attribute.add_attribute(attr)

    if not db.session.query(Attribute).filter_by(name="Additional Data").first():
        attr_enum = [
            {"id": 0, "name": "For Intrusion Detection System", "description": ""},
            {"id": 1, "name": "Disable Correlation", "description": ""},
        ]
        attr = {
            **{
                "name": "Additional Data",
                "description": "Radio box for MISP additional data",
                "type": "RADIO",
                "attribute_enums": attr_enum,
                "attribute_enums_total_count": len(attr_enum),
            },
            **base_attr,
        }
        Attribute.add_attribute(attr)

    if (
        not db.session.query(Attribute)
        .filter_by(name="MISP Event Distribution")
        .first()
    ):
        attr_enum = [
            {"id": 0, "name": "Your organisation only", "description": ""},
            {"id": 1, "name": "This community only", "description": ""},
            {"id": 2, "name": "Connected communities", "description": ""},
            {"id": 3, "name": "All communities", "description": ""},
        ]
        attr = {
            **{
                "name": "MISP Event Distribution",
                "description": "Combo box for MISP event distribution",
                "type": "ENUM",
                "attribute_enums": attr_enum,
                "attribute_enums_total_count": len(attr_enum),
            },
            **base_attr,
        }
        Attribute.add_attribute(attr)

    if (
        not db.session.query(Attribute)
        .filter_by(name="MISP Event Threat Level")
        .first()
    ):
        attr_enum = [
            {"id": 0, "name": "High", "description": ""},
            {"id": 1, "name": "Medium", "description": ""},
            {"id": 2, "name": "Low", "description": ""},
            {"id": 3, "name": "Undefined", "description": ""},
        ]
        attr = {
            **{
                "name": "MISP Event Threat Level",
                "description": "Combo box for MISP event threat level",
                "type": "ENUM",
                "attribute_enums": attr_enum,
                "attribute_enums_total_count": len(attr_enum),
            },
            **base_attr,
        }
        Attribute.add_attribute(attr)

    if not db.session.query(Attribute).filter_by(name="MISP Event Analysis").first():
        attr_enum = [
            {"id": 0, "name": "Initial", "description": ""},
            {"id": 1, "name": "Ongoing", "description": ""},
            {"id": 2, "name": "Completed", "description": ""},
        ]
        attr = {
            **{
                "name": "MISP Event Analysis",
                "description": "Combo box for MISP event analysis",
                "type": "ENUM",
                "attribute_enums": attr_enum,
                "attribute_enums_total_count": len(attr_enum),
            },
            **base_attr,
        }
        Attribute.add_attribute(attr)

    if (
        not db.session.query(Attribute)
        .filter_by(name="MISP Attribute Category")
        .first()
    ):
        attr_enum = [
            {"id": 0, "name": "Internal reference", "description": ""},
            {"id": 1, "name": "Targeting data", "description": ""},
            {"id": 2, "name": "Antivirus detection", "description": ""},
            {"id": 3, "name": "Payload delivery", "description": ""},
            {"id": 4, "name": "Artifacts dropped", "description": ""},
            {"id": 5, "name": "Payload installation", "description": ""},
            {"id": 6, "name": "Persistence mechanism", "description": ""},
            {"id": 7, "name": "Network activity", "description": ""},
            {"id": 8, "name": "Payload type", "description": ""},
            {"id": 9, "name": "Attribution", "description": ""},
            {"id": 10, "name": "External analysis", "description": ""},
            {"id": 11, "name": "Financial fraud", "description": ""},
            {"id": 12, "name": "Support Tool", "description": ""},
            {"id": 13, "name": "Social network", "description": ""},
            {"id": 14, "name": "Person", "description": ""},
            {"id": 15, "name": "Other", "description": ""},
        ]
        attr = {
            **{
                "name": "MISP Attribute Category",
                "description": "Combo box for MISP attribute category",
                "type": "ENUM",
                "attribute_enums": attr_enum,
                "attribute_enums_total_count": len(attr_enum),
            },
            **base_attr,
        }
        Attribute.add_attribute(attr)

    if not db.session.query(Attribute).filter_by(name="MISP Attribute Type").first():
        attr_enum = [
            {"id": 0, "name": "md5", "description": ""},
            {"id": 1, "name": "sha1", "description": ""},
            {"id": 2, "name": "sha256", "description": ""},
            {"id": 3, "name": "filename", "description": ""},
            {"id": 4, "name": "pbd", "description": ""},
            {"id": 5, "name": "filename|md5", "description": ""},
            {"id": 6, "name": "filename|sha1", "description": ""},
            {"id": 7, "name": "filename|sha256", "description": ""},
            {"id": 8, "name": "ip-src", "description": ""},
            {"id": 9, "name": "ip-dst", "description": ""},
            {"id": 10, "name": "hostname", "description": ""},
            {"id": 11, "name": "domain", "description": ""},
            {"id": 12, "name": "domain|ip", "description": ""},
            {"id": 13, "name": "email-src", "description": ""},
            {"id": 14, "name": "eppn", "description": ""},
            {"id": 15, "name": "email-dst", "description": ""},
            {"id": 16, "name": "email-subject", "description": ""},
            {"id": 17, "name": "email-attachment", "description": ""},
            {"id": 18, "name": "email-body", "description": ""},
            {"id": 19, "name": "float", "description": ""},
            {"id": 20, "name": "url", "description": ""},
            {"id": 21, "name": "http-method", "description": ""},
            {"id": 22, "name": "user-agent", "description": ""},
            {"id": 23, "name": "ja3-fingerprint-md5", "description": ""},
            {"id": 24, "name": "hassh-md5", "description": ""},
            {"id": 25, "name": "hasshserver-md5", "description": ""},
            {"id": 26, "name": "reg-key", "description": ""},
            {"id": 27, "name": "regkey|value", "description": ""},
            {"id": 28, "name": "AS", "description": ""},
            {"id": 29, "name": "snort", "description": ""},
            {"id": 30, "name": "bro", "description": ""},
            {"id": 31, "name": "zeek", "description": ""},
            {"id": 32, "name": "community-id", "description": ""},
            {"id": 33, "name": "pattern-in-traffic", "description": ""},
            {"id": 34, "name": "pattern-in-memory", "description": ""},
            {"id": 35, "name": "yara", "description": ""},
            {"id": 36, "name": "stix2-pattern", "description": ""},
            {"id": 37, "name": "sigma", "description": ""},
            {"id": 38, "name": "gene", "description": ""},
            {"id": 39, "name": "kusto-query", "description": ""},
            {"id": 40, "name": "mime-type", "description": ""},
            {"id": 41, "name": "identity-card-number", "description": ""},
            {"id": 42, "name": "cookie", "description": ""},
            {"id": 43, "name": "vulnerability", "description": ""},
            {"id": 44, "name": "weakness", "description": ""},
            {"id": 45, "name": "link", "description": ""},
            {"id": 46, "name": "comment", "description": ""},
            {"id": 47, "name": "text", "description": ""},
            {"id": 48, "name": "hex", "description": ""},
            {"id": 49, "name": "other", "description": ""},
            {"id": 50, "name": "named pipe", "description": ""},
            {"id": 51, "name": "mutex", "description": ""},
            {"id": 52, "name": "target-user", "description": ""},
            {"id": 53, "name": "target-email", "description": ""},
            {"id": 54, "name": "target-machine", "description": ""},
            {"id": 55, "name": "target-org", "description": ""},
            {"id": 56, "name": "target-location", "description": ""},
            {"id": 57, "name": "target-external", "description": ""},
            {"id": 58, "name": "btc", "description": ""},
            {"id": 59, "name": "dash", "description": ""},
            {"id": 60, "name": "xmr", "description": ""},
            {"id": 61, "name": "iban", "description": ""},
            {"id": 62, "name": "bic", "description": ""},
            {"id": 63, "name": "bank-account-nr", "description": ""},
            {"id": 64, "name": "aba-rtn", "description": ""},
            {"id": 65, "name": "bin", "description": ""},
            {"id": 66, "name": "cc-number", "description": ""},
            {"id": 67, "name": "prtn", "description": ""},
            {"id": 68, "name": "phone-number", "description": ""},
            {"id": 69, "name": "threat-actor", "description": ""},
            {"id": 70, "name": "campaign-name", "description": ""},
            {"id": 71, "name": "campaign-id", "description": ""},
            {"id": 72, "name": "malware-type", "description": ""},
            {"id": 73, "name": "uri", "description": ""},
            {"id": 74, "name": "authentihash", "description": ""},
            {"id": 75, "name": "ssdeep", "description": ""},
            {"id": 76, "name": "implash", "description": ""},
            {"id": 77, "name": "pahash", "description": ""},
            {"id": 78, "name": "impfuzzy", "description": ""},
            {"id": 79, "name": "sha224", "description": ""},
            {"id": 80, "name": "sha384", "description": ""},
            {"id": 81, "name": "sha512", "description": ""},
            {"id": 82, "name": "sha512/224", "description": ""},
            {"id": 83, "name": "sha512/256", "description": ""},
            {"id": 84, "name": "tlsh", "description": ""},
            {"id": 85, "name": "cdhash", "description": ""},
            {"id": 86, "name": "filename|authentihash", "description": ""},
            {"id": 87, "name": "filename|ssdeep", "description": ""},
            {"id": 88, "name": "filename|implash", "description": ""},
            {"id": 89, "name": "filename|impfuzzy", "description": ""},
            {"id": 90, "name": "filename|pehash", "description": ""},
            {"id": 91, "name": "filename|sha224", "description": ""},
            {"id": 92, "name": "filename|sha384", "description": ""},
            {"id": 93, "name": "filename|sha512", "description": ""},
            {"id": 94, "name": "filename|sha512/224", "description": ""},
            {"id": 95, "name": "filename|sha512/256", "description": ""},
            {"id": 96, "name": "filename|tlsh", "description": ""},
            {"id": 97, "name": "windows-scheduled-task", "description": ""},
            {"id": 98, "name": "windows-service-name", "description": ""},
            {"id": 99, "name": "windows-service-displayname", "description": ""},
            {"id": 100, "name": "whois-registrant-email", "description": ""},
            {"id": 101, "name": "whois-registrant-phone", "description": ""},
            {"id": 102, "name": "whois-registrant-name", "description": ""},
            {"id": 103, "name": "whois-registrant-org", "description": ""},
            {"id": 104, "name": "whois-registrar", "description": ""},
            {"id": 105, "name": "whois-creation-date", "description": ""},
            {"id": 106, "name": "x509-fingerprint-sha1", "description": ""},
            {"id": 107, "name": "x509-fingerprint-md5", "description": ""},
            {"id": 108, "name": "x509-fingerprint-sha256", "description": ""},
            {"id": 109, "name": "dns-soa-email", "description": ""},
            {"id": 110, "name": "size-in-bytes", "description": ""},
            {"id": 111, "name": "counter", "description": ""},
            {"id": 112, "name": "datetime", "description": ""},
            {"id": 113, "name": "cpe", "description": ""},
            {"id": 114, "name": "port", "description": ""},
            {"id": 115, "name": "ip-dist|port", "description": ""},
            {"id": 116, "name": "ip-src|port", "description": ""},
            {"id": 117, "name": "hostname|port", "description": ""},
            {"id": 118, "name": "mac-address", "description": ""},
            {"id": 119, "name": "mac-eui-64", "description": ""},
            {"id": 120, "name": "email-dst-display-name", "description": ""},
            {"id": 121, "name": "email-src-display-name", "description": ""},
            {"id": 122, "name": "email-header", "description": ""},
            {"id": 123, "name": "email-reply-to", "description": ""},
            {"id": 124, "name": "email-x-mailer", "description": ""},
            {"id": 125, "name": "email-mime-boundary", "description": ""},
            {"id": 126, "name": "email-thread-index", "description": ""},
            {"id": 127, "name": "email-message-id", "description": ""},
            {"id": 128, "name": "github-username", "description": ""},
            {"id": 129, "name": "github-repository", "description": ""},
            {"id": 130, "name": "githzb-organisation", "description": ""},
            {"id": 131, "name": "jabber-id", "description": ""},
            {"id": 132, "name": "twitter-id", "description": ""},
            {"id": 133, "name": "first-name", "description": ""},
            {"id": 134, "name": "middle-name", "description": ""},
            {"id": 135, "name": "last-name", "description": ""},
            {"id": 136, "name": "date-of-birth", "description": ""},
            {"id": 137, "name": "gender", "description": ""},
            {"id": 138, "name": "passport-number", "description": ""},
            {"id": 139, "name": "passport-country", "description": ""},
            {"id": 140, "name": "passport-expiration", "description": ""},
            {"id": 141, "name": "redress-number", "description": ""},
            {"id": 142, "name": "nationality", "description": ""},
            {"id": 143, "name": "visa-number", "description": ""},
            {"id": 144, "name": "issue-date-of-the-visa", "description": ""},
            {"id": 145, "name": "primary-residence", "description": ""},
            {"id": 146, "name": "country-of-residence", "description": ""},
            {"id": 147, "name": "special-service-request", "description": ""},
            {"id": 148, "name": "frequent-flyer-number", "description": ""},
            {"id": 149, "name": "travel-details", "description": ""},
            {"id": 150, "name": "payments-details", "description": ""},
            {
                "id": 151,
                "name": "place-port-of-original-embarkation",
                "description": "",
            },
            {
                "id": 152,
                "name": "passenger-name-record-locator-number",
                "description": "",
            },
            {"id": 153, "name": "mobile-application-id", "description": ""},
            {"id": 154, "name": "chrome-extension-id", "description": ""},
            {"id": 155, "name": "cortex", "description": ""},
            {"id": 156, "name": "boolean", "description": ""},
            {"id": 157, "name": "anonymised", "description": ""},
        ]
        attr = {
            **{
                "name": "MISP Attribute Type",
                "description": "Combo box for MISP attribute type",
                "type": "ENUM",
                "attribute_enums": attr_enum,
                "attribute_enums_total_count": len(attr_enum),
            },
            **base_attr,
        }
        Attribute.add_attribute(attr)

    if (
        not db.session.query(Attribute)
        .filter_by(name="MISP Attribute Distribution")
        .first()
    ):
        attr_enum = [
            {"id": 0, "name": "Your organisation only", "description": ""},
            {"id": 1, "name": "This community only", "description": ""},
            {"id": 2, "name": "Connected communities", "description": ""},
            {"id": 3, "name": "All communities", "description": ""},
            {"id": 4, "name": "Inherit event", "description": ""},
        ]
        attr = {
            **{
                "name": "MISP Attribute Distribution",
                "description": "Combo box for MISP attribute type",
                "type": "ENUM",
                "attribute_enums": attr_enum,
                "attribute_enums_total_count": len(attr_enum),
            },
            **base_attr,
        }
        Attribute.add_attribute(attr)


def pre_seed_report_items():
    from model.report_item_type import (
        ReportItemType,
        AttributeGroupItem,
        AttributeGroup,
    )
    from model.attribute import Attribute

    if (
        not db.session.query(ReportItemType)
        .filter_by(title="Vulnerability Report")
        .first()
    ):
        report_item_type = ReportItemType(
            None, "Vulnerability Report", "Basic report type", []
        )
        db.session.add(report_item_type)
        db.session.commit()
        report_item_type_id = (
            db.session.query(ReportItemType)
            .filter_by(title="Vulnerability Report")
            .first()
            .id
        )

        group1 = AttributeGroup(
            None, "Vulnerability", "", 0, "", 0, [report_item_type_id]
        )
        group2 = AttributeGroup(
            None, "Identify and Act", "", 0, "", 0, [report_item_type_id]
        )
        group3 = AttributeGroup(None, "Resources", "", 0, "", 0, [report_item_type_id])
        db.session.add(group1)
        db.session.add(group2)
        db.session.add(group3)
        db.session.commit()

        db.session.add(
            AttributeGroupItem(
                "CVSS",
                "",
                0,
                1,
                1,
                group1.id,
                db.session.query(Attribute).filter_by(name="CVSS").first().id,
            )
        )
        db.session.add(
            AttributeGroupItem(
                "TLP",
                "",
                1,
                1,
                1,
                group1.id,
                db.session.query(Attribute).filter_by(name="TLP").first().id,
            )
        )
        db.session.add(
            AttributeGroupItem(
                "Confidentiality",
                "",
                2,
                1,
                1,
                group1.id,
                db.session.query(Attribute)
                .filter_by(name="Confidentiality")
                .first()
                .id,
            )
        )
        db.session.add(
            AttributeGroupItem(
                "Description",
                "",
                3,
                1,
                1,
                group1.id,
                db.session.query(Attribute).filter_by(name="Text Area").first().id,
            )
        )
        db.session.add(
            AttributeGroupItem(
                "Exposure Date",
                "",
                4,
                1,
                1,
                group1.id,
                db.session.query(Attribute).filter_by(name="Date").first().id,
            )
        )
        db.session.add(
            AttributeGroupItem(
                "Update Date",
                "",
                5,
                1,
                1,
                group1.id,
                db.session.query(Attribute).filter_by(name="Date").first().id,
            )
        )
        db.session.add(
            AttributeGroupItem(
                "CVE",
                "",
                6,
                0,
                1000,
                group1.id,
                db.session.query(Attribute).filter_by(name="CVE").first().id,
            )
        )
        db.session.add(
            AttributeGroupItem(
                "Impact",
                "",
                7,
                0,
                1000,
                group1.id,
                db.session.query(Attribute).filter_by(name="Impact").first().id,
            )
        )
        db.session.commit()

        db.session.add(
            AttributeGroupItem(
                "Affected systems",
                "",
                0,
                0,
                1000,
                group2.id,
                db.session.query(Attribute).filter_by(name="CPE").first().id,
            )
        )
        db.session.add(
            AttributeGroupItem(
                "IOC",
                "",
                1,
                0,
                1000,
                group2.id,
                db.session.query(Attribute).filter_by(name="Text").first().id,
            )
        )
        db.session.add(
            AttributeGroupItem(
                "Recommendations",
                "",
                2,
                1,
                1,
                group2.id,
                db.session.query(Attribute).filter_by(name="Text Area").first().id,
            )
        )
        db.session.commit()

        db.session.add(
            AttributeGroupItem(
                "Links",
                "",
                0,
                0,
                1000,
                group3.id,
                db.session.query(Attribute).filter_by(name="Text").first().id,
            )
        )
        db.session.commit()

    if not db.session.query(ReportItemType).filter_by(title="MISP Report").first():
        print("Adding default MISP report type.", flush=True)
        report_item_type = ReportItemType(None, "MISP Report", "MISP report type", [])
        db.session.add(report_item_type)
        db.session.commit()

        group4 = AttributeGroup(None, "Event", "", None, None, 0, [report_item_type.id])
        group5 = AttributeGroup(
            None, "Attribute", "", None, None, 0, [report_item_type.id]
        )
        db.session.add(group4)
        db.session.add(group5)
        db.session.commit()

        db.session.add(
            AttributeGroupItem(
                "Event distribution",
                "",
                0,
                1,
                1,
                group4.id,
                db.session.query(Attribute).filter_by(name="Text").first().id,
            )
        )
        db.session.add(
            AttributeGroupItem(
                "Event threat level",
                "",
                1,
                1,
                1,
                group4.id,
                db.session.query(Attribute).filter_by(name="Text").first().id,
            )
        )
        db.session.add(
            AttributeGroupItem(
                "Event analysis",
                "",
                2,
                1,
                1,
                group4.id,
                db.session.query(Attribute).filter_by(name="Text").first().id,
            )
        )
        db.session.add(
            AttributeGroupItem(
                "Event info",
                "",
                2,
                1,
                1,
                group4.id,
                db.session.query(Attribute).filter_by(name="Text").first().id,
            )
        )
        db.session.commit()

        db.session.add(
            AttributeGroupItem(
                "Attribute category",
                "",
                0,
                1,
                1,
                group5.id,
                db.session.query(Attribute).filter_by(name="Text").first().id,
            )
        )
        db.session.add(
            AttributeGroupItem(
                "Attribute type",
                "",
                1,
                1,
                1,
                group5.id,
                db.session.query(Attribute).filter_by(name="Text").first().id,
            )
        )
        db.session.add(
            AttributeGroupItem(
                "Attribute distribution",
                "",
                2,
                1,
                1,
                group5.id,
                db.session.query(Attribute).filter_by(name="Text").first().id,
            )
        )
        db.session.add(
            AttributeGroupItem(
                "Attribute value",
                "",
                3,
                1,
                1,
                group5.id,
                db.session.query(Attribute).filter_by(name="Text Area").first().id,
            )
        )
        db.session.add(
            AttributeGroupItem(
                "Attribute contextual comment",
                "",
                4,
                1,
                1,
                group5.id,
                db.session.query(Attribute).filter_by(name="Text").first().id,
            )
        )
        db.session.add(
            AttributeGroupItem(
                "Attribute additional information",
                "",
                5,
                1,
                1,
                group5.id,
                db.session.query(Attribute)
                .filter_by(name="Additional Data")
                .first()
                .id,
            )
        )
        db.session.add(
            AttributeGroupItem(
                "First seen date",
                "",
                6,
                1,
                1,
                group5.id,
                db.session.query(Attribute).filter_by(name="Date").first().id,
            )
        )
        db.session.add(
            AttributeGroupItem(
                "Last seen date",
                "",
                7,
                1,
                1,
                group5.id,
                db.session.query(Attribute).filter_by(name="Date").first().id,
            )
        )
        db.session.commit()


def pre_seed_wordlists():
    from model.word_list import WordList, WordListCategory

    en_wordlist_category = WordListCategory(
        name="Default EN stop list",
        description="Source: https://www.maxqda.de/hilfe-mx20-dictio/stopp-listen",
        entries=[],
        link="https://raw.githubusercontent.com/SK-CERT/Taranis-NG/main/resources/wordlists/en_complete.csv",
    )
    db.session.add(en_wordlist_category)
    db.session.commit()

    en_wordlist = WordList(
        None,
        "Default EN stop list",
        "English stop-word list packed with the standard Taranis NG installation.",
        [en_wordlist_category],
        True,
    )
    db.session.add(en_wordlist)
    db.session.commit()

    # Slovak

    sk_wordlist_category = WordListCategory(
        name="Default SK stop list",
        description="Source: https://github.com/stopwords-iso/stopwords-sk/blob/master/stopwords-sk.txt",
        entries=[],
        link="https://raw.githubusercontent.com/SK-CERT/Taranis-NG/main/resources/wordlists/sk_complete.csv",
    )
    db.session.add(sk_wordlist_category)
    db.session.commit()

    sk_wordlist = WordList(
        None,
        "Default SK stop list",
        "Slovak stop-word list packed with the standard Taranis NG installation.",
        [sk_wordlist_category],
        True,
    )
    db.session.add(sk_wordlist)
    db.session.commit()

    # Highlighting

    highlighting_wordlist_category = WordListCategory(
        name="Default highlighting wordlist",
        description="Sources: https://www.allot.com/100-plus-cybersecurity-terms-definitions/, https://content.teamascend.com/cybersecurity-glossary",  # noqa
        entries=[],
        link="https://raw.githubusercontent.com/SK-CERT/Taranis-NG/main/resources/wordlists/highlighting.csv",
    )
    db.session.add(highlighting_wordlist_category)
    db.session.commit()

    highlighting_wordlist = WordList(
        None,
        "Default highlighting wordlist",
        "Default highlighting list packed with the standard Taranis NG installation.",
        [highlighting_wordlist_category],
        False,
    )
    db.session.add(highlighting_wordlist)
    db.session.commit()


def pre_seed_default_user():
    from model.address import Address
    from model.organization import Organization
    from model.role import Role
    from model.user import User, UserProfile, UserRole, UserOrganization

    address = Address(
        "29 Arlington Avenue", "Islington, London", "N1 7BE", "United Kingdom"
    )
    db.session.add(address)
    db.session.commit()

    organization = Organization(
        None,
        "The Earth",
        "Earth is the third planet from the Sun and the only astronomical object known to harbor life.",
        address.id,
    )
    db.session.add(organization)
    db.session.commit()

    profile = UserProfile(True, False, [])
    db.session.add(profile)
    db.session.commit()

    user = User("admin", "Arthur Dent", profile.id)
    db.session.add(user)
    db.session.commit()

    admin_role = db.session.query(Role).filter_by(name="Admin").first()
    db.session.add(UserOrganization(user.id, organization.id))
    db.session.add(UserRole(user.id, admin_role))
    db.session.commit()

    address = Address(
        "Cherry Tree Rd",
        "Beaconsfield, Buckinghamshire",
        "HP9 1BH",
        "United Kingdom",
    )
    db.session.add(address)
    db.session.commit()

    organization = Organization(
        "The Clacks",
        "A network infrastructure of Semaphore Towers, that operate in a similar fashion to telegraph.",
        address.id,
    )
    db.session.add(organization)
    db.session.commit()

    profile = UserProfile(True, False)
    db.session.add(profile)
    db.session.commit()

    user = User("user", "Terry Pratchett", profile.id)
    db.session.add(user)
    db.session.commit()

    user_role = db.session.query(Role).filter_by(name="User").first()
    db.session.add(UserOrganization(user.id, organization.id))
    db.session.add(UserRole(user.id, user_role))
    db.session.commit()

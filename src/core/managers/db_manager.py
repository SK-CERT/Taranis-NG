from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, upgrade

db = SQLAlchemy()
migrate = Migrate()


def initialize(app):
    db.init_app(app)
    migrate.init_app(app, db)
    create_tables()


def create_tables():
    db.create_all()
    upgrade()
    pre_seed()


def pre_seed():
    pre_seed_source_groups()
    pre_seed_roles()
    pre_seed_attributes()
    pre_seed_report_items()
    pre_seed_wordlists()


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
        "ASSESS_ACCESS",
        "ASSESS_CREATE",
        "ASSESS_UPDATE",
        "ASSESS_DELETE",
        "ANALYZE_ACCESS",
        "ANALYZE_CREATE",
        "ANALYZE_UPDATE",
        "ANALYZE_DELETE",
        "PUBLISH_ACCESS",
        "PUBLISH_CREATE",
        "PUBLISH_UPDATE",
        "PUBLISH_DELETE",
        "PUBLISH_PRODUCT",
    ]

    if not db.session.query(Role).filter_by(name="Admin").first():
        admin_role = Role(
            "Admin", "Administrator role", db.session.query(Permission).all()
        )
        db.session.add(admin_role)
    if not db.session.query(Role).filter_by(name="User").first():
        user_role = Role("User", "Basic user role", default_user_permissions)
        db.session.add(user_role)
    db.session.commit()


def pre_seed_attributes():
    from model.attribute import Attribute, AttributeEnum
    from schema.attribute import AttributeType

    if not db.session.query(Attribute).filter_by(name="Text").first():
        attr_string = Attribute(
            "Text", "Simple text box", AttributeType.STRING, None, None, None
        )
        db.session.add(attr_string)

    if not db.session.query(Attribute).filter_by(name="Text Area").first():
        attr_text = Attribute(
            "Text Area", "Simple text area", AttributeType.TEXT, None, None, None
        )
        db.session.add(attr_text)

    if not db.session.query(Attribute).filter_by(name="TLP").first():
        attr_tlp = Attribute(
            "TLP", "Traffic Light Protocol element", AttributeType.TLP, None, None, None
        )
        db.session.add(attr_tlp)

    if not db.session.query(Attribute).filter_by(name="CPE").first():
        attr_cpe = Attribute(
            "CPE",
            "Common Platform Enumeration element",
            AttributeType.CPE,
            None,
            None,
            None,
        )
        db.session.add(attr_cpe)

    if not db.session.query(Attribute).filter_by(name="CVSS").first():
        attr_cvss = Attribute(
            "CVSS",
            "Common Vulnerability Scoring System element",
            AttributeType.CVSS,
            None,
            None,
            None,
        )
        db.session.add(attr_cvss)

    if not db.session.query(Attribute).filter_by(name="CVE").first():
        attr_cve = Attribute(
            "CVE",
            "Common Vulnerabilities and Exposures element",
            AttributeType.CVE,
            None,
            None,
            None,
        )
        db.session.add(attr_cve)

    if not db.session.query(Attribute).filter_by(name="Date").first():
        attr_date = Attribute(
            "Date", "Date picker", AttributeType.DATE, None, None, None
        )
        db.session.add(attr_date)

    db.session.commit()

    if not db.session.query(Attribute).filter_by(name="Confidentiality").first():
        attr_conf = Attribute(
            "Confidentiality",
            "Radio box for confidentiality level",
            AttributeType.RADIO,
            None,
            None,
            None,
        )
        db.session.add(attr_conf)
        db.session.commit()
        db.session.add(AttributeEnum(0, "UNRESTRICTED", "", attr_conf.id))
        db.session.add(AttributeEnum(1, "CLASSIFIED", "", attr_conf.id))
        db.session.add(AttributeEnum(2, "CONFIDENTIAL", "", attr_conf.id))
        db.session.add(AttributeEnum(3, "SECRET", "", attr_conf.id))
        db.session.add(AttributeEnum(4, "TOP SECRET", "", attr_conf.id))
        db.session.commit()

    if not db.session.query(Attribute).filter_by(name="Impact").first():
        attr_impact = Attribute(
            "Impact", "Combo box for impact level", AttributeType.ENUM, None, None, None
        )
        db.session.add(attr_impact)
        db.session.commit()
        db.session.add(
            AttributeEnum(
                0,
                "Malicious code execution affecting overall confidentiality, integrity, and availability of the system",
                "",
                attr_impact.id,
            )
        )
        db.session.add(AttributeEnum(1, "Malicious code execution", "", attr_impact.id))
        db.session.add(AttributeEnum(2, "Denial of service", "", attr_impact.id))
        db.session.add(AttributeEnum(3, "Privilege escalation", "", attr_impact.id))
        db.session.add(AttributeEnum(4, "Information exposure", "", attr_impact.id))
        db.session.add(
            AttributeEnum(5, "Unauthorized access to the system", "", attr_impact.id)
        )
        db.session.add(
            AttributeEnum(6, "Unauthorized change in system", "", attr_impact.id)
        )
        db.session.commit()

    if not db.session.query(Attribute).filter_by(name="Additional Data").first():
        attr_attribute_data = Attribute(
            "Additional Data",
            "Radio box for MISP additional data",
            AttributeType.RADIO,
            None,
            None,
            None,
        )
        db.session.add(attr_attribute_data)
        db.session.commit()
        db.session.add(
            AttributeEnum(
                0, "For Intrusion Detection System", "", attr_attribute_data.id
            )
        )
        db.session.add(
            AttributeEnum(1, "Disable Correlation", "", attr_attribute_data.id)
        )
        db.session.commit()

    if (
        not db.session.query(Attribute)
        .filter_by(name="MISP Event Distribution")
        .first()
    ):
        attr_event_distribution = Attribute(
            "MISP Event Distribution",
            "Combo box for MISP event distribution",
            AttributeType.ENUM,
            None,
            None,
            None,
        )
        db.session.add(attr_event_distribution)
        db.session.commit()
        db.session.add(
            AttributeEnum(0, "Your organisation only", "", attr_event_distribution.id)
        )
        db.session.add(
            AttributeEnum(1, "This community only", "", attr_event_distribution.id)
        )
        db.session.add(
            AttributeEnum(2, "Connected communities", "", attr_event_distribution.id)
        )
        db.session.add(
            AttributeEnum(3, "All communities", "", attr_event_distribution.id)
        )
        db.session.commit()

    if (
        not db.session.query(Attribute)
        .filter_by(name="MISP Event Threat Level")
        .first()
    ):
        attr_event_threat_level = Attribute(
            "MISP Event Threat Level",
            "Combo box for MISP event threat level",
            AttributeType.ENUM,
            None,
            None,
            None,
        )
        db.session.add(attr_event_threat_level)
        db.session.commit()
        db.session.add(AttributeEnum(0, "High", "", attr_event_threat_level.id))
        db.session.add(AttributeEnum(1, "Medium", "", attr_event_threat_level.id))
        db.session.add(AttributeEnum(2, "Low", "", attr_event_threat_level.id))
        db.session.add(AttributeEnum(3, "Undefined", "", attr_event_threat_level.id))
        db.session.commit()

    if not db.session.query(Attribute).filter_by(name="MISP Event Analysis").first():
        attr_event_analysis = Attribute(
            "MISP Event Analysis",
            "Combo box for MISP event analysis",
            AttributeType.ENUM,
            None,
            None,
            None,
        )
        db.session.add(attr_event_analysis)
        db.session.commit()
        db.session.add(AttributeEnum(0, "Initial", "", attr_event_analysis.id))
        db.session.add(AttributeEnum(1, "Ongoing", "", attr_event_analysis.id))
        db.session.add(AttributeEnum(2, "Completed", "", attr_event_analysis.id))
        db.session.commit()

    if (
        not db.session.query(Attribute)
        .filter_by(name="MISP Attribute Category")
        .first()
    ):
        attr_attribute_category = Attribute(
            "MISP Attribute Category",
            "Combo box for MISP attribute category",
            AttributeType.ENUM,
            None,
            None,
            None,
        )
        db.session.add(attr_attribute_category)
        db.session.commit()
        db.session.add(
            AttributeEnum(0, "Internal reference", "", attr_attribute_category.id)
        )
        db.session.add(
            AttributeEnum(1, "Targeting data", "", attr_attribute_category.id)
        )
        db.session.add(
            AttributeEnum(2, "Antivirus detection", "", attr_attribute_category.id)
        )
        db.session.add(
            AttributeEnum(3, "Payload delivery", "", attr_attribute_category.id)
        )
        db.session.add(
            AttributeEnum(4, "Artifacts dropped", "", attr_attribute_category.id)
        )
        db.session.add(
            AttributeEnum(5, "Payload installation", "", attr_attribute_category.id)
        )
        db.session.add(
            AttributeEnum(6, "Persistence mechanism", "", attr_attribute_category.id)
        )
        db.session.add(
            AttributeEnum(7, "Network activity", "", attr_attribute_category.id)
        )
        db.session.add(AttributeEnum(8, "Payload type", "", attr_attribute_category.id))
        db.session.add(AttributeEnum(9, "Attribution", "", attr_attribute_category.id))
        db.session.add(
            AttributeEnum(10, "External analysis", "", attr_attribute_category.id)
        )
        db.session.add(
            AttributeEnum(11, "Financial fraud", "", attr_attribute_category.id)
        )
        db.session.add(
            AttributeEnum(12, "Support Tool", "", attr_attribute_category.id)
        )
        db.session.add(
            AttributeEnum(13, "Social network", "", attr_attribute_category.id)
        )
        db.session.add(AttributeEnum(14, "Person", "", attr_attribute_category.id))
        db.session.add(AttributeEnum(15, "Other", "", attr_attribute_category.id))
        db.session.commit()

    if not db.session.query(Attribute).filter_by(name="MISP Attribute Type").first():
        attr_attribute_type = Attribute(
            "MISP Attribute Type",
            "Combo box for MISP attribute type",
            AttributeType.ENUM,
            None,
            None,
            None,
        )
        db.session.add(attr_attribute_type)
        db.session.commit()
        db.session.add(AttributeEnum(0, "md5", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(1, "sha1", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(2, "sha256", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(3, "filename", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(4, "pbd", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(5, "filename|md5", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(6, "filename|sha1", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(7, "filename|sha256", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(8, "ip-src", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(9, "ip-dst", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(10, "hostname", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(11, "domain", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(12, "domain|ip", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(13, "email-src", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(14, "eppn", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(15, "email-dst", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(16, "email-subject", "", attr_attribute_type.id))
        db.session.add(
            AttributeEnum(17, "email-attachment", "", attr_attribute_type.id)
        )
        db.session.add(AttributeEnum(18, "email-body", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(19, "float", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(20, "url", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(21, "http-method", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(22, "user-agent", "", attr_attribute_type.id))
        db.session.add(
            AttributeEnum(23, "ja3-fingerprint-md5", "", attr_attribute_type.id)
        )
        db.session.add(AttributeEnum(24, "hassh-md5", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(25, "hasshserver-md5", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(26, "reg-key", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(27, "regkey|value", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(28, "AS", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(29, "snort", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(30, "bro", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(31, "zeek", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(32, "community-id", "", attr_attribute_type.id))
        db.session.add(
            AttributeEnum(33, "pattern-in-traffic", "", attr_attribute_type.id)
        )
        db.session.add(
            AttributeEnum(34, "pattern-in-memory", "", attr_attribute_type.id)
        )
        db.session.add(AttributeEnum(35, "yara", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(36, "stix2-pattern", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(37, "sigma", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(38, "gene", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(39, "kusto-query", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(40, "mime-type", "", attr_attribute_type.id))
        db.session.add(
            AttributeEnum(41, "identity-card-number", "", attr_attribute_type.id)
        )
        db.session.add(AttributeEnum(42, "cookie", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(43, "vulnerability", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(44, "weakness", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(45, "link", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(46, "comment", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(47, "text", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(48, "hex", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(49, "other", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(50, "named pipe", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(51, "mutex", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(52, "target-user", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(53, "target-email", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(54, "target-machine", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(55, "target-org", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(56, "target-location", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(57, "target-external", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(58, "btc", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(59, "dash", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(60, "xmr", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(61, "iban", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(62, "bic", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(63, "bank-account-nr", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(64, "aba-rtn", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(65, "bin", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(66, "cc-number", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(67, "prtn", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(68, "phone-number", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(69, "threat-actor", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(70, "campaign-name", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(71, "campaign-id", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(72, "malware-type", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(73, "uri", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(74, "authentihash", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(75, "ssdeep", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(76, "implash", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(77, "pahash", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(78, "impfuzzy", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(79, "sha224", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(80, "sha384", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(81, "sha512", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(82, "sha512/224", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(83, "sha512/256", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(84, "tlsh", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(85, "cdhash", "", attr_attribute_type.id))
        db.session.add(
            AttributeEnum(86, "filename|authentihash", "", attr_attribute_type.id)
        )
        db.session.add(AttributeEnum(87, "filename|ssdeep", "", attr_attribute_type.id))
        db.session.add(
            AttributeEnum(88, "filename|implash", "", attr_attribute_type.id)
        )
        db.session.add(
            AttributeEnum(89, "filename|impfuzzy", "", attr_attribute_type.id)
        )
        db.session.add(AttributeEnum(90, "filename|pehash", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(91, "filename|sha224", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(92, "filename|sha384", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(93, "filename|sha512", "", attr_attribute_type.id))
        db.session.add(
            AttributeEnum(94, "filename|sha512/224", "", attr_attribute_type.id)
        )
        db.session.add(
            AttributeEnum(95, "filename|sha512/256", "", attr_attribute_type.id)
        )
        db.session.add(AttributeEnum(96, "filename|tlsh", "", attr_attribute_type.id))
        db.session.add(
            AttributeEnum(97, "windows-scheduled-task", "", attr_attribute_type.id)
        )
        db.session.add(
            AttributeEnum(98, "windows-service-name", "", attr_attribute_type.id)
        )
        db.session.add(
            AttributeEnum(99, "windows-service-displayname", "", attr_attribute_type.id)
        )
        db.session.add(
            AttributeEnum(100, "whois-registrant-email", "", attr_attribute_type.id)
        )
        db.session.add(
            AttributeEnum(101, "whois-registrant-phone", "", attr_attribute_type.id)
        )
        db.session.add(
            AttributeEnum(102, "whois-registrant-name", "", attr_attribute_type.id)
        )
        db.session.add(
            AttributeEnum(103, "whois-registrant-org", "", attr_attribute_type.id)
        )
        db.session.add(
            AttributeEnum(104, "whois-registrar", "", attr_attribute_type.id)
        )
        db.session.add(
            AttributeEnum(105, "whois-creation-date", "", attr_attribute_type.id)
        )
        db.session.add(
            AttributeEnum(106, "x509-fingerprint-sha1", "", attr_attribute_type.id)
        )
        db.session.add(
            AttributeEnum(107, "x509-fingerprint-md5", "", attr_attribute_type.id)
        )
        db.session.add(
            AttributeEnum(108, "x509-fingerprint-sha256", "", attr_attribute_type.id)
        )
        db.session.add(AttributeEnum(109, "dns-soa-email", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(110, "size-in-bytes", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(111, "counter", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(112, "datetime", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(113, "cpe", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(114, "port", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(115, "ip-dist|port", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(116, "ip-src|port", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(117, "hostname|port", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(118, "mac-address", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(119, "mac-eui-64", "", attr_attribute_type.id))
        db.session.add(
            AttributeEnum(120, "email-dst-display-name", "", attr_attribute_type.id)
        )
        db.session.add(
            AttributeEnum(121, "email-src-display-name", "", attr_attribute_type.id)
        )
        db.session.add(AttributeEnum(122, "email-header", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(123, "email-reply-to", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(124, "email-x-mailer", "", attr_attribute_type.id))
        db.session.add(
            AttributeEnum(125, "email-mime-boundary", "", attr_attribute_type.id)
        )
        db.session.add(
            AttributeEnum(126, "email-thread-index", "", attr_attribute_type.id)
        )
        db.session.add(
            AttributeEnum(127, "email-message-id", "", attr_attribute_type.id)
        )
        db.session.add(
            AttributeEnum(128, "github-username", "", attr_attribute_type.id)
        )
        db.session.add(
            AttributeEnum(129, "github-repository", "", attr_attribute_type.id)
        )
        db.session.add(
            AttributeEnum(130, "githzb-organisation", "", attr_attribute_type.id)
        )
        db.session.add(AttributeEnum(131, "jabber-id", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(132, "twitter-id", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(133, "first-name", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(134, "middle-name", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(135, "last-name", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(136, "date-of-birth", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(137, "gender", "", attr_attribute_type.id))
        db.session.add(
            AttributeEnum(138, "passport-number", "", attr_attribute_type.id)
        )
        db.session.add(
            AttributeEnum(139, "passport-country", "", attr_attribute_type.id)
        )
        db.session.add(
            AttributeEnum(140, "passport-expiration", "", attr_attribute_type.id)
        )
        db.session.add(AttributeEnum(141, "redress-number", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(142, "nationality", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(143, "visa-number", "", attr_attribute_type.id))
        db.session.add(
            AttributeEnum(144, "issue-date-of-the-visa", "", attr_attribute_type.id)
        )
        db.session.add(
            AttributeEnum(145, "primary-residence", "", attr_attribute_type.id)
        )
        db.session.add(
            AttributeEnum(146, "country-of-residence", "", attr_attribute_type.id)
        )
        db.session.add(
            AttributeEnum(147, "special-service-request", "", attr_attribute_type.id)
        )
        db.session.add(
            AttributeEnum(148, "frequent-flyer-number", "", attr_attribute_type.id)
        )
        db.session.add(AttributeEnum(149, "travel-details", "", attr_attribute_type.id))
        db.session.add(
            AttributeEnum(150, "payments-details", "", attr_attribute_type.id)
        )
        db.session.add(
            AttributeEnum(
                151, "place-port-of-original-embarkation", "", attr_attribute_type.id
            )
        )
        db.session.add(
            AttributeEnum(
                152, "passenger-name-record-locator-number", "", attr_attribute_type.id
            )
        )
        db.session.add(
            AttributeEnum(153, "mobile-application-id", "", attr_attribute_type.id)
        )
        db.session.add(
            AttributeEnum(154, "chrome-extension-id", "", attr_attribute_type.id)
        )
        db.session.add(AttributeEnum(155, "cortex", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(156, "boolean", "", attr_attribute_type.id))
        db.session.add(AttributeEnum(157, "anonymised", "", attr_attribute_type.id))
        db.session.commit()

    if (
        not db.session.query(Attribute)
        .filter_by(name="MISP Attribute Distribution")
        .first()
    ):
        attr_attribute_distribution = Attribute(
            "MISP Attribute Distribution",
            "Combo box for MISP attribute type",
            AttributeType.ENUM,
            None,
            None,
            None,
        )
        db.session.add(attr_attribute_distribution)
        db.session.commit()
        db.session.add(
            AttributeEnum(
                0, "Your organisation only", "", attr_attribute_distribution.id
            )
        )
        db.session.add(
            AttributeEnum(1, "This community only", "", attr_attribute_distribution.id)
        )
        db.session.add(
            AttributeEnum(
                2, "Connected communities", "", attr_attribute_distribution.id
            )
        )
        db.session.add(
            AttributeEnum(3, "All communities", "", attr_attribute_distribution.id)
        )
        db.session.add(
            AttributeEnum(4, "Inherit event", "", attr_attribute_distribution.id)
        )
        db.session.commit()


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
        report_item_type = ReportItemType("Vulnerability Report", "Basic report type")
        db.session.add(report_item_type)
        db.session.commit()

        group1 = AttributeGroup("Vulnerability", "", None, None, 0, report_item_type.id)
        db.session.add(group1)
        group2 = AttributeGroup(
            "Identify and Act", "", None, None, 0, report_item_type.id
        )
        db.session.add(group2)
        group3 = AttributeGroup("Resources", "", None, None, 0, report_item_type.id)
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
        report_item_type = ReportItemType("MISP Report", "MISP report type")
        db.session.add(report_item_type)
        db.session.commit()

        group4 = AttributeGroup("Event", "", None, None, 0, report_item_type.id)
        db.session.add(group4)
        group5 = AttributeGroup("Attribute", "", None, None, 0, report_item_type.id)
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

    en_wordlist = WordList(
        "Default EN stop list",
        "English stop-word list packed with the standard Taranis NG installation.",
        True,
    )
    db.session.add(en_wordlist)
    db.session.commit()

    en_wordlist_category = WordListCategory(
        "Default EN stop list",
        "Source: https://www.maxqda.de/hilfe-mx20-dictio/stopp-listen",
        en_wordlist.id,
        "https://raw.githubusercontent.com/SK-CERT/Taranis-NG/main/resources/wordlists/en_complete.csv",
    )
    db.session.add(en_wordlist_category)
    db.session.commit()

    # Slovak

    sk_wordlist = WordList(
        "Default SK stop list",
        "Slovak stop-word list packed with the standard Taranis NG installation.",
        True,
    )
    db.session.add(sk_wordlist)
    db.session.commit()

    sk_wordlist_category = WordListCategory(
        "Default SK stop list",
        "Source: https://github.com/stopwords-iso/stopwords-sk/blob/master/stopwords-sk.txt",
        sk_wordlist.id,
        "https://raw.githubusercontent.com/SK-CERT/Taranis-NG/main/resources/wordlists/sk_complete.csv",
    )
    db.session.add(sk_wordlist_category)
    db.session.commit()

    # Highlighting

    highlighting_wordlist = WordList(
        "Default highlighting wordlist",
        "Default highlighting list packed with the standard Taranis NG installation.",
        False,
    )
    db.session.add(highlighting_wordlist)
    db.session.commit()

    highlighting_wordlist_category = WordListCategory(
        "Default highlighting wordlist",
        "Sources: https://www.allot.com/100-plus-cybersecurity-terms-definitions/, https://content.teamascend.com/cybersecurity-glossary",
        highlighting_wordlist.id,
        "https://raw.githubusercontent.com/SK-CERT/Taranis-NG/main/resources/wordlists/highlighting.csv",
    )
    db.session.add(highlighting_wordlist_category)
    db.session.commit()

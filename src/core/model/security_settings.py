"""Site-wide security settings (single row).

Holds the WebAuthn relying-party configuration used by passkey sign-in, and the
site-wide two-factor policy. Passkeys are *credentials owned by users* (see
:mod:`model.webauthn_credential`), not an identity provider - the relying-party
fields only describe this site to the authenticator, so they live here rather
than in ``auth_provider``.

``require_mfa`` here is the *site* level of the policy. It is one of four, and
they are OR-ed: see :func:`managers.auth_manager.mfa_required`.
"""

from __future__ import annotations

from datetime import datetime

from managers.db_manager import db
from shared.common import TZ
from shared.schema.security_settings import SecuritySettingsSchema


class SecuritySettings(db.Model):
    """Site-wide security settings.

    Attributes:
        id (int): Always 1 - this table holds a single row.
        passkey_enabled (bool): Whether passkeys are available at all - the master
            switch that also governs registration.
        passkey_first_factor (bool): Whether a passkey may start a login on its own.
            Off means passkeys exist only as a second factor.
        passkey_second_factor (bool): Whether a registered passkey may satisfy the
            second-factor step. Off means TOTP is the only accepted second factor.
        require_mfa (bool): Whether every user must have a second factor.
        auth_generation (int): Revision counter invalidating all older JWTs.
        rp_id (str): WebAuthn relying-party ID (the site's registrable domain).
        rp_name (str): Relying-party display name shown by the authenticator.
        origins (str): Comma-separated list of allowed origins.
        updated_by (str): User who last updated the settings.
        updated_at (datetime): Timestamp of the last update.
    """

    __tablename__ = "security_settings"

    id = db.Column(db.Integer, primary_key=True)
    passkey_enabled = db.Column(db.Boolean, nullable=False, default=False, server_default="false")
    passkey_first_factor = db.Column(db.Boolean, nullable=False, default=True, server_default="true")
    passkey_second_factor = db.Column(db.Boolean, nullable=False, default=True, server_default="true")
    require_mfa = db.Column(db.Boolean, nullable=False, default=False, server_default="false")
    auth_generation = db.Column(db.Integer, nullable=False, default=1, server_default="1")
    rp_id = db.Column(db.String(), nullable=True)
    rp_name = db.Column(db.String(), nullable=True)
    origins = db.Column(db.String(), nullable=True)
    updated_by = db.Column(db.String())
    updated_at = db.Column(db.DateTime)

    @classmethod
    def get(cls) -> SecuritySettings:
        """Return the settings row, creating it with safe defaults when absent.

        Returns:
            SecuritySettings: The single settings row.
        """
        record = db.session.get(cls, 1)
        if not record:
            record = cls()
            record.id = 1
            record.passkey_enabled = False
            record.passkey_first_factor = True
            record.passkey_second_factor = True
            record.require_mfa = False
            record.auth_generation = 1
            record.rp_name = "Taranis NG"
            db.session.add(record)
            db.session.commit()
        return record

    @classmethod
    def get_json(cls) -> dict:
        """Return the settings in JSON format."""
        return SecuritySettingsSchema().dump(cls.get())

    @classmethod
    def update(cls, data: dict, user_name: str) -> SecuritySettings:
        """Update the security settings.

        Args:
            data (dict): The new settings.
            user_name (str): User performing the update.

        Returns:
            SecuritySettings: The updated settings row.

        Raises:
            ValueError: When passkeys are enabled without a complete relying-party
                configuration, or with neither factor switch left on.
        """
        new = SecuritySettingsSchema().load(data)
        record = cls.get()
        record.passkey_enabled = bool(new.get("passkey_enabled"))
        record.passkey_first_factor = bool(new.get("passkey_first_factor"))
        record.passkey_second_factor = bool(new.get("passkey_second_factor"))
        record.require_mfa = bool(new.get("require_mfa"))
        record.rp_id = (new.get("rp_id") or "").strip()
        record.rp_name = (new.get("rp_name") or "").strip() or "Taranis NG"
        record.origins = (new.get("origins") or "").strip()

        if record.passkey_enabled and not (record.rp_id and record.get_origins()):
            msg = "Passkey sign-in requires a relying-party ID and at least one origin"
            raise ValueError(msg)

        # Enabled with neither switch on, passkeys could be registered but never
        # used for anything - refuse the combination rather than let it look armed.
        if record.passkey_enabled and not (record.passkey_first_factor or record.passkey_second_factor):
            msg = "Passkeys must be usable as a first or a second factor, or be switched off entirely"
            raise ValueError(msg)

        record.updated_by = user_name
        record.updated_at = datetime.now(TZ)
        db.session.commit()
        return record

    def get_origins(self) -> list[str]:
        """Return the allowed origins as a normalized list."""
        return [origin.strip() for origin in (self.origins or "").split(",") if origin.strip()]

    @classmethod
    def passkeys_enabled(cls) -> bool:
        """Tell whether passkeys are available at all on this installation.

        The master switch: it governs registration, and both factor switches are
        gated behind it. Where a passkey may actually be *used* is decided by
        :meth:`passkey_first_factor_enabled` and :meth:`passkey_second_factor_enabled`.
        """
        record = cls.get()
        return bool(record.passkey_enabled and record.rp_id and record.get_origins())

    @classmethod
    def passkey_first_factor_enabled(cls) -> bool:
        """Tell whether a passkey may start a login on its own.

        Requires the relying party to be configured at all - without it no passkey
        can be verified, whatever this switch says.
        """
        return bool(cls.passkeys_enabled() and cls.get().passkey_first_factor)

    @classmethod
    def passkey_second_factor_enabled(cls) -> bool:
        """Tell whether a passkey may satisfy the second-factor step.

        Requires the relying party to be configured at all - without it no passkey
        can be verified, whatever this switch says.
        """
        return bool(cls.passkeys_enabled() and cls.get().passkey_second_factor)

    @classmethod
    def mfa_required(cls) -> bool:
        """Tell whether this installation demands a second factor of every user."""
        return bool(cls.get().require_mfa)

    @classmethod
    def get_auth_generation(cls) -> int:
        """Return the positive integer generation required in every JWT."""
        generation = cls.get().auth_generation
        if type(generation) is not int or generation < 1:  # bool is intentionally invalid
            msg = "Security settings contain an invalid authentication generation"
            raise RuntimeError(msg)
        return generation

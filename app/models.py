from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from crypto import decrypt_data

db = SQLAlchemy()


class IA(db.Model):
    __tablename__ = "ias"
    id = db.Column(db.Integer, primary_key=True, index=True)
    name = db.Column(db.String, nullable=False)
    phone_number = db.Column(db.String, nullable=False)
    status = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime(timezone=True), server_default=db.func.now(), onupdate=db.func.now()
    )

    # Relacionamentos
    prompts = relationship("Prompt", back_populates="ia", cascade="all, delete-orphan")
    ia_config = relationship(
        "IAConfig", back_populates="ia", uselist=False, cascade="all, delete-orphan"
    )
    leads = relationship("Lead", back_populates="ia", cascade="all, delete-orphan")

    @property
    def active_prompt(self):
        active = [p for p in self.prompts if p.is_active]
        return active[0] if active else None


class Prompt(db.Model):
    __tablename__ = "prompts"
    id = db.Column(db.Integer, primary_key=True, index=True)
    ia_id = db.Column(db.Integer, db.ForeignKey("ias.id"), nullable=False)
    prompt_text = db.Column(db.String, nullable=False)
    is_active = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime(timezone=True), server_default=db.func.now(), onupdate=db.func.now()
    )
    ia = relationship("IA", back_populates="prompts")


class IAConfig(db.Model):
    __tablename__ = "ia_config"
    id = db.Column(db.Integer, primary_key=True, index=True)
    ia_id = db.Column(db.Integer, db.ForeignKey("ias.id"), nullable=False)
    channel = db.Column(db.String, nullable=False)
    ai_api = db.Column(db.String, nullable=False)
    encrypted_credentials = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime(timezone=True), server_default=db.func.now(), onupdate=db.func.now()
    )
    ia = relationship("IA", back_populates="ia_config")

    @property
    def credentials(self):
        return decrypt_data(self.encrypted_credentials)


class Lead(db.Model):
    __tablename__ = "leads"
    id = db.Column(db.Integer, primary_key=True, index=True)
    ia_id = db.Column(db.Integer, db.ForeignKey("ias.id"), nullable=False)
    name = db.Column(db.String, nullable=True)
    phone = db.Column(db.String, nullable=True, unique=True)
    message = db.Column(db.JSON, nullable=False)
    resume = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime(timezone=True), server_default=db.func.now(), onupdate=db.func.now()
    )
    ia = relationship("IA", back_populates="leads")

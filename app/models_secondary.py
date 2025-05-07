# models_secondary.py
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func, ForeignKey, JSON
from sqlalchemy.orm import relationship
from crypto import *

Base2 = declarative_base()  # Base "pura" para o banco secundário

class IA(Base2):
    __tablename__ = 'ias'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    status = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relacionamentos
    prompts = relationship("Prompt", back_populates="ia", cascade="all, delete-orphan")
    ia_config = relationship("IAConfig", back_populates="ia", uselist=False, cascade="all, delete-orphan")
    leads = relationship("Lead", back_populates="ia", uselist=False, cascade="all, delete-orphan")
    
    @property
    def active_prompt(self):
        active = [p for p in self.prompts if p.is_active]
        return active[0] if active else None

class Prompt(Base2):
    __tablename__ = 'prompts'
    id = Column(Integer, primary_key=True, index=True)
    ia_id = Column(Integer, ForeignKey('ias.id'), nullable=False)
    prompt_text = Column(String, nullable=False)
    is_active = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    ia = relationship("IA", back_populates="prompts")

class IAConfig(Base2):
    __tablename__ = 'ia_config'
    id = Column(Integer, primary_key=True, index=True)
    ia_id = Column(Integer, ForeignKey('ias.id'), nullable=False)
    channel = Column(String, nullable=False)
    ai_api = Column(String, nullable=False)
    encrypted_credentials = Column(String, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    ia = relationship("IA", back_populates="ia_config")

    def credentials(self):

        return decrypt_data(self.encrypted_credentials)

    

class Lead(Base2):
    __tablename__ = 'leads'
    id = Column(Integer, primary_key=True, index=True)
    ia_id = Column(Integer, ForeignKey('ias.id'), nullable=False)
    name = Column(String, nullable=True)
    phone = Column(String, nullable=True, unique=True)
    message = Column(JSON, nullable=False)
    resume = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    ia = relationship("IA", back_populates="leads")

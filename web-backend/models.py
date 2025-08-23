from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime

Base = declarative_base()

class Store(Base):
    __tablename__ = 'stores'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    district = Column(String)  # 필터 가능한 최소 단위 주소
    lat = Column(Float, nullable=True)  # 위도
    lon = Column(Float, nullable=True)  # 경도
    phone = Column(String)
    
    @property
    def categories(self):
        # store가 가진 모든 certification의 카테고리 코드 집합 반환
        return list({cert.cert_type.category_code for cert in self.certifications if cert.cert_type and cert.cert_type.category_code})

    raw_meta = Column(JSON)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    score = Column(Integer, default=0)

    certifications = relationship("Certification", back_populates="store")
    cardnews = relationship("CardNews", back_populates="store")

class CertificationType(Base):
    __tablename__ = 'certification_types'
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)           
    name = Column(String, nullable=False)                         
    description = Column(String)
    issuing_agency = Column(String)                               
    category_code = Column(String, ForeignKey('categories.code'))

    certifications = relationship("Certification", back_populates="cert_type")
    category = relationship("Category", back_populates="certification_types")

class Certification(Base):
    __tablename__ = 'certifications'
    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey('stores.id'))
    cert_type_id = Column(Integer, ForeignKey('certification_types.id'))

    store = relationship("Store", back_populates="certifications")
    cert_type = relationship("CertificationType", back_populates="certifications")

class CardNews(Base):
    __tablename__ = 'cardnews'
    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey('stores.id'), nullable=False)
    title = Column(String, nullable=False)
    summary = Column(String, nullable=False)
    categories = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    raw_json = Column(JSON)

    store = relationship("Store", back_populates="cardnews")

class Category(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True)
    name = Column(String)
    description = Column(String)

    certification_types = relationship("CertificationType", back_populates="category")
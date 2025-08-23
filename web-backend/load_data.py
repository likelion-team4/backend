# load_data.py
import csv
import datetime
import os
import json
import requests
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from models import Base, Store, Certification, CertificationType, Category

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
KAKAO_API_KEY = os.environ.get("KAKAO_API_KEY")

# SQLite timeout 증가, check_same_thread 유지
engine = create_engine(
    "sqlite:///database.db",
    connect_args={"check_same_thread": False, "timeout": 30}
)
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

def geocode_address(address):
    if not address:
        return None, None
    try:
        url = "https://dapi.kakao.com/v2/local/search/address.json"
        headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
        params = {"query": address}
        resp = requests.get(url, headers=headers, params=params, timeout=5)
        resp.raise_for_status()
        docs = resp.json().get("documents", [])
        if docs:
            y, x = float(docs[0]["y"]), float(docs[0]["x"])
            return y, x
    except Exception as e:
        logger.warning(f"[Geocoding Error] {address}: {e}")
    return None, None

def load_categories(session):
    categories = [
        {"code": "good_price", "name": "착한 가격", "description": "물가 대비 저렴"},
        {"code": "eco_friendly", "name": "친환경", "description": "환경 보호 실천"},
        {"code": "sharing", "name": "나눔 실천", "description": "기부·봉사"},
        {"code": "welfare", "name": "복지 배려", "description": "사회적 약자 배려"},
        {"code": "local_industry", "name": "지역 상생", "description": "지역 활용"},
        {"code": "youth_store", "name": "청년 가게", "description": "청년 운영"},
        {"code": "disadvantaged_friend", "name": "취약계층 친화", "description": "친화적 운영"},
        {"code": "multicultural", "name": "다문화", "description": "문화 교류"},
        {"code": "local_culture", "name": "지역 문화", "description": "문화 보존"}
    ]
    for cat in categories:
        if not session.query(Category).filter_by(code=cat["code"]).first():
            session.add(Category(**cat))
    session.commit()

def load_certification_types(session):
    cert_types = [
        {"code": "good_price", "name": "착한가격업소 인증", "category_code": "good_price", "issuing_agency": "행정안전부"},
        {"code": "eco_friendly", "name": "녹색매장 인증", "category_code": "eco_friendly", "issuing_agency": "한국환경산업기술원"},
        {"code": "1004campaign", "name": "천사나눔 인증", "category_code": "sharing", "issuing_agency": "천사무료급식소"},
        {"code": "vision_store", "name": "비전스토어 인증", "category_code": "sharing", "issuing_agency": "월드비전"},
    ]
    for ct in cert_types:
        if not session.query(CertificationType).filter_by(code=ct["code"]).first():
            category = session.query(Category).filter_by(code=ct["category_code"]).first()
            session.add(CertificationType(
                code=ct["code"],
                name=ct["name"],
                issuing_agency=ct["issuing_agency"],
                category_code=category.code if category else None
            ))
    session.commit()

def load_stores_from_csv(session, csv_path, cert_code, name_keys, batch_size=10):
    try:
        with open(csv_path, newline="", encoding="cp949") as f:
            reader = csv.DictReader(f)
            cert_type = session.query(CertificationType).filter_by(code=cert_code).first()
            count = 0
            for row in reader:
                store_name = next((row.get(k) for k in name_keys if row.get(k)), None)
                if not store_name:
                    continue
                try:
                    store = session.query(Store).filter_by(name=store_name).first()
                    if not store:
                        lat, lon = geocode_address(row.get("주소", ""))
                        store = Store(
                            name=store_name,
                            address=row.get("주소", ""),
                            district=row.get("시군", ""),
                            lat=lat,
                            lon=lon,
                            phone=row.get("연락처", ""),
                            raw_meta=row,
                            created_at=datetime.datetime.utcnow(),
                            score=0,
                        )
                        session.add(store)
                        session.flush()
                    if cert_type and not session.query(Certification).filter_by(store_id=store.id, cert_type_id=cert_type.id).first():
                        session.add(Certification(store_id=store.id, cert_type_id=cert_type.id))
                    count += 1
                    if count % batch_size == 0:
                        session.commit()
                except SQLAlchemyError as e:
                    session.rollback()
                    logger.error(f"[CSV Row Error] {row}: {e}")
            session.commit()
    except Exception as e:
        logger.error(f"[CSV Load Error] {csv_path}: {e}")

def load_stores_from_json(session, json_path, cert_code, batch_size=10):
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        cert_type = session.query(CertificationType).filter_by(code=cert_code).first()
        count = 0
        for item in data:
            store_name = item.get("name")
            if not store_name:
                continue
            try:
                store = session.query(Store).filter_by(name=store_name).first()
                if not store:
                    lat, lon = geocode_address(item.get("address", ""))
                    store = Store(
                        name=store_name,
                        address=item.get("address", ""),
                        district=item.get("district", ""),
                        lat=lat,
                        lon=lon,
                        phone=item.get("phone", ""),
                        raw_meta=item,
                        created_at=datetime.datetime.utcnow(),
                        score=0,
                    )
                    session.add(store)
                    session.flush()
                if cert_type and not session.query(Certification).filter_by(store_id=store.id, cert_type_id=cert_type.id).first():
                    session.add(Certification(store_id=store.id, cert_type_id=cert_type.id))
                count += 1
                if count % batch_size == 0:
                    session.commit()
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"[JSON Row Error] {item}: {e}")
        session.commit()
    except Exception as e:
        logger.error(f"[JSON Load Error] {json_path}: {e}")

def update_store_scores(session):
    for store in session.query(Store).all():
        cert_count = session.query(Certification).filter_by(store_id=store.id).count()
        store.score = (cert_count or 0) * 50
    session.commit()

def main():
    with Session() as session:
        load_categories(session)
        load_certification_types(session)
        load_stores_from_csv(session, os.path.join(DATA_DIR, "good_price.csv"), "good_price", ["업소명"])
        load_stores_from_csv(session, os.path.join(DATA_DIR, "green_store.csv"), "eco_friendly", ["매장명", "업체명"])
        load_stores_from_json(session, os.path.join(DATA_DIR, "1004campaign.json"), "1004campaign")
        load_stores_from_json(session, os.path.join(DATA_DIR, "vision_store.json"), "vision_store")
        update_store_scores(session)

if __name__ == "__main__":
    main()
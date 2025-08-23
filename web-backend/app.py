# Flask 웹 서버
from flask import Flask, jsonify, request, abort
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, joinedload
from contextlib import contextmanager
import os
import datetime
import requests
import json
import load_data  # CSV/JSON 초기 데이터 로딩
from models import Base, Store, Certification, CertificationType, Category, CardNews

app = Flask(__name__)

# DB 세팅
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")
engine = create_engine(f"sqlite:///{os.path.abspath(DB_PATH)}")
Session = sessionmaker(bind=engine)

# AI 서버 설정
AI_SERVER_URL = "http://localhost:5001/ai/generate_stores"

# 카카오 API 키 불러오기
KAKAO_API_KEY = os.environ.get("KAKAO_API_KEY")

# 최소 점수 기준
MIN_SCORE = 50

# 테이블 생성
Base.metadata.create_all(engine)

# Context manager로 세션 안전하게 관리
@contextmanager
def get_session():
    session = Session()
    try:
        yield session
    finally:
        session.close()

# Helper 함수
def add_or_get_category(session, cat_name):
    category = session.query(Category).filter_by(code=cat_name).first()  # code 기준 조회
    if not category:
        category = Category(code=cat_name, name=cat_name)
        session.add(category)
        session.flush()
    return category

def add_or_get_cert_type(session, category):
    cert_type = session.query(CertificationType).filter_by(code=category.code).first()
    if not cert_type:
        cert_type = CertificationType(
            code=category.code,
            name=category.name,
            category_code=category.code
        )
        session.add(cert_type)
        session.flush()
    return cert_type

def link_certification(session, store, cert_type):
    exists = session.query(Certification).filter_by(
        store_id=store.id, cert_type_id=cert_type.id
    ).first()
    if not exists:
        session.add(Certification(store_id=store.id, cert_type_id=cert_type.id))

def geocode_address(address):
    # 주소를 좌표(lat, lon)로 변환
    if not address:
        return None, None
    try:
        url = "https://dapi.kakao.com/v2/local/search/address.json"
        headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
        params = {"query": address}
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        docs = resp.json().get("documents", [])
        if docs:
            return float(docs[0]["y"]), float(docs[0]["x"])  # (lat, lon)
    except Exception as e:
        print(f"[Geocoding Error] {address}: {e}")
    return None, None

# Store -> dict 변환
def store_to_dict(store, include_details=False, include_cardnews=False):
    data = {
        "id": store.id,
        "name": store.name,
        "lat": store.lat,
        "lon": store.lon,
        "score": store.score,
        "categories": store.categories,
    }

    if include_details:
        data.update({
            "address": store.address,
            "phone": store.phone,
            "certifications": [
                {"source": getattr(cert.cert_type, 'name', "")} for cert in store.certifications
            ]
        })

    if include_cardnews:
        data["cardnews"] = [
            {
                "title": c.title,
                "summary": c.summary,
                "created_at": c.created_at.strftime("%Y-%m-%d")
            } for c in getattr(store, "cardnews", [])
        ]

    return data

# AI 서버에서 데이터 가져오기
def fetch_and_store_ai_data():
    try:
        resp = requests.get(AI_SERVER_URL, timeout=5)
        resp.raise_for_status()
        data_list = resp.json()
    except Exception as e:
        print(f"[Error] AI data fetch failed: {e}")
        return

    with get_session() as session:
        for data in data_list:
            store_name = data.get("store_name")
            address = data.get("address", "")
            categories = data.get("categories", [])
            add_score = data.get("positive_news_count", 0) * 25 + data.get("positive_sns_count", 0) * 10

            # cardnews dict/list 대응
            cardnews_data = data.get("cardnews", [])
            if isinstance(cardnews_data, dict):
                cardnews_list = [cardnews_data]
            elif isinstance(cardnews_data, list):
                cardnews_list = cardnews_data
            else:
                cardnews_list = []

            # 주소 기준 조회
            store = session.query(Store).filter_by(address=address).first()
            if not store and add_score >= MIN_SCORE:
                # 여기서 좌표 채우기
                lat, lon = geocode_address(address)

                store = Store(
                    name=store_name,
                    address=address,
                    lat=lat,
                    lon=lon,
                    score=add_score,
                    created_at=datetime.datetime.utcnow()
                )
                session.add(store)
                session.flush()
            elif store:
                store.score += add_score
                # 기존 스토어인데 좌표가 비어 있다면 채워주기
                if (store.lat is None or store.lon is None) and address:
                    lat, lon = geocode_address(address)
                    store.lat, store.lon = lat, lon

            if store:
                for cat_name in categories:
                    category = add_or_get_category(session, cat_name)
                    cert_type = add_or_get_cert_type(session, category)
                    link_certification(session, store, cert_type)

                for cn in cardnews_list:
                    new_card = CardNews(
                        store_id=store.id,
                        title=cn.get("title", ""),
                        summary=cn.get("summary", ""),
                        created_at=datetime.datetime.utcnow(),
                    )
                    session.add(new_card)

        session.commit()

# AI 서버에서 처리 결과 받기
@app.route('/stores/process', methods=['POST'])
def process_store_result():
    # 원본 body 그대로 찍기
    print("=== [DEBUG] Raw request data ===")
    print(request.data.decode("utf-8"))

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data received"}), 400
    
    # 파싱된 값들 확인
    print("=== [DEBUG] Parsed JSON ===")
    print(json.dumps(data, indent=2, ensure_ascii=False))

    store_name = data.get("store_name")
    address = data.get("address", "")
    categories = data.get("categories", [])
    add_score = data.get("positive_news_count", 0) * 25 + data.get("positive_sns_count", 0) * 10

    # cardnews dict/list 대응
    cardnews_data = data.get("cardnews", [])
    if isinstance(cardnews_data, dict):
        cardnews_list = [cardnews_data]
    elif isinstance(cardnews_data, list):
        cardnews_list = cardnews_data
    else:
        cardnews_list = []

    with get_session() as session:
        # 주소 기준으로 store 조회
        store = session.query(Store).filter_by(address=address).first()

        # store가 없고 점수가 기준 이상이면 새로 생성
        if not store and add_score >= MIN_SCORE:
            # 좌표 변환 추가
            lat, lon = geocode_address(address)

            store = Store(
                name=store_name,
                address=address,
                lat=lat,
                lon=lon,
                score=add_score,
                created_at=datetime.datetime.utcnow()
            )
            session.add(store)
            session.flush()  # store.id를 사용하려면 flush 필요
        elif store:
            store.score += add_score
            # 기존 store인데 좌표가 없으면 채워주기
            if (store.lat is None or store.lon is None) and address:
                lat, lon = geocode_address(address)
                store.lat, store.lon = lat, lon

        # store가 생성되거나 이미 존재하는 경우에만 연결
        if store:
            # certification 처리
            for cat_name in categories:
                category = add_or_get_category(session, cat_name)
                cert_type = add_or_get_cert_type(session, category)
                link_certification(session, store, cert_type)

            # 카드뉴스 처리
            for cn in cardnews_list:
                new_card = CardNews(
                    store_id=store.id,
                    title=cn.get("title", ""),
                    summary=cn.get("summary", ""),
                    created_at=datetime.datetime.utcnow(),
                )
                session.add(new_card)

        session.commit()
    return jsonify({"status": "ok", "store": store_name}), 200

# 모든 스토어 조회
@app.route('/stores', methods=['GET'])
def get_stores():
    category_filter = request.args.get('categories')
    with get_session() as session:
        query = session.query(Store).options(
            joinedload(Store.certifications).joinedload(Certification.cert_type),
            joinedload(Store.cardnews)
        ).filter(Store.score >= MIN_SCORE)

        if category_filter:
            query = query.join(Store.certifications).join(Certification.cert_type).filter(
                CertificationType.category_code == category_filter
            ).distinct()

        stores = query.all()
        return jsonify([store_to_dict(s, include_cardnews=True) for s in stores])

# 가게명 검색
@app.route("/stores/search", methods=["GET"])
def search_stores_by_name():
    search_query = request.args.get("q", "").strip()
    if not search_query:
        return jsonify([])
    with get_session() as session:
        stores = session.query(Store).options(
            joinedload(Store.certifications).joinedload(Certification.cert_type),
            joinedload(Store.cardnews)
        ).filter(
            Store.score >= MIN_SCORE,
            Store.name.ilike(f"%{search_query}%")
        ).all()
        return jsonify([store_to_dict(s, include_cardnews=True) for s in stores])

# 특정 스토어 상세 조회
@app.route('/stores/<int:store_id>', methods=['GET'])
def get_store_detail(store_id):
    with get_session() as session:
        store = session.query(Store).options(
            joinedload(Store.certifications).joinedload(Certification.cert_type),
            joinedload(Store.cardnews)
        ).filter(Store.id == store_id).first()
        if not store:
            abort(404, description="Store not found")
        return jsonify(store_to_dict(store, include_details=True, include_cardnews=True))

# 모든 카드뉴스 리스트 조회
@app.route('/cardnews', methods=['GET'])
def get_cardnews():
    with get_session() as session:
        cards = session.query(CardNews).all()
        result = [
            {
                "store_id": card.store_id,
                "store_name": card.store.name if card.store else "",
                "title": card.title,
                "summary": card.summary,
                "categories": card.store.categories if card.store else [],
                "created_at": card.created_at.strftime("%Y-%m-%d")
            }
            for card in cards
        ]
        return jsonify(result)

# 서버 시작
if __name__ == '__main__':
    load_data.main()          # 초기 CSV/JSON 로딩
    fetch_and_store_ai_data() # AI 서버에서 데이터 가져와 DB 저장
    app.run(debug=True)
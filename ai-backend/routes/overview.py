from flask import Blueprint, jsonify, Response
import json
import requests
from services.openai_service import infer_tags
from utils.prompt_templates import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from config import WEB_BACKEND_URL

bp = Blueprint("overview", __name__)
MOCK_DATA_FILE = "mock_data.json"

@bp.get("/ai/generate_stores")
def generate_stores():
    try:
        with open(MOCK_DATA_FILE, "r", encoding="utf-8") as f:
            stores = json.load(f)
    except Exception as e:
        return jsonify({"error": f"mock_data.json load failed: {str(e)}"}), 500

    result = []

    for store in stores:
        store_result = {
            "store_name": store.get("store_name", ""), 
            "address": store.get("address", "")
            }
        try:
            user_prompt = USER_PROMPT_TEMPLATE.format(
                store_json=json.dumps(store, ensure_ascii=False, indent=2)
            )
            ai_output = infer_tags(SYSTEM_PROMPT, user_prompt)

            store_result.update({
                "categories": ai_output.get("categories", []),
                "positive_news_count": ai_output.get("positive_news_count", 0),
                "positive_sns_count": ai_output.get("positive_sns_count", 0),
                "cardnews": ai_output.get("cardnews", {"title": "", "summary": ""})
            })

            # 웹 백엔드로 전송
            try:
                resp = requests.post(WEB_BACKEND_URL, json=store_result)
                if resp.status_code != 200:
                    print(f"[Warning] Failed to send {store_result['store_name']}: {resp.text}")
            except Exception as e2:
                print(f"[Error] Sending {store_result['store_name']} failed: {str(e2)}")

        except Exception as e:
            store_result["error"] = str(e)

        result.append(store_result)

    return Response(
        json.dumps(result, ensure_ascii=False, indent=2),
        status=200,
        mimetype="application/json; charset=utf-8"
    )
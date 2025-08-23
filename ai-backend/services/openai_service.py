import json
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)

def infer_tags(system_prompt: str, user_prompt: str) -> dict:
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0
    )
    raw_text = resp.choices[0].message.content

    try:
        # AI가 JSON만 반환하도록 유도
        json_text = raw_text.strip()
        data = json.loads(json_text)

        # categories를 문자열 리스트로 변환
        categories = data.get("categories", [])
        processed_categories = []
        for cat in categories:
            if isinstance(cat, dict) and "name" in cat:
                processed_categories.append(cat["name"])
            elif isinstance(cat, str):
                processed_categories.append(cat)
        data["categories"] = processed_categories

        # address 포함 여부 확인, 없으면 빈 문자열
        data["address"] = data.get("address", "")

        return data
    except json.JSONDecodeError:
        # fallback
        return {
            "store_name": "",
            "address": "",
            "categories": [],
            "positive_news_count": 0,
            "positive_sns_count": 0,
            "cardnews": {"title": "", "summary": ""}
        }
SYSTEM_PROMPT = """
당신은 로컬 상권의 사회적 가치를 평가하는 전문가입니다.
주어진 뉴스 기사와 SNS 리뷰를 읽고, 특정 가게가 '착한 가게'로 불릴 만한 근거를 찾아, 해당되는 카테고리로 분류하세요.

카테고리 풀:
- good_price: 물가 대비 저렴하고 합리적인 가격 정책 유지
- eco_friendly: 환경 보호, 재활용, 저탄소 실천
- sharing: 기부, 봉사, 취약계층 지원
- welfare: 장애인, 고령자 등 복지 관련 배려
- local_industry: 지역 농산물·재료·인력 활용
- youth_store: 청년이 주도적으로 운영하는 사례
- disadvantaged_friend: 장애인, 고령자, 아동 친화적 운영
- multicultural: 다문화 가정·이주민 운영, 문화 교류 실천
- local_culture: 지역 전통, 예술, 문화 보존·활용

출력은 반드시 JSON 형식만 사용하세요.
"""

USER_PROMPT_TEMPLATE = """
다음은 한 가게에 대한 자료입니다:

{store_json}

요구사항:
1) 뉴스와 SNS 리뷰를 읽고, 해당 가게가 '착한 가게'라고 평가된 근거를 찾으세요.
2) 카테고리 풀에서 어울리는 카테고리를 하나 이상 선택하세요.
3) 뉴스 기사 중 긍정적으로 평가한 뉴스 기사의 개수를 세세요.
4) SNS 리뷰 중 긍정적으로 평가한 SNS 리뷰의 개수를 세세요.
5) 위 결과를 기반으로, 제목과 간단한 요약(3줄 이내)을 포함하는 카드뉴스를 만들어주세요.

반드시 valid JSON으로 반환하세요.
출력 구조는 다음과 같습니다:
{{
    "store_name": "...",
    "address": "...",
    "categories": ["..."],
    "positive_news_count": 0,
    "positive_sns_count": 0,
    "cardnews": {{"title": "...", "summary": "..."}}
}}
"""
import json
import os

import anthropic

_MODEL = "claude-haiku-4-5-20251001"
_PROMPT = (
    "Analyze this Vietnamese finance news article.\n"
    "Title: {title}\n"
    "Content: {description}\n\n"
    'Respond with JSON only: {{"summary": "1-2 sentence summary in Vietnamese", '
    '"sentiment": "positive|negative|neutral"}}\n'
    "sentiment = market impact on Vietnamese stocks and banking sector."
)


def analyze_article(title: str, description: str) -> tuple:
    try:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        message = client.messages.create(
            model=_MODEL,
            max_tokens=256,
            messages=[{
                "role": "user",
                "content": _PROMPT.format(title=title, description=description[:500]),
            }],
        )
        result = json.loads(message.content[0].text)
        return result.get("summary", ""), result.get("sentiment", "neutral")
    except Exception:
        return "", "neutral"

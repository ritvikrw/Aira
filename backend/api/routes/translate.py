import json
import logging
from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class TranslateRequest(BaseModel):
    texts: List[str]


@router.post("/translate")
async def translate_texts(body: TranslateRequest):
    """Batch-translate a list of strings to English using OpenAI gpt-4o-mini.

    Strings that are already in English (or empty) are returned unchanged.
    On any failure the originals are returned so the UI degrades gracefully.
    """
    from openai import AsyncOpenAI

    texts = body.texts
    if not texts:
        return {"translations": []}

    # Only call OpenAI for non-empty strings
    non_empty_indices = [i for i, t in enumerate(texts) if t and t.strip()]
    if not non_empty_indices:
        return {"translations": texts}

    try:
        oai = AsyncOpenAI()
        texts_to_translate = [texts[i] for i in non_empty_indices]
        batch_json = json.dumps(texts_to_translate, ensure_ascii=False)

        resp = await oai.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            max_tokens=2000,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a translator. Translate each string in the 'texts' array to English. "
                        "Rules:\n"
                        "- Keep proper nouns, personal names, brand names, company names, and phone numbers unchanged.\n"
                        "- If a string is already in English, return it exactly as-is.\n"
                        "- Keep the same tone — conversational, not formal.\n"
                        "- Return valid JSON in this exact format: {\"translations\": [\"...\", \"...\"]}\n"
                        "- The output array must have exactly the same length as the input array."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps({"texts": texts_to_translate}, ensure_ascii=False),
                },
            ],
        )

        data = json.loads(resp.choices[0].message.content)
        translated = data.get("translations", [])

        # Merge translated strings back into the original positions
        result = list(texts)
        for arr_idx, orig_idx in enumerate(non_empty_indices):
            if arr_idx < len(translated):
                result[orig_idx] = translated[arr_idx]

        logger.info("Translated %d strings to English", len(non_empty_indices))
        return {"translations": result}

    except Exception as e:
        logger.error("Translation API error: %s", e)
        # Graceful fallback — return originals
        return {"translations": texts}

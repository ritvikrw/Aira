import logging
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

logger = logging.getLogger(__name__)

CATEGORIES = [
    "Product Enquiry",
    "Support Request",
    "Billing & Pricing",
    "Appointment / Booking",
    "General Information",
    "Complaint",
    "Other",
]

_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY", ""),
    temperature=0,
)

_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a call summarization assistant. Given a phone call transcript between a caller (USER) and an AI receptionist (AGENT), produce a concise JSON summary.

Return ONLY valid JSON with this structure:
{{
  "summary_text": "2-4 sentence overview of the entire call",
  "call_category": "<one of the categories below>",
  "key_topics": ["topic1", "topic2"],
  "action_items": ["action1", "action2"]
}}

Rules:
- summary_text: what the caller wanted and how it was resolved
- call_category: pick exactly one from this list — {categories}
  - "Product Enquiry": caller asked about a product, service, feature, pricing, or requested a demo
  - "Support Request": caller needs help with a problem, issue, or technical matter
  - "Billing & Pricing": questions about invoices, payments, costs, or subscriptions
  - "Appointment / Booking": caller wants to schedule, reschedule, or cancel a meeting or visit
  - "General Information": asking about company hours, location, contact details, or background
  - "Complaint": caller is unhappy, raising a complaint, or expressing dissatisfaction
  - "Other": anything that doesn't fit the above
- key_topics: specific subjects discussed (max 5, concise short phrases). NEVER include caller names, agent names, or phone/contact numbers — only business topics and intents.
- action_items: any follow-ups needed (empty list if none)"""),
    ("human", "Transcript:\n\n{transcript}"),
])

_chain = _prompt | _llm | JsonOutputParser()


async def summarize_call(transcripts: list[dict]) -> dict:
    if not transcripts:
        return {"summary_text": "No transcript available.", "call_category": "Other", "key_topics": [], "action_items": []}

    lines = [f"{t['speaker'].upper()}: {t['message']}" for t in transcripts]
    transcript_text = "\n".join(lines)

    try:
        result = await _chain.ainvoke({"transcript": transcript_text, "categories": ", ".join(f'"{c}"' for c in CATEGORIES)})
        if result.get("call_category") not in CATEGORIES:
            result["call_category"] = "Other"
        return result
    except Exception as e:
        logger.error("Summarization failed: %s", e)
        return {"summary_text": "Summarization failed.", "call_category": "Other", "key_topics": [], "action_items": []}

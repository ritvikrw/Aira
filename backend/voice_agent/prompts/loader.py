from .base import build_base_prompt
from . import en_IN, hi_IN, ta_IN, te_IN, kn_IN, ml_IN, mr_IN, bn_IN, gu_IN, pa_IN

_LANGUAGE_MODULES = {
    "en-IN": en_IN,
    "hi-IN": hi_IN,
    "ta-IN": ta_IN,
    "te-IN": te_IN,
    "kn-IN": kn_IN,
    "ml-IN": ml_IN,
    "mr-IN": mr_IN,
    "bn-IN": bn_IN,
    "gu-IN": gu_IN,
    "pa-IN": pa_IN,
}

LANGUAGE_NAMES = {code: mod.LANGUAGE_NAME for code, mod in _LANGUAGE_MODULES.items()}


def build_prompt(
    agent_name: str,
    org_name: str,
    language: str = "en-IN",
    org_description: str = "",
    instructions: str = "",
) -> str:
    base = build_base_prompt(
        agent_name=agent_name,
        org_name=org_name,
        org_description=org_description,
        instructions=instructions,
    )
    lang_module = _LANGUAGE_MODULES.get(language, en_IN)
    return f"{base}\n\n{lang_module.PROMPT}"

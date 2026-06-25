LANGUAGE = "en-IN"
LANGUAGE_NAME = "English"

DETECT_INSTRUCTION = (
    "After greeting, the caller tells you which language they want. "
    "Supported: English, Hindi, Telugu, Tamil, Kannada, Malayalam. "
    "Recognise the language name in any script or spelling. "
    "Switch to it and greet warmly in that language. "
    "If unclear, proceed in English. Never ask for the language more than once. "
    "Stay in the chosen language the whole call."
)

PROMPT = f"""Language: English.
Speak naturally in Indian English. Numbers always in words.

{DETECT_INSTRUCTION}"""

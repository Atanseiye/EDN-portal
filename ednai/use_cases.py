from __future__ import annotations

from typing import Any

LANGUAGES = {
    "english": "English / Nigerian English",
    "yoruba": "Yorùbá",
    "hausa": "Hausa",
    "igbo": "Igbo",
}


def _field(
    name: str,
    label: str,
    *,
    kind: str = "textarea",
    required: bool = True,
    placeholder: str = "",
    options: list[dict[str, str]] | None = None,
    default: str = "",
    help_text: str = "",
) -> dict[str, Any]:
    return {
        "name": name,
        "label": label,
        "type": kind,
        "required": required,
        "placeholder": placeholder,
        "options": options or [],
        "default": default,
        "help": help_text,
    }


_LANGUAGE_OPTIONS = [
    {"value": key, "label": label}
    for key, label in LANGUAGES.items()
]


USE_CASES: dict[str, dict[str, Any]] = {
    "chatbot": {
        "title": "Multilingual Chatbot",
        "icon": "CHAT",
        "description": "Build conversational assistants that respond naturally in supported Nigerian languages.",
        "output_label": "Assistant response",
        "temperature": 0.35,
        "max_tokens": 500,
        "fields": [
            _field(
                "message",
                "User message",
                placeholder="Ask the assistant something…",
            ),
            _field(
                "persona",
                "Assistant role",
                kind="input",
                required=False,
                placeholder="e.g. customer-support assistant",
            ),
            _field(
                "context",
                "Optional application context",
                required=False,
                placeholder="Add product, organisation or domain context the assistant should use.",
            ),
        ],
    },
    "translation": {
        "title": "Content Translation",
        "icon": "TR",
        "description": "Translate content between English, Yorùbá, Hausa and Igbo while preserving meaning and structure.",
        "output_label": "Translation",
        "temperature": 0.1,
        "max_tokens": 700,
        "fields": [
            _field(
                "source_language",
                "Source language",
                kind="select",
                options=_LANGUAGE_OPTIONS,
                default="english",
            ),
            _field(
                "target_language",
                "Target language",
                kind="select",
                options=_LANGUAGE_OPTIONS,
                default="yoruba",
            ),
            _field(
                "text",
                "Content to translate",
                placeholder="Paste the source content here.",
            ),
            _field(
                "notes",
                "Translation notes",
                required=False,
                placeholder="e.g. preserve technical terms; use simple vocabulary",
            ),
        ],
    },
    "education": {
        "title": "Educational Tools",
        "icon": "EDU",
        "description": "Generate explanations, lessons and practice material in local languages.",
        "output_label": "Learning material",
        "temperature": 0.3,
        "max_tokens": 900,
        "fields": [
            _field(
                "topic",
                "Topic",
                kind="input",
                placeholder="e.g. Photosynthesis",
            ),
            _field(
                "learner_level",
                "Learner level",
                kind="input",
                placeholder="e.g. JSS 2 / beginner",
            ),
            _field(
                "objective",
                "Learning objective",
                placeholder="What should the learner understand or be able to do?",
            ),
            _field(
                "format",
                "Material format",
                kind="select",
                options=[
                    {"value": "lesson", "label": "Short lesson"},
                    {"value": "study_notes", "label": "Study notes"},
                    {"value": "quiz", "label": "Quiz + answers"},
                    {"value": "lesson_quiz", "label": "Lesson + mini quiz"},
                ],
                default="lesson_quiz",
            ),
        ],
    },
    "culture": {
        "title": "Cultural Preservation",
        "icon": "CULT",
        "description": "Document oral history, expressions, proverbs and linguistic knowledge without inventing missing facts.",
        "output_label": "Preservation record",
        "temperature": 0.2,
        "max_tokens": 900,
        "fields": [
            _field(
                "material",
                "Source material",
                placeholder="Enter the proverb, oral-history excerpt, expression or cultural text.",
            ),
            _field(
                "material_type",
                "Material type",
                kind="select",
                options=[
                    {"value": "proverb", "label": "Proverb / saying"},
                    {"value": "oral_history", "label": "Oral history"},
                    {"value": "expression", "label": "Expression / phrase"},
                    {"value": "story", "label": "Story / narrative"},
                    {"value": "language_note", "label": "Language note"},
                ],
                default="proverb",
            ),
            _field(
                "known_context",
                "Known context",
                required=False,
                placeholder="Who uses it, where it was recorded, known meaning, speaker notes, etc.",
            ),
        ],
    },
    "government": {
        "title": "Government Services",
        "icon": "GOV",
        "description": "Turn supplied public-service information into clear local-language guidance for citizens.",
        "output_label": "Citizen guidance",
        "temperature": 0.15,
        "max_tokens": 800,
        "fields": [
            _field(
                "service",
                "Service or process",
                kind="input",
                placeholder="e.g. applying for a public document",
            ),
            _field(
                "question",
                "Citizen question",
                placeholder="What does the citizen need help understanding?",
            ),
            _field(
                "official_context",
                "Authoritative context",
                required=False,
                placeholder="Paste official instructions, eligibility rules or process text here.",
                help_text="Specific requirements should be grounded in authoritative material supplied to the model.",
            ),
        ],
    },
    "digital_inclusion": {
        "title": "Digital Inclusion",
        "icon": "ACCESS",
        "description": "Rewrite complex digital information into clear, accessible local-language guidance.",
        "output_label": "Accessible version",
        "temperature": 0.2,
        "max_tokens": 650,
        "fields": [
            _field(
                "content",
                "Content to simplify",
                placeholder="Paste technical, financial, service or digital instructions.",
            ),
            _field(
                "audience",
                "Audience",
                kind="input",
                placeholder="e.g. first-time smartphone user",
            ),
            _field(
                "channel",
                "Delivery channel",
                kind="select",
                options=[
                    {"value": "mobile", "label": "Mobile app"},
                    {"value": "whatsapp", "label": "WhatsApp / messaging"},
                    {"value": "sms", "label": "SMS"},
                    {"value": "web", "label": "Website"},
                    {"value": "print", "label": "Print / offline"},
                ],
                default="mobile",
            ),
        ],
    },
    "research": {
        "title": "Research Applications",
        "icon": "R&D",
        "description": "Summarise, classify and analyse Nigerian-language research material with evidence separated from inference.",
        "output_label": "Research analysis",
        "temperature": 0.15,
        "max_tokens": 1000,
        "fields": [
            _field(
                "task",
                "Research task",
                kind="select",
                options=[
                    {"value": "summarize", "label": "Summarise"},
                    {"value": "analyze", "label": "Analyse"},
                    {"value": "classify", "label": "Classify"},
                    {"value": "extract", "label": "Extract findings"},
                    {"value": "compare", "label": "Compare evidence"},
                ],
                default="analyze",
            ),
            _field(
                "question",
                "Research question",
                placeholder="What should N-ATLaS investigate in the material?",
            ),
            _field(
                "material",
                "Research material",
                placeholder="Paste notes, transcripts, labelled excerpts or other source material.",
            ),
        ],
    },
    "song": {
        "title": "Song Generation",
        "icon": "SONG",
        "description": "Generate original song lyrics in a supported language. This is text generation, not audio synthesis.",
        "output_label": "Original lyrics",
        "temperature": 0.65,
        "max_tokens": 900,
        "fields": [
            _field(
                "theme",
                "Theme",
                kind="input",
                placeholder="e.g. hope, community, education",
            ),
            _field(
                "mood",
                "Mood",
                kind="input",
                placeholder="e.g. uplifting, reflective, playful",
            ),
            _field(
                "structure",
                "Song structure",
                kind="select",
                options=[
                    {"value": "verse_chorus", "label": "Verse + chorus"},
                    {"value": "two_verses_chorus", "label": "2 verses + chorus"},
                    {"value": "verse_chorus_bridge", "label": "Verse + chorus + bridge"},
                ],
                default="two_verses_chorus",
            ),
            _field(
                "details",
                "Additional details",
                required=False,
                placeholder="Audience, setting, key phrases or ideas to include.",
            ),
        ],
    },
}


def normalize_language(language: str) -> str:
    key = str(language).strip().lower()
    aliases = {
        "en": "english",
        "en-ng": "english",
        "english": "english",
        "nigerian english": "english",
        "yo": "yoruba",
        "yor": "yoruba",
        "yoruba": "yoruba",
        "ha": "hausa",
        "hau": "hausa",
        "hausa": "hausa",
        "ig": "igbo",
        "ibo": "igbo",
        "igbo": "igbo",
    }
    if key not in aliases:
        raise ValueError(
            "Unsupported language. Choose english, yoruba, hausa or igbo."
        )
    return aliases[key]


def public_use_case_registry() -> dict[str, Any]:
    return {
        "languages": LANGUAGES,
        "use_cases": {
            slug: {
                key: value
                for key, value in definition.items()
                if key not in {"system"}
            }
            for slug, definition in USE_CASES.items()
        },
    }


def _require_inputs(slug: str, inputs: dict[str, Any]) -> dict[str, str]:
    definition = USE_CASES[slug]
    cleaned = {
        str(key): str(value).strip()
        for key, value in inputs.items()
        if value is not None and str(value).strip()
    }
    missing = [
        field["name"]
        for field in definition["fields"]
        if field["required"] and field["name"] not in cleaned
    ]
    if missing:
        raise ValueError(
            f"Missing required inputs for {slug}: {', '.join(missing)}"
        )
    return cleaned


def build_use_case_prompt(
    slug: str,
    language: str,
    inputs: dict[str, Any],
) -> tuple[str, str, str]:
    if slug not in USE_CASES:
        raise KeyError(slug)

    language = normalize_language(language)
    output_language = language
    data = _require_inputs(slug, inputs)

    common = (
        "You are NCAIR1/N-ATLaS running inside EDNAi. "
        "Use the requested Nigerian language naturally and preserve names, numbers "
        "and important domain terms. Do not pretend that another model generated "
        "the response. "
    )

    if slug == "chatbot":
        role = data.get("persona", "helpful multilingual assistant")
        context = data.get("context", "")
        system = (
            common
            + f"Act as a {role}. Respond in {LANGUAGES[language]}. "
            "Be conversational, direct and useful. Do not invent application-specific "
            "facts that were not supplied."
        )
        user = data["message"]
        if context:
            user = f"Application context:\n{context}\n\nUser message:\n{user}"

    elif slug == "translation":
        source = normalize_language(data["source_language"])
        target = normalize_language(data["target_language"])
        output_language = target
        notes = data.get("notes", "")
        system = (
            common
            + f"Translate faithfully from {LANGUAGES[source]} to {LANGUAGES[target]}. "
            "Preserve meaning, names, numbers, paragraph structure and technical terms. "
            "Do not add explanations unless the translation notes request them."
        )
        user = f"Text to translate:\n{data['text']}"
        if notes:
            user += f"\n\nTranslation notes:\n{notes}"

    elif slug == "education":
        system = (
            common
            + f"Create accurate learning material in {LANGUAGES[language]}. "
            "Match the stated learner level. Explain concepts step by step, use a "
            "practical example, and avoid claiming uncertain facts."
        )
        user = (
            f"Topic: {data['topic']}\n"
            f"Learner level: {data['learner_level']}\n"
            f"Learning objective: {data['objective']}\n"
            f"Requested format: {data['format']}"
        )

    elif slug == "culture":
        system = (
            common
            + f"Help document cultural and linguistic material in {LANGUAGES[language]}. "
            "Preserve original wording and culturally specific terms. Clearly separate "
            "the supplied material from interpretation. Never invent undocumented "
            "origins, meanings, customs or historical claims; mark uncertainty."
        )
        user = (
            f"Material type: {data['material_type']}\n"
            f"Source material:\n{data['material']}"
        )
        if data.get("known_context"):
            user += f"\n\nKnown context:\n{data['known_context']}"

    elif slug == "government":
        system = (
            common
            + f"Explain public-service information neutrally in {LANGUAGES[language]}. "
            "Use supplied authoritative context for specific eligibility, fees, dates, "
            "documents or procedures. If authoritative context is missing, give only "
            "general navigation guidance and identify what the user should verify with "
            "the responsible agency. Do not impersonate a government office."
        )
        user = (
            f"Service/process: {data['service']}\n"
            f"Citizen question: {data['question']}"
        )
        if data.get("official_context"):
            user += f"\n\nAuthoritative context:\n{data['official_context']}"

    elif slug == "digital_inclusion":
        system = (
            common
            + f"Rewrite information in accessible {LANGUAGES[language]}. "
            "Use short sentences, concrete steps, familiar wording and an inclusive tone. "
            "Preserve safety warnings, money amounts, dates, numbers and essential conditions."
        )
        user = (
            f"Audience: {data['audience']}\n"
            f"Delivery channel: {data['channel']}\n"
            f"Content to simplify:\n{data['content']}"
        )

    elif slug == "research":
        system = (
            common
            + f"Support research analysis in {LANGUAGES[language]}. "
            "Base conclusions only on supplied material. Separate evidence, inference "
            "and uncertainty. Preserve source labels when present and never fabricate "
            "citations, studies, statistics or references."
        )
        user = (
            f"Task: {data['task']}\n"
            f"Research question: {data['question']}\n"
            f"Research material:\n{data['material']}"
        )

    elif slug == "song":
        system = (
            common
            + f"Write original song lyrics in {LANGUAGES[language]}. "
            "Create new wording rather than reproducing existing lyrics or imitating "
            "a named living artist. This is text-only lyric generation, not audio synthesis. "
            "Use clear section labels such as Verse, Chorus and Bridge where appropriate."
        )
        user = (
            f"Theme: {data['theme']}\n"
            f"Mood: {data['mood']}\n"
            f"Structure: {data['structure']}"
        )
        if data.get("details"):
            user += f"\nAdditional details: {data['details']}"

    else:
        raise KeyError(slug)

    return system, user, output_language

"""Gemini-authored writing guidance used by the prompt builder.

The guidance text in this module was generated with Gemini 3.1 Pro High for
the Gemini Writing Copilot plugin, then committed as static defaults so the
plugin can build prompts deterministically.
"""

from __future__ import annotations

TASK_LABELS = {
    "auto": "auto",
    "draft": "draft",
    "rewrite": "rewrite",
    "polish": "polish",
    "summarize": "summarize",
    "translate": "translate",
    "outline": "outline",
    "custom": "custom",
    "email": "email",
    "announcement": "announcement",
    "blog": "blog",
    "pr-description": "pr-description",
    "release-notes": "release-notes",
    "readme": "readme",
    "proposal": "proposal",
    "product-copy": "product-copy",
    "technical-doc": "technical-doc",
}

TASK_GUIDANCE = {
    "draft": [
        "Generate a complete first pass based on the provided inputs.",
        "Focus on structure and getting the core ideas down clearly.",
        "Leave placeholders in square brackets for missing information.",
    ],
    "rewrite": [
        "Transform the input text significantly while retaining its original meaning.",
        "Adjust the tone, style, and vocabulary to match the target profile.",
        "Ensure the new version flows naturally and improves readability.",
    ],
    "polish": [
        "Refine the existing text for clarity, grammar, and flow.",
        "Correct minor errors without changing the core sentence structures.",
        "Ensure consistent terminology and tone throughout the piece.",
    ],
    "summarize": [
        "Extract the main points and key takeaways from the source text.",
        "Condense the information into a brief format.",
        "Omit minor details and redundant examples.",
    ],
    "translate": [
        "Convert the source text into the target language accurately.",
        "Avoid literal translations that sound unnatural in the target language.",
        "Maintain the original formatting and factual claims.",
    ],
    "outline": [
        "Create a structured hierarchy of topics for the given subject.",
        "Use bullet points or numbered lists to denote sections.",
        "Ensure logical flow from introduction to conclusion.",
    ],
    "custom": [
        "Follow the user's specific custom instructions exactly.",
        "Apply the requested constraints and formatting rules.",
        "Prioritize explicit user guidance over default behaviors.",
    ],
    "email": [
        "Draft a clear and focused email with an appropriate subject line.",
        "State the purpose of the email early in the body.",
        "Conclude with a clear call to action or next steps.",
    ],
    "announcement": [
        "Highlight the most important news immediately.",
        "Provide necessary context and explain the impact on the audience.",
        "Keep the tone engaging but professional.",
    ],
    "blog": [
        "Write an engaging post tailored to the target audience.",
        "Use clear headings and formatting for readability.",
        "Include a compelling introduction and a strong conclusion.",
    ],
    "pr-description": [
        "Summarize the changes made in the pull request clearly.",
        "Explain the motivation behind the changes and the problem solved.",
        "List any relevant issue numbers or testing instructions.",
    ],
    "release-notes": [
        "List new features, bug fixes, and breaking changes clearly.",
        "Group items logically using standard categories.",
        "Keep descriptions concise and focused on user impact.",
    ],
    "readme": [
        "Provide a clear overview of the project and its purpose.",
        "Include essential sections like installation, usage, and configuration.",
        "Use clear formatting and code blocks for examples.",
    ],
    "proposal": [
        "Outline the problem, proposed solution, and expected benefits.",
        "Provide a clear timeline, resource requirements, or next steps.",
        "Maintain a persuasive yet objective and factual tone.",
    ],
    "product-copy": [
        "Highlight the benefits and value proposition of the product.",
        "Use active voice and persuasive language.",
        "Keep sentences punchy and avoid technical jargon.",
    ],
    "technical-doc": [
        "Explain technical concepts precisely and unambiguously.",
        "Use consistent terminology and provide clear examples.",
        "Structure the document logically for easy navigation.",
    ],
}

GENERAL_WRITING_GUIDANCE = [
    "Return only the requested writing without meta-commentary.",
    "Preserve all factual claims, metrics, dates, and names from the source.",
    "Use specific nouns and verbs while avoiding empty intensifiers.",
    "Write for the specified audience and purpose before optimizing for cleverness.",
    "Keep the language of the source unless a target language or translation task says otherwise.",
    "For Korean writing, prefer natural modern Korean with clean sentence endings and no translationese.",
    "Make paragraph breaks intentional.",
    "Ensure each paragraph moves the reader forward.",
    "Choose the most fitting writing form for the task.",
]

OUTPUT_MODE_GUIDANCE = {
    "final": "Output only the finalized text without preamble or commentary.",
    "alternatives": "Provide the final text followed by distinct alternative phrasings.",
    "edit-with-notes": "Return the revised text followed by concise notes explaining key changes.",
    "diff-summary": "Output a concise list of modifications made to the original text without returning the full revised text.",
}

PRESERVE_VOICE_GUIDANCE = {
    "off": "Optimize strictly for the target style, discarding the source voice.",
    "light": "Retain key vocabulary while standardizing phrasing and tone.",
    "medium": "Preserve the author's distinctive tone and vocabulary. Standardize only jarring awkwardness.",
    "strong": "Strictly maintain the original voice, cadence, and stylistic quirks.",
}

STRUCTURE_MODE_GUIDANCE = {
    "preserve": "Maintain existing paragraph boundaries and logical sequencing exactly.",
    "allow-restructure": "Modify sentence order and paragraph breaks if necessary for clarity.",
    "restructure": "Reorganize the text entirely to establish an optimal logical flow.",
}

REWRITE_STRENGTH_GUIDANCE = {
    "light": "Correct grammar and spelling while preserving sentence structure.",
    "medium": "Rephrase sentences for better clarity and impact while keeping the overall structure.",
    "heavy": "Completely restructure paragraphs and sentences to adopt a new tone or style.",
}

CODEX_REVIEW_CHECKLIST = [
    "Does the output follow the requested format strictly?",
    "Are all factual claims from the source preserved?",
    "Is the tone appropriate for the selected profile?",
    "Are there any missing placeholders that need user attention?",
    "Is the text free of conversational filler?",
]

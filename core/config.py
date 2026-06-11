"""Core configuration for requirement extraction and classification."""

from __future__ import annotations

from typing import Final, List

PROMPT_EXTRACT: Final[str] = """
You are an expert in software requirements engineering.

Extract ONLY VALID and ATOMIC software requirements.

STRICT RULES:
- A requirement MUST describe a SINGLE system behavior or constraint
- DO NOT include definitions, explanations, or descriptive text
- DO NOT include introductions, glossaries, or background information
- DO NOT merge multiple sentences into one requirement
- SPLIT long paragraphs into separate requirements
- IGNORE sections like:
  introduction, definitions, overview, tables, examples

VALID REQUIREMENTS MUST:
- contain an action (shall, must, should, allow, provide)
- be a COMPLETE sentence
- describe system behavior, function, or constraint

REJECT:
- definitions (e.g., "A system is...")
- descriptions (e.g., "This section describes...")
- lists or bullet explanations

FORMAT (STRICT):
Global_ID|requirement text|Type

IMPORTANT:
- One requirement per line
- MAX 200 characters per requirement
- If Type is unclear → UNK
- NO explanations
- NO extra text

EXAMPLES:
REQ_001|The system shall support group voice calls|UNK
REQ_002|The system must allow emergency calls|UNK
REQ_003|The system shall provide call prioritization|UNK
"""
PROMPT_CLASS: Final[str] = """
You are a STRICT software requirements classifier aligned with ISO standards.

TASK:
Classify each requirement line.

INPUT FORMAT (each line):
Global_ID|Text|Type

OUTPUT FORMAT (STRICT, exactly 1 line per input line):
Global_ID|Text|Type|Subclass

RULES:
- Keep Global_ID EXACTLY as input.
- NEVER change Text.
- NEVER change ordering.
- NEVER skip lines.
- NEVER invent IDs.
- Output MUST match input order.
- Do not add explanations or extra text.
- Do not put spaces around the '|' separators.

Type MUST be EXACTLY:
FR or NFR

Subclass rules:
- If Type = FR  → Subclass = Functional
- If Type = NFR → choose EXACTLY ONE of:
Performance, Usability, Reliability, Security, Maintainability, Compatibility, Portability

DECISION RULES (MANDATORY):
1) FR:
- If the requirement describes system behavior, features, or services
- Keywords: "shall support", "shall allow", "shall provide", "user can"
→ Type=FR, Subclass=Functional

2) Security (NFR):
- If it involves: authentication, authorization, privacy, encryption, integrity,
  credentials, firewall, access control, replay protection
→ Type=NFR, Subclass=Security

3) Performance (NFR):
- ONLY if explicitly about: latency, response time, throughput, bandwidth, QoS, scalability
→ Type=NFR, Subclass=Performance

4) Usability:
- ease of use, UI, UX, interaction
→ Type=NFR, Subclass=Usability

5) Reliability:
- failures, recovery, availability, fault tolerance
→ Type=NFR, Subclass=Reliability

6) Compatibility:
- interoperability, cross-platform, different systems/browsers
→ Type=NFR, Subclass=Compatibility

7) Maintainability:
- updates, modification, maintainability
→ Type=NFR, Subclass=Maintainability

8) Portability:
- deployment across environments/platforms
→ Type=NFR, Subclass=Portability

ANTI-BIAS:
- NEVER default to Performance.
- Performance MUST be explicitly stated.
- If security-related → ALWAYS Security.
- If system behavior → ALWAYS Functional.
"""

VALID_REQUIREMENT_TYPES: Final[List[str]] = ["FR", "NFR", "UNK"]
VALID_SUBCLASSES: Final[List[str]] = [
    "Functional",
    "Performance",
    "Usability",
    "Reliability",
    "Security",
    "Maintainability",
    "Compatibility",
    "Portability",
]

DEFAULT_REQUIREMENT_TYPE: Final[str] = "UNK"
DEFAULT_SUBCLASS: Final[str] = "Functional"


def build_extract_prompt(text: str) -> str:
    """Build a complete extraction prompt from raw input text."""
    return f"{PROMPT_EXTRACT}\n\nINPUT:\n{text.strip()}".strip()


def build_classification_prompt(requirements: str) -> str:
    """Build a complete classification prompt for requirement lines."""
    return f"{PROMPT_CLASS}\n\nINPUT:\n{requirements.strip()}".strip()
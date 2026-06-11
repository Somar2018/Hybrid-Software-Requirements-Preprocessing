"""Core configuration for requirement extraction and classification."""

from __future__ import annotations
from typing import Final, List

PROMPT_EXTRACT: Final[str] = """
You are an expert in software requirements engineering.

Extract ALL possible software requirements from the text.

IMPORTANT RULES:
- Do NOT miss any requirement.
- Include implicit requirements.
- Include short requirements.
- A requirement is ANY sentence describing system behavior, constraints, or features.
- Ignore titles, headers, tables, and metadata.
- Do not invent requirements.

Include:
- functional requirements
- non-functional requirements
- user interface requirements
- constraints

Return one requirement per line.

Preferred format:
ID | requirement text | type

If unsure:
- still return the requirement
- type = UNK

Examples:
REQ_001 | The system shall allow users to login | UNK
REQ_002 | The system must respond within 2 seconds | NFR
REQ_003 | Users can search for books | FR
"""

PROMPT_CLASS: Final[str] = """
You are a STRICT software requirements classifier aligned with ISO standards.

TASK:
Classify each requirement.

INPUT FORMAT:
Global_ID|Text

OUTPUT FORMAT (STRICT):
Global_ID|Text|Type|Subclass

RULES:
- Keep Global_ID EXACTLY as input.
- NEVER change Text.
- NEVER skip lines.
- NEVER invent IDs.
- Output MUST match input order.

Type MUST be:
- FR
- NFR

Subclass rules:
- If FR → Subclass = Functional
- If NFR → choose EXACTLY ONE:
  - Performance
  - Usability
  - Reliability
  - Security
  - Maintainability
  - Compatibility
  - Portability

--------------------------------------------------
DECISION RULES (MANDATORY):
--------------------------------------------------

1. Functional (FR):
- If the requirement describes system behavior, features, or services
- Keywords:
  "shall support", "shall allow", "shall provide", "user can"
→ CLASSIFY AS: FR | Functional

2. Security (NFR):
- If requirement involves:
  authentication, authorization, privacy, encryption, integrity,
  credentials, firewall, access control, replay protection
→ CLASSIFY AS: NFR | Security

3. Performance (NFR):
- ONLY if explicitly about:
  latency, response time, throughput, bandwidth, QoS, scalability
→ CLASSIFY AS: NFR | Performance

4. Usability:
- ease of use, UI, UX, interaction

5. Reliability:
- failures, recovery, availability, fault tolerance

6. Compatibility:
- interoperability, cross-platform, different systems/browsers

7. Maintainability:
- updates, modification, maintainability

8. Portability:
- deployment across environments/platforms

--------------------------------------------------
CRITICAL ANTI-BIAS RULES:
--------------------------------------------------

- NEVER default to Performance
- Performance MUST be explicitly stated
- If security-related → ALWAYS Security
- If system behavior → ALWAYS Functional

--------------------------------------------------
VALIDATION RULES:
--------------------------------------------------

- Each output line MUST contain exactly 4 fields separated by "|"
- Do not add explanations or extra text
- Do not change wording

--------------------------------------------------
EXAMPLES:
--------------------------------------------------

REQ_00001|System shall store user data|FR|Functional
REQ_00002|System must respond within 2 seconds|NFR|Performance
REQ_00003|System shall authenticate users|NFR|Security
REQ_00004|System shall support file upload|FR|Functional
REQ_00005|System shall ensure data integrity|NFR|Security
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
    return f"{PROMPT_CLASS}\n\n{requirements.strip()}".strip()

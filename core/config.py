"""Core configuration for requirement extraction and classification."""

from __future__ import annotations

from typing import Final, List

PROMPT_EXTRACT = """
You are an expert in Software Requirements Engineering (ISO/IEC/IEEE 29148).

Your task is to EXTRACT ONLY REAL SOFTWARE REQUIREMENTS from the text below.

A REAL REQUIREMENT must satisfy ALL of the following:

1. It describes a system behavior, capability, constraint or function.
2. It contains a clear ACTION VERB (shall, must, should, allow, enable, provide, support, manage, track, create, define).
3. It is complete, testable, unambiguous and self‑contained.
4. It is NOT a title, section header, description, motivation, context, introduction, explanation or background text.
5. It is NOT truncated, incomplete, or ending with ":" or ",".
6. It is NOT describing the document itself (e.g., “This specification describes…”).
7. It is NOT describing the organization, market, problem or context.
8. It MUST be a requirement that the system must satisfy — not a justification, not a goal, not a description.

STRICT FILTERING RULES:
- Reject any sentence that starts with: Software Specification, General Description, Introduction, Overview, Purpose, Scope, This document, This specification.
- Reject any sentence that contains: is an integrated solution, provides an initial foundation, organizations face, as companies grow, promoting team collaboration.
- Reject any sentence that does NOT contain an action verb.
- Reject any sentence that is not testable.

OUTPUT FORMAT (mandatory):
One requirement per line, in the format:

REQ001 | REQUIREMENT_TEXT | FR

Where:
- REQ001 is a sequential placeholder ID
- REQUIREMENT_TEXT is the cleaned requirement
- FR is always “FR”

DO NOT invent requirements.
DO NOT rewrite text.
DO NOT complete missing information.
DO NOT include anything that is not a requirement.

Extract requirements ONLY from the following text:
---
{{TEXT}}
---
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
- authentication, authorization, privacy, encryption, integrity,
  credentials, firewall, access control, replay protection

3) Performance (NFR):
- latency, response time, throughput, bandwidth, QoS, scalability

4) Usability:
- ease of use, UI, UX, interaction

5) Reliability:
- failures, recovery, availability, fault tolerance

6) Compatibility:
- interoperability, cross-platform, different systems/browsers

7) Maintainability:
- updates, modification, maintainability

8) Portability:
- deployment across environments/platforms

ANTI-BIAS:
- NEVER default to Performance.
- Performance MUST be explicitly stated.
- If security-related → ALWAYS Security.
- If system behavior → ALWAYS Functional.
"""

VALID_REQUIREMENT_TYPES: Final[List[str]] = ["FR", "NFR", "UNK"]
VALID_SUBCLASSES = {
    "Functional",
    "Performance",
    "Security",
    "Usability",
    "Reliability",
    "Availability",
    "Scalability",
    "Maintainability",
    "Portability"
}

# =========================
# CONFIG GLOBAL
# =========================

BATCH_SIZE = 10

# Classes principais
VALID_CLASSES = {"FR", "NFR"}

# Subclasses detalhadas
VALID_SUBCLASSES = {
    "Functional",
    "Performance",
    "Security",
    "Usability",
    "Reliability",
    "Availability",
    "Scalability",
    "Maintainability",
    "Portability",
}

# Defaults
DEFAULT_CLASS = "NFR"
DEFAULT_SUB = "Unknown"

# Output
OUTPUT_COLUMNS = ["id", "text", "class", "subclass","confidence"]

def build_extract_prompt(text: str) -> str:
    return f"{PROMPT_EXTRACT}\n\nINPUT:\n{text.strip()}".strip()


def build_classification_prompt(requirements: str) -> str:
    return f"{PROMPT_CLASS}\n\nINPUT:\n{requirements.strip()}".strip()

FREE_DETECT = {
    # Performance
    "latency": "Performance",
    "respond": "Performance",
    "response": "Performance",
    "fast": "Performance",
    "quick": "Performance",
    "seconds": "Performance",
    "simultaneous": "Performance",
    "concurrent": "Performance",
    "scalab": "Performance",
    "load": "Performance",
    "throughput": "Performance",

    # Usability
    "readable": "Usability",
    "understandable": "Usability",
    "intuitive": "Usability",
    "easy": "Usability",
    "learn": "Usability",
    "screen": "Usability",
    "projection": "Usability",
    "color": "Usability",
    "ui": "Usability",
    "ux": "Usability",

    # Security
    "auth": "Security",
    "encrypt": "Security",
    "access": "Security",
    "unauthorized": "Security",
    "malicious": "Security",
    "attack": "Security",
    "privacy": "Security",
    "virus": "Security",
    "role": "Security",
    "permission": "Security",

    # Reliability
    "availability": "Reliability",
    "uptime": "Reliability",
    "fail": "Reliability",
    "recover": "Reliability",
    "downtime": "Reliability",
    "99%": "Reliability",

    # Maintainability
    "update": "Maintainability",
    "modify": "Maintainability",
    "maintenance": "Maintainability",
    "support": "Maintainability",
    "configuration": "Maintainability",

    # Compatibility
    "browser": "Compatibility",
    "interoper": "Compatibility",
    "integration": "Compatibility",
    "api": "Compatibility",
    "ie ": "Compatibility",
    "firefox": "Compatibility",
    "chrome": "Compatibility",

    # Portability
    "platform": "Portability",
    "environment": "Portability",
    "install": "Portability",
    "hardware": "Portability",
    "operation": "Portability",
    "linux": "Portability",
    "windows": "Portability",
}

ISO_MAP = {
    "Functional": "Functional",
    "Performance": "Performance",
    "Usability": "Usability",
    "Security": "Security",
    "Reliability": "Reliability",
    "Maintainability": "Maintainability",
    "Compatibility": "Compatibility",
    "Portability": "Portability",
}

ISO_25010_MAISO_25010_MAP = {

    "Performance": [
        "response time", "latency", "throughput",
        "seconds", "performance", "load",
        "memory", "storage", "mb", "cpu"
    ],

    "Reliability": [
        "reliability", "fault tolerance", "failure",
        "recover", "backup", "restore"
    ],

    "Availability": [
        "availability", "uptime", "% of time", "available"
    ],

    "Security": [
        "authentication", "authorization", "access control",
        "password", "encryption", "privacy"
    ],

    "Usability": [
        "user-friendly", "easy to use", "interface",
        "ux", "ui", "usable"
    ],

    "Compatibility": [
        "interoperability", "integration", "api",
        "browser", "cross-platform"
    ],

    "Maintainability": [
        "maintain", "maintenance", "modification",
        "configuration", "update"
    ],

    "Portability": [
        "portability", "platform", "environment",
        "installation", "deploy", "os"
    ],
}



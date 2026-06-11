# =========================================================
# myutils/text.py - Text Processing & Requirement Extraction
# ✅ ISO 25010 Compliant | Type-Safe | Well-Documented
# =========================================================

import re
import logging
from typing import List, Dict, Tuple, Optional, Set
import pdfplumber
import pandas as pd

# =========================================================
# 📋 LOGGING CONFIGURATION
# =========================================================
logger = logging.getLogger(__name__)

# =========================================================
# ⚙️ REGEX PATTERNS (Constants)
# =========================================================
PATTERN_HEADER = r"Software Requirements Specification.*"
PATTERN_PAGE = r"Page\s+\d+"
PATTERN_SECTION = r"\b\d+\s+(Operating Environment|Design and Implementation Constraints|User Documentation).*"
PATTERN_RELATED_REQS = r"Related Reqs:.*?(?=Req ID:|OE-\d+:|CO-\d+:|UD-\d+:|$)"
PATTERN_REQ_ID = r"(Req ID:|OE-\d+|CO-\d+|UD-\d+)"
PATTERN_METADATA = r"^(OE|CO|UD)-\d+:\s*"
PATTERN_REQ_METADATA = r"Req ID:\s*\d+.*?Description:\s*"
PATTERN_REQ_KEYWORD = r"\b(shall|must|required)\b"

PATTERN_HEADER_RE = re.compile(PATTERN_HEADER, re.IGNORECASE)
PATTERN_PAGE_RE = re.compile(PATTERN_PAGE, re.IGNORECASE)
PATTERN_SECTION_RE = re.compile(PATTERN_SECTION, re.IGNORECASE)
PATTERN_RELATED_REQS_RE = re.compile(PATTERN_RELATED_REQS, re.DOTALL | re.IGNORECASE)
PATTERN_REQ_ID_RE = re.compile(PATTERN_REQ_ID)
PATTERN_METADATA_RE = re.compile(PATTERN_METADATA)
PATTERN_REQ_METADATA_RE = re.compile(PATTERN_REQ_METADATA, re.IGNORECASE)
PATTERN_REQ_KEYWORD_RE = re.compile(PATTERN_REQ_KEYWORD, re.IGNORECASE)
ARFF_LINE_RE = re.compile(r"\s*\d+\s*,\s*'(.+?)'\s*,\s*([A-Z]+)")

# =========================================================
# ⚙️ CONSTANTS
# =========================================================
MIN_TEXT_LENGTH = 20
MIN_LINE_LENGTH = 10
NOISE_PATTERNS = [
    "flowcharts generally",
    "among others",
    "for example",
    "it is highly desirable",
]

# =========================================================
# 📊 ISO 25010 QUALITY CHARACTERISTICS MAPPING
# =========================================================
ISO_MAPPING = {
    "F":  ("FR",  "Functional Suitability", "Functional Completeness"),
    "PE": ("NFR", "Performance Efficiency", "Time Behaviour"),
    "US": ("NFR", "Usability", "Operability"),
    "SE": ("NFR", "Security", "Confidentiality"),
    "A":  ("NFR", "Reliability", "Availability"),
    "FT": ("NFR", "Reliability", "Fault Tolerance"),
    "SC": ("NFR", "Compatibility", "Interoperability"),
    "LF": ("NFR", "Usability", "User Interface Aesthetics"),
    "MN": ("NFR", "Maintainability", "Modifiability"),
    "PO": ("NFR", "Portability", "Adaptability"),
    "O":  ("NFR", "Reliability", "Maturity"),
}



# =========================================================
# ✅ CLEAN TEXT
# =========================================================
def limpar(txt: str) -> str:
    """
    Clean text by removing headers, metadata, and noise.
    
    Removes:
    - Common headers (Software Requirements Specification, Page numbers)
    - Section markers
    - Related Requirements metadata
    - Punctuation artifacts
    
    Args:
        txt: Raw text to clean
        
    Returns:
        Cleaned text with normalized whitespace
        
    Examples:
        >>> limpar("Software Requirements Specification v1.0\\n  Text here  ")
        'Text here'
    """
    if not txt or not isinstance(txt, str):
        return ""
    
    txt = str(txt)

    # Remove common headers
    txt = PATTERN_HEADER_RE.sub("", txt)
    txt = PATTERN_PAGE_RE.sub("", txt)

    # Remove sections
    txt = PATTERN_SECTION_RE.sub("", txt)

    # Remove "Related Reqs" completely
    txt = PATTERN_RELATED_REQS_RE.sub("", txt)

    # Remove punctuation artifacts
    txt = txt.replace("'", "")
    txt = txt.replace(" ,", ",")

    # Normalize whitespace
    return re.sub(r"\s+", " ", txt).strip()


def limpar_prefixo(text: str) -> str:
    """
    Remove requirement ID prefixes and metadata blocks.
    
    Removes patterns like:
    - OE-1:, CO-1:, UD-1:
    - Req ID metadata blocks
    
    Args:
        text: Text with prefixes
        
    Returns:
        Text without prefixes
        
    Examples:
        >>> limpar_prefixo("OE-1: System shall authenticate users")
        'System shall authenticate users'
    """
    if not text or not isinstance(text, str):
        return ""

    # Remove OE-1: / CO-1: / UD-1: prefixes
    text = PATTERN_METADATA_RE.sub("", text)

    # Remove Req ID metadata blocks
    text = PATTERN_REQ_METADATA_RE.sub("", text)

    return text.strip()


# =========================================================
# ✅ LINE VALIDATION
# =========================================================
def linha_valida(line: str) -> bool:
    """
    Check if a line is a valid requirement text.
    
    Rejects:
    - Empty or whitespace-only lines
    - Very short lines (< 10 chars)
    - Lines starting with special characters (%, @)
    - Lines with formatting characters (====, %%%%)
    - Lines with URLs
    
    Args:
        line: Line to validate
        
    Returns:
        True if valid, False otherwise
        
    Examples:
        >>> linha_valida("The system shall authenticate")
        True
        >>> linha_valida("@ignore")
        False
    """
    if not line or not isinstance(line, str):
        return False
    
    line = line.strip()

    if not line:
        return False

    if len(line) < MIN_LINE_LENGTH:
        return False

    if line.startswith("%"):
        return False

    if line.startswith("@"):
        return False

    if "====" in line or "%%%%" in line:
        return False

    if "http://" in line or "https://" in line:
        return False

    return True


# =========================================================
# ✅ SPLIT TEXT INTO BLOCKS
# =========================================================
def dividir(txt: str) -> List[str]:
    """
    Split text into requirement blocks using requirement ID patterns.
    
    Splits on patterns:
    - Req ID:
    - OE-\d+:
    - CO-\d+:
    - UD-\d+:
    
    Then validates and filters each block.
    
    Args:
        txt: Raw text to split
        
    Returns:
        List of valid requirement blocks
        
    Examples:
        >>> blocks = dividir("OE-1: Text\\nOE-2: More text")
        >>> len(blocks)
        2
    """
    if not txt or not isinstance(txt, str):
        return []

    # Split by requirement ID patterns
    blocos = re.split(
        rf"(?={PATTERN_REQ_ID})",
        txt
    )

    linhas: List[str] = []

    for bloco in blocos:
        bloco = bloco.strip()

        if not bloco:
            continue

        if linha_valida(bloco):
            linhas.append(bloco)

    return linhas



# =========================================================
# ✅ PARSE PROMISE ARFF → ISO 25010
# =========================================================
def extrair_arff_iso(linha: str) -> Optional[Tuple[str, str, str, str]]:
    """
    Parse PROMISE ARFF format and map to ISO 25010 quality characteristics.
    
    Expected format: index,'text',CLASS_CODE
    
    Args:
        linha: ARFF line to parse
        
    Returns:
        Tuple of (text, req_type, iso_char, iso_subchar) or None if invalid
        
    Examples:
        >>> result = extrair_arff_iso("1,'System authenticates',SE")
        >>> result[0]
        'System authenticates'
        >>> result[1]
        'NFR'
    """
    if not linha or not isinstance(linha, str):
        return None

    try:
        match = ARFF_LINE_RE.match(linha)

        if not match:
            return None

        texto = match.group(1).strip()
        classe = match.group(2).strip()

        # Look up in ISO mapping, default to Functional Suitability
        iso_data = ISO_MAPPING.get(classe, ("FR", "Functional Suitability", "Functional Completeness"))
        
        return texto, *iso_data
        
    except Exception as e:
        logger.warning(f"Failed to parse ARFF line: {e}")
        return None


# =========================================================
# ✅ ISO HEURISTIC (Fallback Classification)
# =========================================================
def heuristica_iso(texto: str) -> Tuple[str, str, str]:
    """
    Classify requirement using heuristic keywords (fallback method).
    
    Returns ISO 25010 characteristic based on text content.
    
    Args:
        texto: Requirement text
        
    Returns:
        Tuple of (req_type, iso_characteristic, iso_subcharacteristic)
        
    Examples:
        >>> heuristica_iso("Response time must be under 2 seconds")
        ('NFR', 'Performance Efficiency', 'Time Behaviour')
    """
    if not texto or not isinstance(texto, str):
        return "FR", "Functional Suitability", "Functional Completeness"

    t = texto.lower()

    # Performance indicators
    if any(keyword in t for keyword in ["second", "seconds", "ms", "%", "time", "latency", "fast", "slow", "delay"]):
        return "NFR", "Performance Efficiency", "Time Behaviour"

    # Security indicators
    if any(keyword in t for keyword in ["secure", "authorized", "authentication", "encrypt"]):
        return "NFR", "Security", "Confidentiality"

    # Availability indicators
    if any(keyword in t for keyword in ["available", "uptime", "downtime"]):
        return "NFR", "Reliability", "Availability"

    # Usability indicators
    if any(keyword in t for keyword in ["easy", "intuitive", "usable", "user-friendly"]):
        return "NFR", "Usability", "Operability"

    # Default to Functional
    return "FR", "Functional Suitability", "Functional Completeness"



# =========================================================
# ✅ PARSE LLM RESPONSE (Pipe-delimited format)
# =========================================================
def parse_extract(resp: str) -> List[List[str]]:
    """
    Parse LLM response in pipe-delimited format.
    
    Expected format per line: ID|TEXT|TYPE|OTHER
    
    Args:
        resp: Raw LLM response text
        
    Returns:
        List of parsed requirement rows (each row is a list)
        
    Examples:
        >>> rows = parse_extract("REQ001|System shall validate|FR|Important")
        >>> len(rows)
        1
    """
    if not resp or not isinstance(resp, str):
        return []

    out: List[List[str]] = []

    try:
        for line in str(resp).splitlines():
            line = line.strip()
            
            if not line:
                continue
            
            parts = [x.strip() for x in line.split("|")]

            # Need at least 3 parts: ID, TEXT, TYPE
            if len(parts) >= 3 and len(parts[1]) > MIN_TEXT_LENGTH:
                out.append(parts)
                
    except Exception as e:
        logger.warning(f"Failed to parse extract response: {e}")

    return out


# =========================================================
# ✅ RECONSTRUCT SENTENCES (Critical for multi-line reqs)
# =========================================================
def reconstruir(linhas: List[str]) -> List[str]:
    """
    Reconstruct requirement sentences from text lines.
    
    Groups lines that belong to the same requirement:
    - Lines starting with requirement patterns → new requirement
    - Continuation lines (no capital start) → append to previous
    - Empty lines → skipped
    
    Args:
        linhas: List of text lines
        
    Returns:
        List of reconstructed requirement sentences
        
    Examples:
        >>> lines = ["Req ID: 1", "System shall validate", "and authenticate users"]
        >>> reconstruir(lines)
        ['Req ID: 1 System shall validate and authenticate users']
    """
    if not linhas or not isinstance(linhas, (list, tuple)):
        return []

    resultado: List[str] = []
    buffer = ""

    try:
        for line in linhas:
            line = line.strip()
            
            if not line:
                continue

            # New requirement block detected
            if PATTERN_REQ_ID_RE.match(line):
                if buffer:
                    resultado.append(buffer)
                buffer = line
                continue

            # Continuation line (starts with lowercase or special char)
            if buffer and not line[0].isupper():
                buffer += " " + line
            else:
                # New independent line
                if buffer:
                    resultado.append(buffer)
                buffer = line

        # Don't forget the last buffer
        if buffer:
            resultado.append(buffer)
            
    except Exception as e:
        logger.warning(f"Reconstruction failed: {e}")

    return resultado


# =========================================================
# ✅ STRONG REQUIREMENT FILTER
# =========================================================
def is_requirement(text: str) -> bool:
    if not text:
        return False

    t = text.lower().strip()

    if len(t) < 25:
        return False

    # ✅ palavras chave de requisito REAL
    keywords = [
        "shall", "must", "should",
        "allow", "provide", "support",
        "system", "user"
    ]

    return any(k in t for k in keywords)


# =========================================================
# ✅ MAIN PIPELINE: TEXT → RAW REQUIREMENTS
# =========================================================
def extrair_requisitos_brutos(text: str) -> List[str]:
    """
    Extract raw requirements from text using multi-step pipeline.
    
    Pipeline steps:
    1. Split text into blocks by requirement ID patterns
    2. Clean each block (remove headers, metadata)
    3. Remove requirement ID prefixes
    4. Filter for actual requirements (must have keywords)
    5. Deduplicate
    
    Args:
        text: Raw input text (from PDF, DOCX, etc.)
        
    Returns:
        List of requirement strings (deduplicated, cleaned)
        
    Examples:
        >>> reqs = extrair_requisitos_brutos("OE-1: System shall authenticate\\nOE-2: System must authorize")
        >>> len(reqs)
        2
    """
    if not text or not isinstance(text, str):
        logger.warning("Invalid text input for requirement extraction")
        return []

    try:
        logger.info("Starting requirement extraction pipeline")
        
        # Step 1: Split into blocks
        linhas = dividir(text)
        logger.debug(f"Split into {len(linhas)} blocks")

        # Step 2: Clean each block
        linhas = [limpar(l) for l in linhas]

        # Step 3: Remove prefixes
        linhas = [limpar_prefixo(l) for l in linhas]

        # Step 4: Filter for actual requirements
        linhas = [l for l in linhas if is_requirement(l)]
        logger.debug(f"Filtered to {len(linhas)} requirements")

        # Step 5: Deduplicate (case-insensitive)
        seen: Set[str] = set()
        clean: List[str] = []

        for line in linhas:
            key = line.lower().strip()

            if key and key not in seen:
                seen.add(key)
                clean.append(line)

        logger.info(f"✅ Extraction complete: {len(clean)} unique requirements extracted")
        return clean
        
    except Exception as e:
        logger.error(f"Requirement extraction failed: {e}", exc_info=True)
        return []

def hybrid_classification(text: str) -> Optional[Tuple[str, str]]:
    """
    Hybrid classifier combining rule-based + ISO heuristics.

    Returns:
        (type, subclass) or None if uncertain
    """
    if not text:
        return None

    t = text.lower()

    # 🔒 SECURITY (prioridade alta)
    if any(k in t for k in [
        "authentication", "authorization", "privacy", "encryption",
        "integrity", "credential", "firewall", "access control", "secure"
    ]):
        return "NFR", "Security"

    # ⚙️ FUNCTIONAL (forte sinal)
    if any(k in t for k in [
        "shall support", "shall provide", "shall allow", "user can"
    ]):
        return "FR", "Functional"

    # ⚡ PERFORMANCE
    if any(k in t for k in [
        "latency", "response time", "throughput", "bandwidth", "qos"
    ]):
        return "NFR", "Performance"

    # 🔁 ISO fallback
    iso_type, iso_char, _ = heuristica_iso(text)

    mapping = {
        "Performance Efficiency": "Performance",
        "Usability": "Usability",
        "Reliability": "Reliability",
        "Security": "Security",
        "Compatibility": "Compatibility",
        "Maintainability": "Maintainability",
        "Portability": "Portability",
    }

    subclass = mapping.get(iso_char)

    if iso_type and subclass:
        return iso_type, subclass

    return None

# =========================================================
# PDF TABLE EXTRACTION (FINAL)
# =========================================================

def extract_pdf_tables(path_or_file):
    """
    Extract structured tables from PDF preserving columns.
    Works for requirement tables (ID | Text | Class | ...).
    Returns a DataFrame or None if no tables found.
    """
    rows = []
    header = None

    try:
        with pdfplumber.open(path_or_file) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()

                for table in tables:
                    if not table:
                        continue

                    # First row is header
                    if not header:
                        header = [c.strip() if c else "" for c in table[0]]

                    # Remaining rows
                    for row in table[1:]:
                        clean_row = [c.strip() if isinstance(c, str) else "" for c in row]
                        rows.append(clean_row)

        if not rows or not header:
            return None

        df = pd.DataFrame(rows, columns=header)
        return df

    except Exception as e:
        logger.warning(f"PDF table extraction error: {e}")
        return None


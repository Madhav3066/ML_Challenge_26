import re
import unicodedata

# Missing value representations
MISSING_VALUES = {
    "none", "null", "n/a", "na", "nan", "undefined", ""
}

def is_missing_value(val) -> bool:
    """Return True if value represents a missing/empty entity field."""
    if val is None:
        return True
    s = str(val).strip().lower()
    return s in MISSING_VALUES

# Legal / corporate entity suffixes to strip for root_name
# Comprehensive across US, India, France, and international entities
LEGAL_TERMS = [
    r'private\s+limited',
    r'pvt\s+ltd',
    r'limited\s+private',
    r'pvt\s+limited',
    r'private\s+ltd',
    r'(?:and|et)\s+fils',
    r'fils',
    r'incorporated',
    r'corporation',
    r'company',
    r'limited',
    r'private',
    r'pvt',
    r'corp',
    r'inc',
    r'llc',
    r'pllc',
    r'llp',
    r'ltd',
    r'co',
    r'sarl',
    r'sasu',
    r'sas',
    r'eurl',
    r'eirl',
    r'sa',
    r'selarl',
    r'snc',
    r'gmbh',
    r'spa',
    r'bv',
]

# Suffix pattern matching at word boundaries or inside brackets at the end of string
LEGAL_SUFFIX_RE = re.compile(
    r'(?:[\(\[\{]\s*(?:' + '|'.join(LEGAL_TERMS) + r')\s*[\)\]\}]|\b(?:' + '|'.join(LEGAL_TERMS) + r')\b)\s*$',
    re.IGNORECASE
)

# Prefix pattern for leading legal designations (e.g. LLC Crystal Staffing)
LEGAL_PREFIX_RE = re.compile(
    r'^(?:llc|inc|corp|corporation|company|co|ltd|limited|pvt\s+ltd|pvt|private|sarl|sasu|sas|eurl)\b\s*',
    re.IGNORECASE
)

# Honorifics pattern: boundary-aware leading prefixes
HONORIFIC_PREFIX_RE = re.compile(
    r'^(?:m\s*/\s*s|dr\.?|sri|shri|smt|messrs|mr\.?|mrs\.?|ms\.?)\b\s*',
    re.IGNORECASE
)

# Numeric address token pattern (e.g., 570/13, 201/D, 113/154, 105, 3907)
NUMERIC_ADDR_PATTERN = re.compile(r'\b\d+(?:[/-]\d+|[a-zA-Z])?\b')

# Known country normalization mappings
COUNTRY_MAP = {
    "us": "us", "usa": "us", "united states": "us", "united states of america": "us",
    "india": "india", "ind": "india", "in": "india",
    "france": "france", "fr": "france", "fra": "france",
    "uk": "uk", "gbr": "uk", "united kingdom": "uk", "great britain": "uk",
    "germany": "germany", "deu": "germany", "de": "germany",
    "brazil": "brazil", "bra": "brazil", "br": "brazil",
}

# State/region mappings for US and India
INDIA_STATES = {
    "west bengal": "wb", "wb": "wb",
    "maharashtra": "mh", "mh": "mh",
    "delhi": "dl", "dl": "dl", "new delhi": "dl",
    "tamil nadu": "tn", "tn": "tn",
    "karnataka": "ka", "ka": "ka",
    "uttar pradesh": "up", "up": "up",
    "gujarat": "gj", "gj": "gj",
    "telangana": "tg", "tg": "tg", "ts": "tg",
    "andhra pradesh": "ap", "ap": "ap",
    "kerala": "kl", "kl": "kl",
    "rajasthan": "rj", "rj": "rj",
    "madhya pradesh": "mp", "mp": "mp",
    "punjab": "pb", "pb": "pb",
    "haryana": "hr", "hr": "hr",
    "bihar": "br", "br": "br",
    "odisha": "od", "orissa": "od", "od": "od",
    "assam": "as", "as": "as",
    "jharkhand": "jh", "jh": "jh",
    "uttarakhand": "uk", "uk": "uk",
    "goa": "ga", "ga": "ga",
    "himachal pradesh": "hp", "hp": "hp",
    "chhattisgarh": "cg", "cg": "cg",
    "chandigarh": "ch", "ch": "ch",
    "puducherry": "py", "pondicherry": "py",
}

US_STATES = {
    "al": "al", "alabama": "al", "ak": "ak", "alaska": "ak",
    "az": "az", "arizona": "az", "ar": "ar", "arkansas": "ar",
    "ca": "ca", "california": "ca", "co": "co", "colorado": "co",
    "ct": "ct", "connecticut": "ct", "de": "de", "delaware": "de",
    "fl": "fl", "florida": "fl", "ga": "ga", "georgia": "ga",
    "hi": "hi", "hawaii": "hi", "id": "id", "idaho": "id",
    "il": "il", "illinois": "il", "in": "in", "indiana": "in",
    "ia": "ia", "iowa": "ia", "ks": "ks", "kansas": "ks",
    "ky": "ky", "kentucky": "ky", "la": "la", "louisiana": "la",
    "me": "me", "maine": "me", "md": "md", "maryland": "md",
    "ma": "ma", "massachusetts": "ma", "mi": "mi", "michigan": "mi",
    "mn": "mn", "minnesota": "mn", "ms": "ms", "mississippi": "ms",
    "mo": "mo", "missouri": "mo", "mt": "mt", "montana": "mt",
    "ne": "ne", "nebraska": "ne", "nv": "nv", "nevada": "nv",
    "nh": "nh", "new hampshire": "nh", "nj": "nj", "new jersey": "nj",
    "nm": "nm", "new mexico": "nm", "ny": "ny", "new york": "ny",
    "nc": "nc", "north carolina": "nc", "nd": "nd", "north dakota": "nd",
    "oh": "oh", "ohio": "oh", "ok": "ok", "oklahoma": "ok",
    "or": "or", "oregon": "or", "pa": "pa", "pennsylvania": "pa",
    "ri": "ri", "rhode island": "ri", "sc": "sc", "south carolina": "sc",
    "sd": "sd", "south dakota": "sd", "tn": "tn", "tennessee": "tn",
    "tx": "tx", "texas": "tx", "ut": "ut", "utah": "ut",
    "vt": "vt", "vermont": "vt", "va": "va", "virginia": "va",
    "wa": "wa", "washington": "wa", "wv": "wv", "west virginia": "wv",
    "wi": "wi", "wisconsin": "wi", "wy": "wy", "wyoming": "wy",
    "dc": "dc", "district of columbia": "dc",
}

def _is_latin_combining(c: str) -> bool:
    """Check if character is a Latin combining diacritical mark."""
    o = ord(c)
    return (
        (0x0300 <= o <= 0x036F) or  # Combining Diacritical Marks
        (0x1DC0 <= o <= 0x1DFF) or  # Combining Diacritical Marks Supplement
        (0x20D0 <= o <= 0x20FF) or  # Combining Diacritical Marks for Symbols
        (0xFE20 <= o <= 0xFE2F)     # Combining Half Marks
    )

def normalize_text(text: str) -> str:
    """Apply Unicode NFKD normalization, strip Latin diacritics, normalize quotes, &, spaces."""
    if is_missing_value(text):
        return ""
    text = str(text)
    # Replace smart quotes with standard quotes
    text = text.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
    # Replace ampersands with 'and'
    text = re.sub(r'&', ' and ', text)
    # Unicode NFKD normalization
    text = unicodedata.normalize('NFKD', text)
    # Strip Latin combining diacritics while strictly preserving Indic matras / viramas
    text = "".join(c for c in text if not _is_latin_combining(c))
    text = text.lower()
    # Collapse multiple whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def clean_business_name(text: str) -> str:
    """Normalize business name: lowercase, punctuation removed, multilingual preserved."""
    if is_missing_value(text):
        return ""
    text = normalize_text(text)
    # Keep Unicode letters (L), numbers (N), combining marks (M - Indic matras), and spaces.
    # Replace all punctuation and symbols with space.
    cleaned = []
    for c in text:
        cat = unicodedata.category(c)
        if cat[0] in ('L', 'N', 'M') or c.isspace():
            cleaned.append(c)
        else:
            cleaned.append(' ')
    text = "".join(cleaned)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def strip_honorifics(text: str) -> str:
    """Safely strip leading honorific prefixes while preserving real name boundaries."""
    if not text:
        return ""
    text = text.strip()
    while True:
        new_text = HONORIFIC_PREFIX_RE.sub('', text).strip()
        if new_text == text:
            break
        text = new_text
    return text

def strip_legal_suffixes(text: str) -> str:
    """Strip legal and corporate suffixes (and prefixes) from business name."""
    if not text:
        return ""
    text = text.strip()
    while True:
        new_text = LEGAL_SUFFIX_RE.sub('', text).strip()
        new_text = LEGAL_PREFIX_RE.sub('', new_text).strip()
        if new_text == text:
            break
        text = new_text
    # Clean any dangling brackets
    text = re.sub(r'[\(\[\{\)\]\}]', '', text).strip()
    return text if text else ""

def get_root_name(clean_name: str) -> str:
    """Remove honorifics and legal suffixes to produce canonical root_name."""
    if not clean_name:
        return ""
    root = strip_honorifics(clean_name)
    root = strip_legal_suffixes(root)
    root = re.sub(r'\s+', ' ', root).strip()
    return root if root else clean_name

def get_sorted_tokens(text: str, n: int = 2) -> str:
    """Extract alphabetically sorted tokens (first n tokens after sort)."""
    if not text:
        return ""
    tokens = sorted(text.split())
    return " ".join(tokens[:n])

def clean_business_address(text: str) -> str:
    """Normalize address while preserving numeric formats like 570/13, 201/D."""
    if is_missing_value(text):
        return ""
    text = normalize_text(text)
    if not text:
        return ""
    text = re.sub(r'[^\w\s/-]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_numeric_tokens(clean_addr: str) -> list:
    """Extract list of numeric address tokens, stripping redundant leading zeros."""
    if not clean_addr:
        return []
    raw_tokens = NUMERIC_ADDR_PATTERN.findall(clean_addr)
    # Normalize leading zeros from pure digit sequences (e.g. 0684 -> 684)
    normalized = []
    for t in raw_tokens:
        norm_t = re.sub(r'^0+(?=[1-9])', '', t)
        normalized.append(norm_t if norm_t else t)
    return normalized

def extract_first_num_token(clean_addr: str) -> str:
    """Return the first numeric address token or empty string."""
    tokens = extract_numeric_tokens(clean_addr)
    return tokens[0] if tokens else ""

def get_first_n_tokens(text: str, n: int = 2) -> str:
    """Extract first n whitespace-delimited tokens."""
    if not text:
        return ""
    tokens = text.split()
    return " ".join(tokens[:n])

def extract_region_prefix(raw_address: str) -> str:
    """Extract 3-char prefix of city/state/region from address."""
    if not raw_address:
        return ""
    parts = [p.strip() for p in raw_address.split(',') if p.strip()]
    if len(parts) >= 2:
        region = normalize_text(parts[-1])
        region = re.sub(r'[^\w]', '', region)
        return region[:3]
    clean = re.sub(r'[^\w]', '', normalize_text(raw_address))
    return clean[-3:] if len(clean) >= 3 else clean

def normalize_country(country) -> str:
    """Normalize country code/name while keeping unseen countries valid."""
    if is_missing_value(country):
        return ""
    c = normalize_text(str(country))
    return COUNTRY_MAP.get(c, c)

INDIA_STATES_REGEX = re.compile(
    r'\b(?:' + '|'.join(re.escape(k) for k in sorted(INDIA_STATES.keys(), key=len, reverse=True)) + r')\b'
)

US_STATES_REGEX = re.compile(
    r'\b(?:' + '|'.join(re.escape(k) for k in sorted(US_STATES.keys(), key=len, reverse=True)) + r')\b'
)

def standardize_region(address: str, country: str) -> str:
    """Extract standardized 2-char region/state code from address if possible."""
    if not address:
        return ""
    c = normalize_country(country)
    parts = [p.strip().lower() for p in address.split(',') if p.strip()]
    
    if c in ("india", "ind", "in"):
        for p in [parts[0], parts[-1]] if parts else []:
            clean_p = re.sub(r'[^\w\s]', '', p).strip()
            if clean_p in INDIA_STATES:
                return INDIA_STATES[clean_p]
        norm_addr = normalize_text(address)
        m = INDIA_STATES_REGEX.search(norm_addr)
        if m:
            return INDIA_STATES[m.group(0)]
                
    elif c in ("us", "usa"):
        for p in [parts[0], parts[-1]] if parts else []:
            clean_p = re.sub(r'[^\w\s]', '', p).strip()
            if clean_p in US_STATES:
                return US_STATES[clean_p]
        norm_addr = normalize_text(address)
        m = US_STATES_REGEX.search(norm_addr)
        if m:
            return US_STATES[m.group(0)]
                
    return extract_region_prefix(address)

def generate_blocking_keys(root_name: str, clean_name: str, raw_address: str, clean_address: str, country: str) -> dict:
    """
    Generate the 4 blocking keys for candidate generation.
    All keys are strictly suffixed with country to ensure country-aware partitioning.
    """
    c = normalize_country(country)
    first_num = extract_first_num_token(clean_address)
    first_2_tokens = get_first_n_tokens(root_name, 2)
    first_6_root = re.sub(r'[^\w]', '', root_name)[:6]
    region_3 = standardize_region(raw_address, country) or extract_region_prefix(raw_address)
    first_3_name = re.sub(r'[^\w]', '', clean_name)[:3]

    keys = {
        # Pass 1: exact root_name + country
        "pass1": f"{root_name}||{c}" if root_name else "",
        
        # Pass 2: first 2 significant root-name tokens + first numeric address token + country
        "pass2": f"{first_2_tokens}||{first_num}||{c}" if (first_2_tokens and first_num) else "",
        
        # Pass 3: first 6 alphanumeric chars of root_name + first 3 chars of city/state + country
        "pass3": f"{first_6_root}||{region_3}||{c}" if (len(first_6_root) >= 3 and region_3) else "",
        
        # Pass 4: exact address numeric token + 3-char name prefix + country
        "pass4": f"{first_num}||{first_3_name}||{c}" if (first_num and len(first_3_name) >= 2) else ""
    }
    return keys

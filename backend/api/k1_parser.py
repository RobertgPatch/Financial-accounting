"""K-1 PDF text extraction and field parsing.

Uses pdfplumber for text extraction from digitally-generated PDFs,
with pytesseract OCR as a fallback for scanned documents.

The parser does best-effort extraction — users can always correct
values on the review page. Logging is verbose so failures are diagnosable.
"""
import logging
import re
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)
# Turn on DEBUG for this module in dev to see extracted text
# logging.getLogger(__name__).setLevel(logging.DEBUG)


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def extract_text_from_pdf(file_path):
    """Extract text from a PDF file.

    Tries pdfplumber text extraction first (including tables).
    If no meaningful text is found (likely scanned), falls back to OCR.

    Returns:
        tuple: (full_text: str, extraction_method: str)
    """
    import pdfplumber

    pages_text = []
    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            # Standard text extraction
            text = page.extract_text() or ''

            # Also try to extract tables (K-1 forms are heavily tabular)
            try:
                tables = page.extract_tables() or []
                for table in tables:
                    for row in (table or []):
                        cells = [str(c).strip() for c in (row or []) if c]
                        if cells:
                            text += '\n' + '  '.join(cells)
            except Exception:
                pass

            pages_text.append(text)
            logger.debug("Page %d extracted %d chars", page_num, len(text))

    full_text = '\n\n'.join(pages_text)
    logger.info("PDF text extraction: %d total chars from %d pages", len(full_text.strip()), len(pages_text))
    logger.debug("Extracted text (first 2000 chars):\n%s", full_text[:2000])

    # If we got meaningful text, return it
    if len(full_text.strip()) > 100:
        return full_text, 'text'

    # OCR fallback for scanned documents
    logger.info("Text extraction yielded minimal content, attempting OCR fallback")
    try:
        from PIL import Image
        import pytesseract

        ocr_pages = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                img = page.to_image(resolution=300).original
                ocr_text = pytesseract.image_to_string(img)
                ocr_pages.append(ocr_text)

        ocr_full = '\n\n'.join(ocr_pages)
        if len(ocr_full.strip()) > 50:
            logger.info("OCR extraction: %d chars", len(ocr_full.strip()))
            return ocr_full, 'ocr'
    except Exception as e:
        logger.warning("OCR fallback failed: %s", e)

    # Return whatever we got from text extraction
    return full_text, 'text'


# ---------------------------------------------------------------------------
# Currency / percentage parsing helpers
# ---------------------------------------------------------------------------

def _parse_currency(text):
    """Parse a currency string into a Decimal, handling parentheses for negatives.

    Examples:
        "4,493,757"    → Decimal("4493757.00")
        "(409,615)"    → Decimal("-409615.00")
        "$1,234.56"    → Decimal("1234.56")
        "-1234"        → Decimal("-1234.00")
        ""             → None
    """
    if not text or not text.strip():
        return None
    text = text.strip().replace('$', '').replace(',', '').replace(' ', '')
    negative = False
    if text.startswith('(') and text.endswith(')'):
        negative = True
        text = text[1:-1]
    elif text.startswith('-'):
        negative = True
        text = text[1:]
    text = text.strip()
    if not text:
        return None
    try:
        val = Decimal(text)
        if negative:
            val = -val
        return val.quantize(Decimal('0.01'))
    except InvalidOperation:
        return None


def _parse_percentage(text):
    """Parse a percentage string into a Decimal (as the numeric value, not divided by 100).

    Examples:
        "3.032900%"  → Decimal("3.032900")
        "3.0329"     → Decimal("3.032900")
        "50%"        → Decimal("50.000000")
    """
    if not text or not text.strip():
        return None
    text = text.strip().replace('%', '').replace(',', '').replace(' ', '')
    if not text:
        return None
    try:
        return Decimal(text).quantize(Decimal('0.000001'))
    except InvalidOperation:
        return None


# ---------------------------------------------------------------------------
# Part I: Partnership Info
# ---------------------------------------------------------------------------

def parse_partnership_info(text):
    """Extract Part I — Information About the Partnership from K-1 text.

    Returns dict with keys: ein, name, address, city, state, zip_code,
    irs_center, is_ptp, tax_year, is_final, is_amended
    """
    result = {
        'ein': '',
        'name': '',
        'address': '',
        'city': '',
        'state': '',
        'zip_code': '',
        'irs_center': '',
        'is_ptp': False,
    }
    header = {
        'tax_year': None,
        'is_final': False,
        'is_amended': False,
    }

    # Extract tax year from header
    year_match = re.search(r'(?:calendar\s+year|tax\s+year\s*(?:beginning|ending)?)\s*(\d{4})', text, re.IGNORECASE)
    if year_match:
        header['tax_year'] = int(year_match.group(1))
    else:
        year_match2 = re.search(r'\b(20[2-9]\d)\b', text[:500])
        if year_match2:
            header['tax_year'] = int(year_match2.group(1))

    # Final / Amended checkboxes
    if re.search(r'(?:final|Final)\s*K-?1', text[:1000]):
        header['is_final'] = True
    if re.search(r'(?:amended|Amended)\s*K-?1', text[:1000]):
        header['is_amended'] = True

    # Partnership EIN (Line A) — try multiple patterns
    ein_patterns = [
        r"(?:partnership|employer)(?:'s)?\s*(?:employer\s+)?identification\s+number[:\s]*(\d{2}-?\d{7})",
        r"[Ee]\.?[Ii]\.?[Nn]\.?\s*[:\s]+(\d{2}-?\d{7})",
        r"\bA\b[.\s]+(\d{2}-\d{7})",
        r'\b(\d{2}-\d{7})\b',
    ]
    for pattern in ein_patterns:
        m = re.search(pattern, text[:3000], re.IGNORECASE)
        if m:
            result['ein'] = m.group(1)
            logger.debug("EIN matched with pattern: %s → %s", pattern[:40], m.group(1))
            break

    # Partnership name and address (Line B) — try multiple strategies
    name_found = False

    # Strategy 1: Look for name block after "Partnership's name"
    name_block_match = re.search(
        r"(?:Partnership'?s?\s+name|B\s+Partnership)[,.\s:]*(?:address[,.\s:]*(?:city[,.\s:]*state[,.\s:]*(?:and\s+)?ZIP\s*(?:code)?)?)?[:\s]*\n(.*?)(?=\n\s*(?:C\s+IRS|IRS\s+[Cc]enter|Part\s+II|D\s+))",
        text, re.DOTALL | re.IGNORECASE
    )
    if name_block_match:
        block = name_block_match.group(1).strip()
        lines = [l.strip() for l in block.split('\n') if l.strip()]
        if lines:
            result['name'] = lines[0]
            name_found = True
        if len(lines) > 1:
            result['address'] = lines[1] if len(lines) > 2 else ''
        if len(lines) > 2:
            _parse_city_state_zip(lines[-1], result)

    # Strategy 2: Look for name near EIN — common in tabular K-1s
    if not name_found:
        _extract_name_after_ein(text, result)
        if result['name']:
            name_found = True

    # Strategy 3: Look for text immediately following the EIN on the same or next lines
    if not name_found and result['ein']:
        ein_pos = text.find(result['ein'])
        if ein_pos >= 0:
            after_ein = text[ein_pos + len(result['ein']):ein_pos + 500]
            lines_after = [l.strip() for l in after_ein.split('\n') if l.strip() and not re.match(r'^[\d\-]+$', l.strip())]
            for line in lines_after[:5]:
                # Skip lines that are just numbers or EIN-like
                if len(line) > 3 and not re.match(r'^[\d\-\s]+$', line):
                    result['name'] = line
                    name_found = True
                    break

    logger.debug("Partnership name: %s", result['name'] or '(not found)')

    # IRS Center (Line C)
    if re.search(r'E-?FILE', text[:5000], re.IGNORECASE):
        result['irs_center'] = 'E-FILE'
    else:
        center_match = re.search(
            r'IRS\s+[Cc]enter.*?(?:filed\s+return|return\s+(?:was\s+)?filed)[:\s]*(.*?)(?:\n|$)',
            text, re.IGNORECASE
        )
        if center_match and center_match.group(1).strip():
            result['irs_center'] = center_match.group(1).strip()

    # PTP checkbox (Line D)
    if re.search(r'publicly\s+traded\s+partnership.*?(?:\[?[xX✓✗]\]?|Yes)', text, re.IGNORECASE):
        result['is_ptp'] = True

    logger.debug("Partnership info result: ein=%s, name=%s, city=%s", result['ein'], result['name'], result['city'])
    return result, header


def _parse_city_state_zip(line, result):
    """Parse a 'City, ST XXXXX' or 'City, ST XXXXX-XXXX' line."""
    csz = re.match(r'(.*?),\s*([A-Z]{2})\s+(\d{5}(?:-\d{4})?)', line)
    if csz:
        result['city'] = csz.group(1).strip()
        result['state'] = csz.group(2)
        result['zip_code'] = csz.group(3)
    else:
        # Try without comma
        csz2 = re.match(r'(.*?)\s+([A-Z]{2})\s+(\d{5}(?:-\d{4})?)', line)
        if csz2:
            result['city'] = csz2.group(1).strip()
            result['state'] = csz2.group(2)
            result['zip_code'] = csz2.group(3)


def _extract_name_after_ein(text, result):
    """Fallback: extract partnership name from near the EIN in text."""
    # Look for common pattern: EIN followed by partnership name on next line(s)
    match = re.search(r'\d{2}-\d{7}\s*\n\s*(.*?)(?:\n|$)', text[:2000])
    if match:
        result['name'] = match.group(1).strip()


# ---------------------------------------------------------------------------
# Part II: Partner Info
# ---------------------------------------------------------------------------

def parse_partner_info(text):
    """Extract Part II — Information About the Partner from K-1 text.

    Returns dict matching K1PartnerInfo model fields.
    """
    result = {
        'tin': '',
        'name': '',
        'address': '',
        'city': '',
        'state': '',
        'zip_code': '',
        'is_general_partner': False,
        'is_domestic': True,
        'entity_type': '',
        'is_retirement_plan': False,
        'profit_beginning_pct': None,
        'profit_ending_pct': None,
        'loss_beginning_pct': None,
        'loss_ending_pct': None,
        'capital_beginning_pct': None,
        'capital_ending_pct': None,
        'nonrecourse_beginning': None,
        'nonrecourse_ending': None,
        'qualified_nonrecourse_beginning': None,
        'qualified_nonrecourse_ending': None,
        'recourse_beginning': None,
        'recourse_ending': None,
        'has_lower_tier_liabilities': False,
        'has_guarantee_obligations': False,
        'section_704c_beginning': None,
        'section_704c_ending': None,
        'built_in_gain': None,
    }

    # Partner TIN (Line E) — try multiple patterns
    tin_patterns = [
        r"(?:Partner'?s?\s+)?(?:identifying|taxpayer\s+identification)\s+number[:\s]*([\d*X]{2,3}[-\s]?[\d*X]{2}[-\s]?[\d*X]{4})",
        r"(?:SSN|TIN|T\.?I\.?N\.?)[:\s]*([\d*X]{2,3}[-\s]?[\d*X]{2}[-\s]?[\d*X]{4})",
        r'(\*{3}-\*{2}-\d{4})',
        r'(\d{3}-\d{2}-\d{4})',
        r'(X{3}-X{2}-\d{4})',
        r'(\*{5,}\d{4})',
    ]
    for pattern in tin_patterns:
        m = re.search(pattern, text[:4000], re.IGNORECASE)
        if m:
            result['tin'] = m.group(1)
            logger.debug("TIN matched: %s", m.group(1))
            break

    # Partner name/address (Line F)
    name_block = re.search(
        r"(?:Partner'?s?\s+name|F\s+Partner)[,.\s:]*(?:address)?[:\s]*\n(.*?)(?=\n\s*(?:G\s+|General\s+partner|What\s+type|H\s+))",
        text, re.DOTALL | re.IGNORECASE
    )
    if name_block:
        block = name_block.group(1).strip()
        lines = [l.strip() for l in block.split('\n') if l.strip()]
        if lines:
            result['name'] = lines[0]
        if len(lines) > 1:
            result['address'] = lines[1] if len(lines) > 2 else ''
        if len(lines) > 2:
            _parse_city_state_zip(lines[-1], result)

    # General partner vs Limited partner (Line G)
    if re.search(r'General\s+partner.*?(?:\[?[xX✓]\]?|checked)', text, re.IGNORECASE):
        result['is_general_partner'] = True

    # Domestic vs Foreign (Line H1)
    if re.search(r'Foreign\s+partner.*?(?:\[?[xX✓]\]?|checked)', text, re.IGNORECASE):
        result['is_domestic'] = False

    # Entity type (Line I1)
    entity_match = re.search(r'(?:type\s+of\s+entity|I1)[:\s]*(Individual|Corporation|Estate|Trust|Partnership|LLC|S\s+Corporation|Exempt\s+Organization|Nominee)', text, re.IGNORECASE)
    if entity_match:
        result['entity_type'] = entity_match.group(1).strip()

    # Retirement plan (Line I2)
    if re.search(r'retirement\s+plan.*?(?:\[?[xX✓]\]?|checked|Yes)', text, re.IGNORECASE):
        result['is_retirement_plan'] = True

    # Section J: Profit/Loss/Capital percentages
    _parse_section_j(text, result)

    # Section K: Liabilities
    _parse_section_k(text, result)

    # Section N: 704(c)
    _parse_section_n(text, result)

    # Section M: Built-in gain
    if re.search(r'built-?in\s+gain.*?Yes', text, re.IGNORECASE):
        result['built_in_gain'] = True
    elif re.search(r'built-?in\s+gain.*?No', text, re.IGNORECASE):
        result['built_in_gain'] = False

    logger.debug("Partner info: tin=%s, name=%s, profit_pct=%s/%s",
                 result['tin'], result['name'],
                 result['profit_beginning_pct'], result['profit_ending_pct'])
    return result


def _parse_section_j(text, result):
    """Parse Section J: Profit/Loss/Capital percentages (Beginning/Ending).

    Tries multiple strategies since K-1 formats vary widely:
    1. Label + two percentages on the same line
    2. Table-style: label in one cell, percentages in adjacent cells
    3. Generic: find a block of 6 percentages near "Profit" / "Loss" / "Capital"
    """
    pct_patterns = [
        ('profit', 'profit_beginning_pct', 'profit_ending_pct'),
        ('loss', 'loss_beginning_pct', 'loss_ending_pct'),
        ('capital', 'capital_beginning_pct', 'capital_ending_pct'),
    ]

    # Strategy 1: label followed by two numbers on same or adjacent lines
    for label, beg_key, end_key in pct_patterns:
        match = re.search(
            rf'{label}[:\s]*(\d+\.?\d*)\s*%?\s+(\d+\.?\d*)\s*%?',
            text, re.IGNORECASE
        )
        if match:
            result[beg_key] = _parse_percentage(match.group(1))
            result[end_key] = _parse_percentage(match.group(2))
            logger.debug("Section J %s matched (strategy 1): %s / %s", label, match.group(1), match.group(2))

    # Strategy 2: look for "Beginning" and "Ending" column headers followed by rows
    if result['profit_beginning_pct'] is None:
        j_block = re.search(
            r'(?:J\s+|[Pp]artner.?s?\s+share).*?(?:Beginning|Beg\.?).*?((?:\d+\.?\d*\s*%?\s*)+)',
            text, re.DOTALL | re.IGNORECASE
        )
        if j_block:
            nums = re.findall(r'(\d+\.?\d*)\s*%?', j_block.group(1))
            logger.debug("Section J strategy 2 found %d numbers: %s", len(nums), nums[:10])
            if len(nums) >= 6:
                pairs = list(zip(nums[0::2], nums[1::2]))
                for i, (_, beg_key, end_key) in enumerate(pct_patterns):
                    if i < len(pairs):
                        result[beg_key] = _parse_percentage(pairs[i][0])
                        result[end_key] = _parse_percentage(pairs[i][1])


def _parse_section_k(text, result):
    """Parse Section K: Partner's share of liabilities.

    Handles formats like:
      Nonrecourse . . $ 498,211 $
      Nonrecourse: 498,211  0
    Searches all occurrences and picks the one with actual data (page 1 is
    typically empty form labels, page 2 has the values).
    """
    liability_patterns = [
        (r'[Nn]onrecourse\b(?!\s*(?:financing|[Qq]ualified))', 'nonrecourse_beginning', 'nonrecourse_ending'),
        (r'[Qq]ualified\s+nonrecourse', 'qualified_nonrecourse_beginning', 'qualified_nonrecourse_ending'),
        (r'(?<!non)[Rr]ecourse\b', 'recourse_beginning', 'recourse_ending'),
    ]
    for pattern, beg_key, end_key in liability_patterns:
        best_beg = None
        best_end = None

        # Strategy 1: "label . . $ amount $" with $ delimiters
        for m in re.finditer(
            rf'{pattern}[^\n]*?\$\s*([\d,.-]+)?\s*\$\s*([\d,.-]+)?',
            text, re.IGNORECASE
        ):
            beg_raw = m.group(1)
            end_raw = m.group(2)
            beg_val = _parse_currency(beg_raw) if beg_raw else Decimal('0')
            end_val = _parse_currency(end_raw) if end_raw else Decimal('0')
            if beg_val is not None and (best_beg is None or abs(beg_val) > abs(best_beg or 0)):
                best_beg = beg_val
                best_end = end_val

        if best_beg is not None and abs(best_beg) > 0:
            result[beg_key] = best_beg
            result[end_key] = best_end
            continue

        # Strategy 2: label followed by two amounts without $ signs
        for m in re.finditer(
            rf'{pattern}[:\s\.]+(\d[\d,.]*)\s+(\d[\d,.]*)',
            text, re.IGNORECASE
        ):
            beg_val = _parse_currency(m.group(1))
            end_val = _parse_currency(m.group(2))
            if beg_val is not None and (best_beg is None or abs(beg_val) > abs(best_beg or 0)):
                best_beg = beg_val
                best_end = end_val

        if best_beg is not None:
            result[beg_key] = best_beg
            result[end_key] = best_end

    # K2: Lower tier liabilities
    if re.search(r'lower\s+tier.*?(?:\[?[xX✓]\]?|Yes)', text, re.IGNORECASE):
        result['has_lower_tier_liabilities'] = True
    # K3: Guarantee obligations
    if re.search(r'guarantee.*?obligation.*?(?:\[?[xX✓]\]?|Yes)', text, re.IGNORECASE):
        result['has_guarantee_obligations'] = True


def _parse_section_n(text, result):
    """Parse Section N: Net Unrecognized Section 704(c) Gain or Loss."""
    match = re.search(
        r'704\(?c\)?[:\s]*(?:gain|loss)?[:\s]*([\d,$.()-]+)\s+([\d,$.()-]+)',
        text, re.IGNORECASE
    )
    if match:
        result['section_704c_beginning'] = _parse_currency(match.group(1))
        result['section_704c_ending'] = _parse_currency(match.group(2))


# ---------------------------------------------------------------------------
# Part III: Income Items
# ---------------------------------------------------------------------------

# Standard K-1 line descriptions
LINE_DESCRIPTIONS = {
    '1': 'Ordinary business income (loss)',
    '2': 'Net rental real estate income (loss)',
    '3': 'Other net rental income (loss)',
    '4a': 'Guaranteed payments for services',
    '4b': 'Guaranteed payments for capital',
    '4c': 'Total guaranteed payments',
    '5': 'Interest income',
    '6a': 'Ordinary dividends',
    '6b': 'Qualified dividends',
    '6c': 'Dividend equivalents',
    '7': 'Royalties',
    '8': 'Net short-term capital gain (loss)',
    '9a': 'Net long-term capital gain (loss)',
    '9b': 'Collectibles (28%) gain (loss)',
    '9c': 'Unrecaptured section 1250 gain',
    '10': 'Net section 1231 gain (loss)',
    '11': 'Other income (loss)',
    '12': 'Section 179 deduction',
    '13': 'Other deductions',
    '14': 'Self-employment earnings (loss)',
    '15': 'Credits',
    '16': 'Foreign transactions',
    '17': 'Alternative minimum tax (AMT) items',
    '18': 'Tax-exempt income and nondeductible expenses',
    '19': 'Distributions',
    '20': 'Other information',
    '21': 'More information',
    '22': 'More information',
    '23': 'More information',
}

# Lines that use letter codes (multi-code lines)
MULTI_CODE_LINES = {'11', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23'}

# Words that look like 1-3 letter codes but are actually description words
_CODE_BLACKLIST = {
    'NET', 'TAX', 'AMT', 'THE', 'AND', 'FOR', 'NOT', 'ALL', 'ANY', 'ARE',
    'WAS', 'HAS', 'HAD', 'DID', 'SEE', 'USE', 'MAY', 'DUE', 'IRS', 'PER',
    'IF', 'IS', 'OF', 'OR', 'TO', 'AT', 'BY', 'IN', 'ON', 'NO', 'DO',
}


def parse_income_items(text):
    """Extract Part III income items from K-1 text.

    Returns list of dicts with keys: line_number, code, description, amount,
    raw_text, is_supplemental.

    Uses multiple strategies to extract line items since K-1 PDF layouts vary
    significantly. Real K-1 PDFs often split line number, code, and amount
    across separate text lines.
    """
    items = []
    found_keys = set()  # "line_num:code" to deduplicate

    lines_text = text.split('\n')

    def _add_item(line_num, code, amount_str, is_supp=False):
        key = f"{line_num}:{code or ''}"
        if key in found_keys:
            return
        amount = _parse_currency(amount_str) if amount_str and not is_supp else None
        items.append({
            'line_number': line_num,
            'code': code or None,
            'description': LINE_DESCRIPTIONS.get(line_num, ''),
            'amount': amount,
            'raw_text': amount_str or '',
            'is_supplemental': is_supp,
        })
        found_keys.add(key)

    for i, line in enumerate(lines_text):
        line = line.strip()
        if not line:
            continue

        # Pattern 1: "19  A  4,493,757" — all on one line (line_num + code + amount)
        multi_match = re.match(
            r'^(\d+)\s+([A-Z]{1,3}\*?)\s+([-]?[\d,$.()-]+|SEE\s+STMT|STMT)\s*$',
            line, re.IGNORECASE
        )
        if multi_match:
            line_num = multi_match.group(1)
            code = multi_match.group(2).upper()
            raw = multi_match.group(3)
            if code not in _CODE_BLACKLIST:
                is_supp = bool(re.match(r'SEE|STMT', raw, re.IGNORECASE))
                _add_item(line_num, code, raw, is_supp)
                continue

        # Pattern 2: "11  ZZ*  Other income (loss)  (409,615)" — line with description+amount
        labeled_match = re.match(
            r'^(\d+)\s+([A-Z]{1,3}\*?)\s+.+?\s{2,}([-]?[\d,$.()-]+|SEE\s+STMT)\s*$',
            line, re.IGNORECASE
        )
        if labeled_match:
            line_num = labeled_match.group(1)
            code = labeled_match.group(2).upper()
            raw = labeled_match.group(3)
            if code not in _CODE_BLACKLIST:
                is_supp = bool(re.match(r'SEE|STMT', raw, re.IGNORECASE))
                _add_item(line_num, code, raw, is_supp)
                continue

        # Pattern 3: Single-value line "1  Ordinary business income (loss)  12345"
        # Must ensure the trailing number is a real amount, not a line label
        single_match = re.match(
            r'^(\d+[a-c]?)\s{2,}.*?\s{2,}([-]?[\d,]+\.?\d{0,2}|\([\d,.]+\))\s*$',
            line
        )
        if single_match:
            line_num = single_match.group(1)
            amount_str = single_match.group(2)
            # Validate: recognized line, NOT multi-code, amount not a known line number
            if line_num in LINE_DESCRIPTIONS and line_num not in MULTI_CODE_LINES:
                # Reject if the "amount" is itself a known K-1 line number (1-23)
                stripped = amount_str.replace(',', '').replace('.', '').lstrip('0') or '0'
                if stripped in LINE_DESCRIPTIONS:
                    continue
                amount = _parse_currency(amount_str)
                if amount is not None and abs(amount) >= 100:
                    _add_item(line_num, None, amount_str)
                    continue

        # Pattern 4: Multi-line format (common in real K-1 PDFs):
        #   19              ← line number alone
        #   A  Distributions ← code + description
        #   4,493,757       ← amount alone (or with trailing code like "V  SEE STMT")
        # Look for line starting with an amount and trace back for line_num + code
        amount_leading = re.match(r'^([-]?[\d,]+\.?\d*|\([\d,.]+\))(?:\s|$)', line)
        if amount_leading and i >= 1:
            amount_str = amount_leading.group(1)
            amount = _parse_currency(amount_str)
            if amount is not None and abs(amount) >= 1:
                # Look backward for code + line number
                code_found = None
                line_num_found = None
                for j in range(i - 1, max(i - 5, -1), -1):
                    prev = lines_text[j].strip()
                    if not prev:
                        continue
                    # Check for "A  Description" or just "A" (single letter code)
                    code_match = re.match(r'^([A-Z]{1,3}\*?)\s', prev)
                    if code_match and code_found is None:
                        candidate_code = code_match.group(1).upper()
                        if candidate_code not in _CODE_BLACKLIST:
                            code_found = candidate_code
                            continue
                    # Check for standalone line number
                    lnum_match = re.match(r'^(\d+)\s*$', prev)
                    if lnum_match and line_num_found is None:
                        candidate = lnum_match.group(1)
                        if candidate in LINE_DESCRIPTIONS:
                            line_num_found = candidate
                            break
                if line_num_found:
                    _add_item(line_num_found, code_found, amount_str)

        # Pattern 5: Standalone "A  SEE STMT" or "A  (amount)" on its own line
        code_val_match = re.match(
            r'^([A-Z]{1,3}\*?)\s+([-]?[\d,$.()-]+|SEE\s+STMT|STMT)\s*$',
            line, re.IGNORECASE
        )
        if code_val_match and i > 0:
            code = code_val_match.group(1).upper()
            raw = code_val_match.group(2)
            if code not in _CODE_BLACKLIST:
                is_supp = bool(re.match(r'SEE|STMT', raw, re.IGNORECASE))
                # Look backward for line number
                for j in range(max(0, i - 4), i):
                    prev = lines_text[j].strip()
                    lnum_match = re.match(r'^(\d+)\s*$', prev)
                    if lnum_match:
                        line_num = lnum_match.group(1)
                        if line_num in LINE_DESCRIPTIONS:
                            _add_item(line_num, code, raw, is_supp)
                            break

        # Pattern 6: "SEE STMT" or "STMT" alone on a line — supplemental reference
        # Look backward for code and line number
        stmt_match = re.match(r'^(SEE\s+STMT|STMT)\s*$', line, re.IGNORECASE)
        if stmt_match and i > 0:
            stmt_code = None
            stmt_lnum = None
            for j in range(i - 1, max(i - 5, -1), -1):
                prev = lines_text[j].strip()
                if not prev:
                    continue
                code_match = re.match(r'^([A-Z]{1,3}\*?)\s', prev)
                if code_match and stmt_code is None:
                    c = code_match.group(1).upper()
                    if c not in _CODE_BLACKLIST:
                        stmt_code = c
                        continue
                lnum_match = re.match(r'^(\d+)\s*$', prev)
                if lnum_match and stmt_lnum is None:
                    if lnum_match.group(1) in LINE_DESCRIPTIONS:
                        stmt_lnum = lnum_match.group(1)
                        break
            if stmt_lnum and stmt_code:
                _add_item(stmt_lnum, stmt_code, stmt_match.group(1), True)

    items.sort(key=lambda x: (
        x['line_number'].rjust(3, '0'),
        x['code'] or '',
    ))

    logger.info("Parsed %d income items: %s", len(items),
                ', '.join(f"L{it['line_number']}{it.get('code') or ''}" for it in items[:15]))
    return items


# ---------------------------------------------------------------------------
# Section L: Capital Account
# ---------------------------------------------------------------------------

def parse_capital_account(text):
    """Extract Section L: Partner's Capital Account Analysis.

    Returns dict matching K1CapitalAccount model fields.
    """
    result = {
        'beginning_balance': None,
        'capital_contributed': None,
        'net_income': None,
        'other_increase_decrease': None,
        'withdrawals': None,
        'ending_balance': None,
        'tax_basis_method': '',
    }

    # Find ALL occurrences of Section L and pick the one with actual data
    # (pdfplumber often extracts the empty form labels first, data second)
    section_matches = list(re.finditer(
        r'(?:capital\s+account\s+analysis|Section\s+L)(.*?)(?=(?:capital\s+account\s+analysis|Section\s+L|Section\s+[MN]|built-?in\s+gain|704\(c\)|For\s+Paperwork))',
        text, re.DOTALL | re.IGNORECASE
    ))

    # Also try matching to end of text for the last occurrence
    last_match = re.search(
        r'(?:capital\s+account\s+analysis|Section\s+L)(.*?)(?:built-?in\s+gain|704\(c\)|For\s+Paperwork|$)',
        text, re.DOTALL | re.IGNORECASE
    )

    # Collect all candidate sections and pick the one with the most dollar amounts
    candidates = [m.group(1) for m in section_matches]
    if last_match:
        candidates.append(last_match.group(1))

    best_section = ''
    best_count = 0
    for cand in candidates:
        count = len(re.findall(r'[\d,]+\.?\d{0,2}', cand))
        if count > best_count:
            best_count = count
            best_section = cand

    search_text = best_section if best_section else text

    logger.debug("Capital account section has %d numeric tokens in %d chars",
                 best_count, len(search_text))

    # Labeled extraction — match the standard K-1 Section L format:
    #   "Beginning capital account . . . $ 4,903,568"
    label_patterns = [
        (r'[Bb]eginning\s+capital.*?\$\s*([-]?[\d,]+\.?\d*|\([\d ,.]+\))', 'beginning_balance'),
        (r'[Cc]apital\s+contributed.*?\$\s*([-]?[\d,]+\.?\d*|\([\d ,.]+\))', 'capital_contributed'),
        (r'(?:[Cc]urrent\s+year\s+)?[Nn]et\s+income.*?\$\s*([-]?[\d,]+\.?\d*|\([\d ,.]+\))', 'net_income'),
        (r'[Oo]ther\s+(?:increase|decrease).*?\$\s*([-]?[\d,]+\.?\d*|\([\d ,.]+\))', 'other_increase_decrease'),
        (r'[Ww]ithdrawals?\s+(?:and|&)\s+dist.*?\$\(?\s*([-]?[\d, ]+\.?\d*)\)?\s*', 'withdrawals'),
        (r'[Ee]nding\s+capital.*?\$\s*([-]?[\d,]+\.?\d*|\([\d ,.]+\))', 'ending_balance'),
    ]
    for pattern, key in label_patterns:
        m = re.search(pattern, search_text, re.IGNORECASE)
        if m:
            raw = m.group(1).replace(' ', '')  # Handle spaced numbers like "4 , 4 9 3 , 7 5 7"
            val = _parse_currency(raw)
            if val is not None:
                # Withdrawals are typically shown as positive in parens but should be negative
                if key == 'withdrawals' and val > 0 and '(' in m.group(0):
                    val = -val
                result[key] = val
                logger.debug("Capital %s = %s (from: %s)", key, val, m.group(0)[:50])

    # Fallback: if labeled extraction found nothing, try positional
    filled = sum(1 for v in result.values() if v is not None and v != '')
    if filled == 0:
        amounts = re.findall(r'([-]?[\d,]+\.?\d*|\([\d,.]+\))', search_text)
        currency_amounts = []
        for a in amounts:
            val = _parse_currency(a)
            if val is not None and abs(val) > 0:
                currency_amounts.append(val)

        if len(currency_amounts) >= 4:
            result['beginning_balance'] = currency_amounts[0]
            if len(currency_amounts) >= 2:
                result['capital_contributed'] = currency_amounts[1]
            if len(currency_amounts) >= 3:
                result['net_income'] = currency_amounts[2]
            if len(currency_amounts) >= 4:
                result['other_increase_decrease'] = currency_amounts[3]
            if len(currency_amounts) >= 5:
                result['withdrawals'] = currency_amounts[4]
            if len(currency_amounts) >= 6:
                result['ending_balance'] = currency_amounts[5]

    # Tax basis method
    if re.search(r'Tax\s+basis', search_text, re.IGNORECASE):
        result['tax_basis_method'] = 'Tax basis'
    elif re.search(r'GAAP', search_text):
        result['tax_basis_method'] = 'GAAP'
    elif re.search(r'704\s*\(b\)', search_text):
        result['tax_basis_method'] = 'Section 704(b)'

    logger.debug("Capital account result: beg=%s end=%s", result['beginning_balance'], result['ending_balance'])
    return result


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def parse_k1_document(file_path):
    """Parse a K-1 PDF document and return all extracted data.

    Args:
        file_path: Path to the PDF file.

    Returns:
        dict with keys:
            - extraction_method: 'text' or 'ocr'
            - tax_year: int or None
            - is_final: bool
            - is_amended: bool
            - partnership_info: dict
            - partner_info: dict
            - income_items: list of dicts
            - capital_account: dict
            - warnings: list of str
            - raw_text: str (first 5000 chars for debug)
    """
    full_text, extraction_method = extract_text_from_pdf(file_path)
    warnings = []

    if not full_text.strip():
        raise ValueError("Could not extract any text from the PDF.")

    # Check this looks like a K-1
    if not re.search(r'K-?1|1065|Schedule\s+K|Partner.?s?\s+Share', full_text[:3000], re.IGNORECASE):
        raise ValueError("Could not recognize this document as a Schedule K-1 (Form 1065).")

    # Parse each section, catching individual failures
    try:
        partnership_info, header = parse_partnership_info(full_text)
    except Exception as e:
        logger.warning("Partnership info parsing failed: %s", e)
        partnership_info = {'ein': '', 'name': '', 'address': '', 'city': '', 'state': '', 'zip_code': '', 'irs_center': '', 'is_ptp': False}
        header = {'tax_year': None, 'is_final': False, 'is_amended': False}
        warnings.append(f"Partnership info extraction failed: {e}")

    try:
        partner_info = parse_partner_info(full_text)
    except Exception as e:
        logger.warning("Partner info parsing failed: %s", e)
        partner_info = {'tin': '', 'name': ''}
        warnings.append(f"Partner info extraction failed: {e}")

    try:
        income_items = parse_income_items(full_text)
    except Exception as e:
        logger.warning("Income items parsing failed: %s", e)
        income_items = []
        warnings.append(f"Income items extraction failed: {e}")

    try:
        capital_account = parse_capital_account(full_text)
    except Exception as e:
        logger.warning("Capital account parsing failed: %s", e)
        capital_account = {}
        warnings.append(f"Capital account extraction failed: {e}")

    # Generate warnings for supplemental items
    for item in income_items:
        if item.get('is_supplemental'):
            warnings.append(
                f"Line {item['line_number']} code {item.get('code', '?')} references "
                f"supplemental statement - manual entry may be needed"
            )

    # Warn if key fields are empty — user should fill manually
    if not partnership_info.get('name'):
        warnings.append("Partnership name was not extracted — please enter manually.")
    if not income_items:
        warnings.append("No income items were extracted — add them manually on the review page.")

    return {
        'extraction_method': extraction_method,
        'tax_year': header.get('tax_year'),
        'is_final': header.get('is_final', False),
        'is_amended': header.get('is_amended', False),
        'partnership_info': partnership_info,
        'partner_info': partner_info,
        'income_items': income_items,
        'capital_account': capital_account,
        'warnings': warnings,
        'raw_text': full_text[:5000],
    }

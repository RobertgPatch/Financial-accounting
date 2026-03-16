# Phase 0 Research: K-1 PDF Extraction Library Comparison

**Feature**: 004-k1-pdf-ingestion | **Date**: 2026-03-04  
**Goal**: Select the best Python PDF text extraction library for parsing IRS Schedule K-1 (Form 1065) documents in a Django/Docker environment.

---

## 1. K-1 Document Characteristics

Before comparing libraries, it's important to understand what we're parsing:

| Property | K-1 Detail |
|----------|-----------|
| **Form structure** | Fixed-position IRS form with labeled boxes (Part I, II, III + lines 1–20+) |
| **Page count** | 1–2 pages base form + 0–5 supplemental statement pages |
| **Data types** | EINs (XX-XXXXXXX), percentages (XX.XXXX%), monetary values ($X,XXX.XX), checkboxes, dates, text labels |
| **Tables** | Section L (Capital Account Analysis) is a true table; Lines 1–20 are labeled rows with amount columns |
| **Generation** | ~90% digitally generated (tax software: TurboTax, Drake, UltraTax), ~10% scanned images |
| **Typical file size** | 50KB–2MB |

Key extraction challenges:
- **Positional awareness** is critical: K-1 fields are identified by their (x, y) position on the page, not by parsing running text
- **Two-column layout**: Lines 1–11 on the left, Lines 12–20 on the right
- **Coded items**: Lines 11, 13, 17, 18, 20 use letter codes (e.g., "A", "B", "C") with amounts
- **Supplemental statements**: Often reference "SEE STMT" with details on subsequent pages

---

## 2. Library Comparison Matrix

### 2.1 pdfplumber

| Criterion | Assessment |
|-----------|-----------|
| **What it is** | High-level PDF text and table extraction built on top of pdfminer.six |
| **Installation** | `pip install pdfplumber` — pure Python + pdfminer.six dependency. No system packages needed. |
| **Docker complexity** | **Trivial** — no extra `apt-get` packages. Works with `python:3.12-slim` as-is. |
| **Positional text extraction** | **Excellent** — `page.chars` returns every character with `x0, y0, x1, y1, top, bottom` coordinates. `page.extract_words()` groups characters into words with bounding boxes. Can filter text by region with `page.crop(bbox).extract_text()`. |
| **Table extraction** | **Very good** — `page.extract_tables()` uses visual line detection to find table structures. Works well for ruled tables like Section L. Also supports `table_settings` for fine-tuning. |
| **Performance** | Moderate — Python-based, ~1–3 seconds per page. For a 5-page K-1, expect 3–10 seconds total. Well within our 30-second budget. |
| **API quality** | **Excellent** — intuitive, well-documented. Cropping to bounding boxes is a first-class feature, which is ideal for extracting K-1 boxes by position. |
| **Maintenance** | Active. Last release: v0.11.4 (2024). GitHub: ~6k stars, regular commits. Maintained by Jeremy Singer-Vine (formerly BuzzFeed News data team). |
| **License** | MIT — fully compatible. |
| **K-1 fit** | **Best fit.** The `page.crop()` API maps directly to "extract the value from Box 1 at coordinates (x0, y0, x1, y1)". |

**K-1 extraction pattern with pdfplumber:**
```python
import pdfplumber

with pdfplumber.open("k1.pdf") as pdf:
    page = pdf.pages[0]
    
    # Extract partnership name from a known bounding box
    partnership_box = page.crop((72, 100, 350, 130))
    partnership_name = partnership_box.extract_text()
    
    # Extract Section L capital account table
    tables = page.extract_tables()
    
    # Get all words with positions for debugging
    words = page.extract_words(keep_blank_chars=True)
    for w in words:
        print(f"{w['text']} at ({w['x0']:.0f}, {w['top']:.0f})")
```

---

### 2.2 PyMuPDF (fitz)

| Criterion | Assessment |
|-----------|-----------|
| **What it is** | Python binding for MuPDF, a lightweight C-based PDF/XPS renderer |
| **Installation** | `pip install PyMuPDF` — ships pre-compiled wheels for Linux x86_64. |
| **Docker complexity** | **Low** — wheels are self-contained. No extra system packages for basic text extraction. If rendering to images (for OCR fallback), needs no additional deps. |
| **Positional text extraction** | **Excellent** — `page.get_text("dict")` returns blocks/lines/spans with full bounding box data. `page.get_text("words")` returns words with `(x0, y0, x1, y1)` tuples. Can extract text from a rect with `page.get_textbox(rect)`. |
| **Table extraction** | **Limited natively** — no built-in table detection. As of v1.23+, there is experimental `page.find_tables()` API, but it's less mature than pdfplumber's. Would need manual grid detection or pairing with another library. |
| **Performance** | **Fastest** — C-based, ~10–50x faster than pdfminer.six. Processes pages in milliseconds. Overkill for our scale (10–50 K-1s/year) but leaves plenty of headroom. |
| **API quality** | Good but lower-level. The dict-based output requires more post-processing to group text by regions. Less intuitive than pdfplumber's crop API. |
| **Maintenance** | Very active. Frequent releases (monthly). GitHub: ~5k stars. Maintained by Artifex (MuPDF creators). |
| **License** | **AGPL-3.0** (since v1.24.2, Sep 2024). Previously had a more permissive option. AGPL requires source disclosure if the software is offered as a network service. Since we deploy this as a web app (Railway), **AGPL may require open-sourcing the entire codebase** unless we purchase a commercial license from Artifex. |
| **K-1 fit** | Strong technically, but **license risk is a concern** for a deployed web application. |

**License note:** PyMuPDF's AGPL license is a significant consideration. If this project is ever closed-source or commercially deployed, AGPL compliance would require either open-sourcing the full application or purchasing a commercial license. pdfplumber's MIT license has no such constraint.

---

### 2.3 pdfminer.six

| Criterion | Assessment |
|-----------|-----------|
| **What it is** | Pure Python PDF parser, community-maintained fork of PDFMiner. Low-level text extraction engine. |
| **Installation** | `pip install pdfminer.six` — pure Python, no system deps. |
| **Docker complexity** | **Trivial** — pure Python. |
| **Positional text extraction** | **Excellent (but verbose)** — provides `LTChar`, `LTTextLine`, `LTTextBox` objects with full coordinate data. This is the most granular positional data available in any Python PDF library. pdfplumber is actually built on top of this. |
| **Table extraction** | **None** — no table detection at all. Would need to build table extraction logic from raw character positions manually. |
| **Performance** | **Slow** — pure Python, no C extensions. 2–5x slower than pdfplumber (which adds caching/optimization on top). |
| **API quality** | **Poor for this use case** — very low-level, callback-based API. Requires writing significant boilerplate to aggregate characters into useful text regions. pdfplumber exists specifically because pdfminer.six's API is cumbersome. |
| **Maintenance** | Maintained but slow cadence. Last release: 2024. Community-maintained fork. |
| **License** | MIT — fully compatible. |
| **K-1 fit** | **Not recommended directly.** pdfplumber provides a better API on top of the same engine. Using pdfminer.six directly means reimplementing what pdfplumber already provides. |

---

### 2.4 Camelot

| Criterion | Assessment |
|-----------|-----------|
| **What it is** | Specialized library for extracting tables from PDFs. Two modes: Lattice (for ruled tables) and Stream (for whitespace-separated tables). |
| **Installation** | `pip install camelot-py[cv]` — requires **Ghostscript** and **OpenCV** as system dependencies. |
| **Docker complexity** | **High** — requires `apt-get install ghostscript` and OpenCV native libs. Adds ~200MB+ to Docker image. Ghostscript has had CVE security issues. |
| **Positional text extraction** | **None** — Camelot is table-only. Cannot extract arbitrary text by position. Would need to pair with another library (pdfplumber or pdfminer) for non-table K-1 fields. |
| **Table extraction** | **Excellent** — best-in-class for complex tables with merged cells, multi-line content. Lattice mode is very accurate for ruled tables. |
| **Performance** | Slow — Ghostscript rendering + OpenCV processing. Several seconds per table. |
| **Maintenance** | **Stale** — last PyPI release was 2023. GitHub activity has slowed significantly. Forks exist (e.g., `camelot-py` vs `camelot`). |
| **License** | MIT — compatible. |
| **K-1 fit** | **Poor fit as sole library.** Only handles tables, not the bulk of K-1 fields. Adding it as a table supplement alongside pdfplumber isn't worth the Docker image bloat, given pdfplumber's table extraction is sufficient for Section L. |

---

### 2.5 tabula-py

| Criterion | Assessment |
|-----------|-----------|
| **What it is** | Python wrapper for tabula-java, a Java-based table extraction tool. |
| **Installation** | `pip install tabula-py` — requires **Java JRE** (OpenJDK 8+) on the system. |
| **Docker complexity** | **Very high** — requires installing JDK in the Docker image. Adds ~300–400MB. Contradicts the constraint of no Java. |
| **Positional text extraction** | **None** — table extraction only, same limitation as Camelot. |
| **Table extraction** | **Very good** — reliable for clean tables. |
| **Performance** | Moderate — JVM startup adds latency (~2–3 seconds cold start). |
| **Maintenance** | Active. Regular releases. |
| **License** | MIT — compatible. |
| **K-1 fit** | **Disqualified** — requires Java. Explicitly excluded by requirements. |

---

## 3. Summary Comparison Table

| Feature | pdfplumber | PyMuPDF | pdfminer.six | Camelot | tabula-py |
|---------|-----------|---------|-------------|---------|----------|
| **Positional text** | ✅ Excellent | ✅ Excellent | ✅ Excellent (verbose) | ❌ None | ❌ None |
| **Table extraction** | ✅ Good | ⚠️ Experimental | ❌ None | ✅ Excellent | ✅ Very good |
| **Region cropping** | ✅ First-class | ✅ Good | ⚠️ Manual | ❌ N/A | ❌ N/A |
| **Docker deps** | None | None | None | Ghostscript + OpenCV | Java JDK |
| **Docker image impact** | +0 MB | +0 MB | +0 MB | +200 MB | +400 MB |
| **Performance** | ~2s/page | ~0.05s/page | ~5s/page | ~3s/table | ~3s/table + JVM |
| **API simplicity** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **License** | MIT ✅ | AGPL ⚠️ | MIT ✅ | MIT ✅ | MIT ✅ |
| **Maintenance** | Active ✅ | Very active ✅ | Slow ⚠️ | Stale ⚠️ | Active ✅ |
| **K-1 suitability** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ❌ Disqualified |

---

## 4. OCR Fallback Comparison: pytesseract vs EasyOCR

For scanned K-1 images (~10% of uploads), an OCR fallback is needed.

### 4.1 pytesseract

| Criterion | Assessment |
|-----------|-----------|
| **What it is** | Python wrapper for Google's Tesseract OCR engine (C++) |
| **Installation** | `pip install pytesseract Pillow` + `apt-get install tesseract-ocr` |
| **Docker impact** | ~30–50 MB for the Tesseract engine + English language data |
| **Accuracy** | Good for printed text (IRS forms are clean, fixed-font). Tesseract 5 with LSTM engine handles K-1 text well. |
| **Positional data** | ✅ `image_to_data()` returns word-level bounding boxes with confidence scores — critical for mapping OCR output back to K-1 field positions |
| **Speed** | Fast — ~1–3 seconds per page for a standard K-1 scan at 300 DPI |
| **GPU required** | No — CPU only |
| **Memory** | Low — ~100–200 MB RAM |
| **License** | Apache 2.0 — fully compatible |
| **Maturity** | 20+ years of development. Industry standard. Tesseract 5.x is current. |

### 4.2 EasyOCR

| Criterion | Assessment |
|-----------|-----------|
| **What it is** | Deep learning-based OCR using PyTorch (CRAFT text detection + CRNN recognition) |
| **Installation** | `pip install easyocr` — pulls in PyTorch (~700 MB–2 GB), torchvision, and model weights |
| **Docker impact** | **Massive** — 1.5–2.5 GB for PyTorch + models. Would 3–4x our Docker image size. |
| **Accuracy** | Excellent for varied fonts, handwriting, multi-language. For clean printed IRS forms, marginal improvement over Tesseract. |
| **Positional data** | ✅ Returns bounding boxes with text and confidence |
| **Speed** | Slower on CPU (~5–15 seconds per page). Fast on GPU but we don't have GPU in Docker/Railway. |
| **GPU required** | Not required but strongly recommended. CPU inference is significantly slower. |
| **Memory** | High — 1–2 GB RAM for model loading |
| **License** | Apache 2.0 — compatible |
| **Maturity** | Newer (2020+). Active development but less battle-tested than Tesseract. |

### 4.3 OCR Comparison Summary

| Factor | pytesseract | EasyOCR |
|--------|------------|---------|
| Docker image size impact | +50 MB | +2,000 MB |
| RAM usage | ~200 MB | ~1.5 GB |
| Speed (CPU, per page) | 1–3 sec | 5–15 sec |
| Accuracy (printed IRS forms) | Very good | Slightly better |
| Positional data | ✅ | ✅ |
| Setup complexity | Low (1 apt package) | Medium (PyTorch) |
| **Verdict for K-1** | **Winner** | Overkill |

**Rationale**: EasyOCR's deep learning approach offers marginal accuracy gains on clean, printed IRS forms but at an enormous cost (~2 GB Docker image bloat, 5x slower without GPU, high RAM). pytesseract is the clear choice for our constrained Docker environment. K-1 forms are professionally typeset with standard fonts — exactly the domain where Tesseract excels.

---

## 5. Recommended Architecture

### Primary: pdfplumber (text-layer PDFs)

```
PDF Upload → Detect text layer → pdfplumber extracts characters with (x,y) positions
           → Map coordinates to K-1 field definitions (box boundaries)  
           → Parse values (EIN regex, currency parsing, percentage parsing)
           → Return structured K-1 data dict
```

### Fallback: pytesseract (scanned image PDFs)

```
PDF Upload → Text layer empty/sparse → Convert pages to images (pdfplumber or Pillow)
           → pytesseract.image_to_data() → words with bounding boxes
           → Same coordinate-to-field mapping as above
           → Flag as "OCR-extracted, review carefully"
```

### Detection logic:

```python
import pdfplumber

def has_text_layer(pdf_path: str) -> bool:
    """Check if PDF has extractable text or is a scanned image."""
    with pdfplumber.open(pdf_path) as pdf:
        if not pdf.pages:
            return False
        first_page = pdf.pages[0]
        text = first_page.extract_text() or ""
        # K-1 forms should have substantial text; threshold filters out
        # PDFs with only a few stray characters from image metadata
        return len(text.strip()) > 100
```

---

## 6. Final Recommendation

### Primary extraction: **pdfplumber**

| Factor | Rationale |
|--------|-----------|
| **Best API for K-1 parsing** | `page.crop(bbox)` maps 1:1 to "extract value from K-1 Box N at position (x0, y0, x1, y1)". No other library makes region-based extraction this clean. |
| **Zero Docker overhead** | Pure Python install. No system packages, no image bloat. Fits our slim Docker image. |
| **Built-in table extraction** | Handles Section L (Capital Account Analysis) without adding a second library. |
| **MIT license** | No AGPL concerns for deployed web applications. No commercial license needed. |
| **Active maintenance** | Regular releases, responsive maintainer, large user base (6k+ GitHub stars). |
| **Performance is sufficient** | ~2s/page means a 5-page K-1 processes in ~10 seconds, well within our 30-second target. We're processing 10–50 K-1s/year, not thousands per hour. |

### OCR fallback: **pytesseract + Pillow**

| Factor | Rationale |
|--------|-----------|
| **Minimal Docker footprint** | +50 MB vs +2 GB for EasyOCR |
| **Excellent for printed forms** | Tesseract 5 LSTM handles clean IRS typography with high accuracy |
| **Positional output** | `image_to_data()` provides word-level bounding boxes, enabling the same coordinate-based field mapping as pdfplumber |
| **Industry standard** | 20+ years of development, widely deployed, well-documented |

### Dockerfile additions needed:

```dockerfile
# For pytesseract OCR fallback (scanned K-1s)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*
```

### requirements.txt additions:

```
pdfplumber>=0.10,<1.0
pytesseract>=0.3.10,<1.0
Pillow>=10.0,<11.0
```

### Why not PyMuPDF?

Despite being faster and having excellent positional extraction, PyMuPDF's **AGPL license** is a dealbreaker for a web application deployed on Railway. AGPL would require open-sourcing the entire codebase or purchasing a commercial license from Artifex. pdfplumber's MIT license avoids this entirely, and its API is better suited for the K-1 region-extraction pattern.

### Why not Camelot + pdfplumber combo?

Adding Camelot for its superior table extraction isn't justified because:
1. K-1's Section L is a simple ruled table that pdfplumber handles well
2. Camelot adds Ghostscript + OpenCV to the Docker image (+200 MB)
3. Two extraction libraries increases maintenance burden
4. Camelot's development has stalled

---

## 7. Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| K-1 field positions vary between tax software vendors (Drake vs UltraTax vs TurboTax) | **High** | Define field regions with tolerance margins. Build calibration by detecting form anchor points (e.g., "Schedule K-1" header position, box borders) and adjusting coordinates relative to anchors. |
| pdfplumber table extraction fails on poorly formatted Section L | **Low** | Fall back to positional text extraction for table cells individually. |
| Scanned K-1 has low resolution, pytesseract produces errors | **Medium** | Flag OCR-extracted K-1s for mandatory user review. Show confidence scores. Pre-process images (deskew, contrast enhancement via Pillow) before OCR. |
| pdfplumber project becomes unmaintained | **Low** | Built on pdfminer.six, so the underlying engine would persist. Could migrate to raw pdfminer.six or PyMuPDF if needed. |
| K-1 form layout changes in future tax years | **Low** | IRS form layouts change infrequently. Field mapping coordinates are defined as configuration, easy to update per tax year. |

---

## 8. File Upload and Storage

**Decision**: Django FileField with custom `upload_to` function

**Rationale**:
- `upload_to=k1_upload_path` organizes files as `k1_documents/<tax_year>/<entity_id>/<filename>`
- DRF `MultiPartParser` handles file + metadata in single request via `FormData`
- PDF validation via extension check + MIME type + magic bytes (`%PDF-`) — no extra dependencies
- `DATA_UPLOAD_MAX_MEMORY_SIZE = 10 MB` in settings.py to allow 10 MB uploads (Django default is 2.5 MB)
- Docker Compose bind mount `./backend/media:/app/media` for local dev
- Production: Start with Railway Volume; migrate to `django-storages` + S3 when needed

**Serving media files**:
- Development: `django.conf.urls.static` in urls.py (DEBUG only)
- Production: Django view with `FileResponse` for streaming downloads (WhiteNoise does not serve media)
- Future: `django-storages` + S3 signed URLs when auth is added

---

## 9. Django App Architecture

**Decision**: Add K-1 models and views to existing `api` app

**Rationale**:
- Constitution constraint: Max 3 Django apps (currently 2: `api`, `plaid_integration`)
- K-1 ingestion is tightly coupled to existing Entity and Asset models already in `api`
- Parser logic isolated in a new `k1_parser.py` module — clean separation without app overhead

---

## 10. Portfolio Data Auto-Population

**Decision**: On K-1 confirmation, atomically create Distribution + DistributionAllocation + K1CapitalAccount records in a single transaction

**Rationale**:
- Constitution: Data Integrity First — use `django.db.transaction.atomic()`
- Distribution record: Created from line 19A (cash distributions). Distribution linked to asset, allocation linked to entity
- Capital account: Stored as K1CapitalAccount record with beginning/ending balances
- Duplicate detection: Check for existing K-1 with same partnership EIN + partner TIN + tax year before save
- User confirms duplicate resolution (skip/overwrite/create new) in review UI

---

## 11. New Dependencies Summary

| Package | Version | Purpose | Docker Impact |
|---------|---------|---------|---------------|
| pdfplumber | >=0.10,<1.0 | PDF text extraction | ~5 MB, pure Python |
| Pillow | >=10.0,<11.0 | Image handling for OCR fallback | ~20 MB |
| pytesseract | >=0.3.10,<1.0 | OCR wrapper | ~2 MB Python + ~50 MB Tesseract system package |

Tesseract system package requires `apt-get install tesseract-ocr` in Dockerfile.

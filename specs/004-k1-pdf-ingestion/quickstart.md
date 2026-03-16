# Quickstart: K-1 PDF Ingestion

**Feature**: 004-k1-pdf-ingestion  
**Prerequisites**: Docker Compose running (backend + frontend + db)

---

## 1. Install New Dependencies

Add to `backend/requirements.txt`:
```
pdfplumber>=0.10,<1.0
pytesseract>=0.3.10,<1.0
Pillow>=10.0,<11.0
```

Add to `backend/Dockerfile` (before `pip install`):
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*
```

Rebuild containers:
```bash
docker-compose up --build
```

---

## 2. Run Migrations

After adding the new models:
```bash
docker-compose exec backend python manage.py makemigrations api
docker-compose exec backend python manage.py migrate
```

---

## 3. Configure Media Storage

Add to `docker-compose.yml` backend service volumes:
```yaml
- ./backend/media:/app/media
```

Add to `backend/financial_accounting/settings.py`:
```python
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
```

Add to `backend/financial_accounting/urls.py` (for dev):
```python
from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

---

## 4. Test the Upload Flow

### Upload a K-1 PDF
```bash
curl -X POST http://localhost:8000/api/k1-documents/upload/ \
  -F "document=@path/to/k1.pdf"
```

Expected: 201 response with extracted fields in draft status.

### Review and Classify
```bash
curl -X PUT http://localhost:8000/api/k1-documents/1/ \
  -H "Content-Type: application/json" \
  -d '{"entity": 1, "asset": 1, "asset_type_classification": "private_equity"}'
```

### Confirm
```bash
curl -X POST http://localhost:8000/api/k1-documents/1/confirm/ \
  -H "Content-Type: application/json" \
  -d '{}'
```

Expected: 200 response with created Distribution records.

---

## 5. Frontend Navigation

After implementation, three new pages will be available:

| Route | Page | Purpose |
|-------|------|---------|
| `/k1/upload` | K1Upload | Drag-and-drop PDF upload |
| `/k1/review/:id` | K1Review | Review, classify, and confirm extracted data |
| `/k1` | K1Documents | List all ingested K-1 documents with filters |

Add navigation links to the sidebar/nav matching existing patterns (Entities, Assets, Reports, etc.).

---

## 6. Development Workflow

1. **Backend first**: Models → Migration → Parser module → Serializers → Views → URL routes
2. **Test parser**: Unit test with sample K-1 text fixtures (extract from real PDF, anonymize)
3. **API integration tests**: Upload, review, confirm flow via DRF test client
4. **Frontend**: API client → Upload page → Review page → List page → Navigation integration
5. **End-to-end**: Upload real K-1 PDF through UI, verify extraction, confirm, check portfolio reports

---

## Key Files to Create/Modify

### New Files
- `backend/api/k1_parser.py` — PDF extraction and field parsing logic
- `backend/api/validators.py` — PDF file validation (magic bytes, extension, size)
- `frontend/src/api/k1.js` — API client for K-1 endpoints
- `frontend/src/pages/K1Upload.jsx` — Upload page
- `frontend/src/pages/K1Review.jsx` — Review/classify page
- `frontend/src/pages/K1Documents.jsx` — List/detail page

### Modified Files
- `backend/api/models.py` — Add 5 new models
- `backend/api/serializers.py` — Add K-1 serializers
- `backend/api/views.py` — Add K-1 viewset and actions
- `backend/api/urls.py` — Add K-1 routes
- `backend/requirements.txt` — Add pdfplumber, pytesseract, Pillow
- `backend/Dockerfile` — Add tesseract-ocr system package
- `backend/financial_accounting/settings.py` — DATA_UPLOAD_MAX_MEMORY_SIZE
- `backend/financial_accounting/urls.py` — Media serving for DEBUG
- `docker-compose.yml` — Media volume mount
- `frontend/src/App.jsx` — Add routes for K-1 pages

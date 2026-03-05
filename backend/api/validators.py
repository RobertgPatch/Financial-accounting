"""Custom validators for the API app."""
import os
from django.core.exceptions import ValidationError


def validate_pdf_file(value):
    """Validate that an uploaded file is a valid PDF.

    Checks:
      1. File extension is .pdf
      2. File size ≤ 10 MB
      3. File starts with the PDF magic bytes (%PDF)
    """
    # Extension check
    ext = os.path.splitext(value.name)[1].lower()
    if ext != '.pdf':
        raise ValidationError('Only PDF files are allowed.')

    # Size check (10 MB limit)
    max_size = 10 * 1024 * 1024
    if value.size > max_size:
        raise ValidationError('File size exceeds the 10 MB limit.')

    # Magic bytes check
    try:
        start = value.read(5)
        value.seek(0)  # Reset file pointer
        if not start.startswith(b'%PDF'):
            raise ValidationError('File does not appear to be a valid PDF.')
    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        raise ValidationError('Could not read file to verify PDF format.')

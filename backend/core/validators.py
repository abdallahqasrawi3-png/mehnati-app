from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def validate_image_file(f):
    """Accept only real JPEG/PNG/WEBP images below the configured size."""
    max_bytes = settings.MAX_IMAGE_UPLOAD_MB * 1024 * 1024
    if f.size > max_bytes:
        raise ValidationError(f"حجم الصورة أكبر من {settings.MAX_IMAGE_UPLOAD_MB} ميغابايت.")
    name = (getattr(f, "name", "") or "").lower()
    if not any(name.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise ValidationError("نوع الملف غير مسموح. المسموح: JPG وPNG وWEBP.")
    try:
        pos = f.tell() if hasattr(f, "tell") else 0
        img = Image.open(f)
        img.verify()
        fmt = img.format
        f.seek(pos)
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise ValidationError("الملف ليس صورة صالحة.")
    if fmt not in ALLOWED_IMAGE_FORMATS:
        raise ValidationError("صيغة الصورة غير مدعومة.")

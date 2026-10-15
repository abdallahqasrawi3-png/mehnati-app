from django.conf import settings
from django.db import models


class City(models.Model):
    name = models.CharField("المدينة", max_length=80, unique=True)
    is_active = models.BooleanField("فعالة", default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "مدينة"
        verbose_name_plural = "المدن"

    def __str__(self):
        return self.name


class Area(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="areas", verbose_name="المدينة")
    name = models.CharField("المنطقة", max_length=80)

    class Meta:
        ordering = ["city__name", "name"]
        unique_together = [("city", "name")]
        verbose_name = "منطقة"
        verbose_name_plural = "المناطق"

    def __str__(self):
        return f"{self.city.name} - {self.name}"


class AuditLog(models.Model):
    """Records important administrative actions done through the API."""

    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, verbose_name="المنفذ")
    action = models.CharField("الإجراء", max_length=80)
    target_type = models.CharField("نوع الهدف", max_length=40, blank=True)
    target_id = models.CharField("معرف الهدف", max_length=40, blank=True)
    details = models.JSONField("تفاصيل", default=dict, blank=True)
    created_at = models.DateTimeField("الوقت", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "سجل إداري"
        verbose_name_plural = "سجل العمليات الإدارية"

    def __str__(self):
        return f"{self.action} {self.target_type}#{self.target_id}"


class AbuseReport(models.Model):
    class Target(models.TextChoices):
        REVIEW = "review", "تقييم"
        OFFER = "offer", "عرض"
        BUSINESS = "business", "مشروع منزلي"
        MATERIAL = "material", "مادة خام"
        SUPPLIER = "supplier", "مورد"

    class Status(models.TextChoices):
        OPEN = "open", "مفتوح"
        RESOLVED = "resolved", "تمت المعالجة"
        DISMISSED = "dismissed", "مرفوض"

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="abuse_reports", verbose_name="المُبلِّغ"
    )
    target_type = models.CharField("نوع المحتوى", max_length=20, choices=Target.choices)
    target_id = models.PositiveIntegerField("معرف المحتوى")
    reason = models.TextField("السبب", max_length=1000)
    status = models.CharField("الحالة", max_length=20, choices=Status.choices, default=Status.OPEN)
    admin_note = models.TextField("ملاحظة الإدارة", blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "بلاغ"
        verbose_name_plural = "البلاغات"

    def __str__(self):
        return f"{self.get_target_type_display()} #{self.target_id}"


class ContactMessage(models.Model):
    """A report or question sent to the platform administrator from the app's contact form.
    Saved here (admin dashboard) and also handed to the admin's WhatsApp by the sender."""

    class Kind(models.TextChoices):
        PROBLEM = "problem", "مشكلة في التطبيق"
        ABUSE = "abuse", "بلاغ عن محتوى أو مستخدم"
        ORDER = "order", "شكوى على طلب"
        SUGGESTION = "suggestion", "اقتراح"
        OTHER = "other", "أخرى"

    class Status(models.TextChoices):
        OPEN = "open", "جديد"
        RESOLVED = "resolved", "تمت المعالجة"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="contact_messages", verbose_name="المستخدم",
    )
    name = models.CharField("الاسم", max_length=120)
    phone = models.CharField("الهاتف", max_length=30, blank=True)
    kind = models.CharField("نوع البلاغ", max_length=20, choices=Kind.choices, default=Kind.PROBLEM)
    order_ref = models.CharField("رقم الطلب", max_length=30, blank=True)
    message = models.TextField("الرسالة", max_length=2000)
    status = models.CharField("الحالة", max_length=20, choices=Status.choices, default=Status.OPEN)
    admin_note = models.TextField("ملاحظة الإدارة", blank=True)
    created_at = models.DateTimeField("وقت الإرسال", auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "رسالة إلى الإدارة"
        verbose_name_plural = "رسائل التواصل مع الإدارة"

    def __str__(self):
        return f"#{self.pk} {self.get_kind_display()} - {self.name}"

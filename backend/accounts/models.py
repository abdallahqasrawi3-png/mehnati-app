from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


class MehnatyUserManager(UserManager):
    def create_user(self, email=None, password=None, **extra):
        email = self.normalize_email(email).lower()
        extra.setdefault("username", email)
        username = extra.pop("username")
        return super().create_user(username, email, password, **extra)

    def create_superuser(self, email=None, password=None, **extra):
        email = self.normalize_email(email).lower()
        extra.setdefault("username", email)
        username = extra.pop("username")
        return super().create_superuser(username, email, password, **extra)


class User(AbstractUser):
    """One account may be a customer, a home-business owner and a supplier at once.

    Every account can act as a customer. Business/supplier roles exist when the
    related profile (catalog.BusinessProfile / suppliers.SupplierProfile) exists.
    Suspension = is_active False (set by administrators).
    """

    email = models.EmailField("البريد الإلكتروني", unique=True)
    full_name = models.CharField("الاسم الكامل", max_length=120)
    phone = models.CharField("رقم الهاتف (خاص)", max_length=30, blank=True)
    city = models.ForeignKey("core.City", null=True, blank=True, on_delete=models.SET_NULL, verbose_name="المدينة")

    objects = MehnatyUserManager()

    # Sign in with email; username is filled automatically with the email.
    EMAIL_FIELD = "email"
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    def save(self, *args, **kwargs):
        self.email = (self.email or "").strip().lower()
        if not self.username:
            self.username = self.email
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "مستخدم"
        verbose_name_plural = "المستخدمون"

    def __str__(self):
        return self.full_name or self.email

    @property
    def roles(self):
        r = ["customer"]
        if hasattr(self, "business_profile"):
            r.append("business")
        if hasattr(self, "supplier_profile"):
            r.append("supplier")
        if self.is_staff:
            r.append("admin")
        return r


class Address(models.Model):
    """Private delivery address. Visible only to its owner and, as an order
    snapshot, to the counterparty fulfilling that order.

    Besides city/area it can hold street-level parts and an optional exact map
    pin (latitude/longitude), e.g. a workshop entrance or a storage room door."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    label = models.CharField("الاسم", max_length=50, default="المنزل")
    recipient_name = models.CharField("اسم المستلم", max_length=120)
    phone = models.CharField("الهاتف", max_length=30)
    city = models.ForeignKey("core.City", on_delete=models.PROTECT, verbose_name="المدينة")
    area = models.ForeignKey("core.Area", null=True, blank=True, on_delete=models.SET_NULL, verbose_name="المنطقة")
    street = models.CharField("الشارع", max_length=120, blank=True)
    building = models.CharField("البناية / رقم المبنى", max_length=60, blank=True)
    floor = models.CharField("الطابق", max_length=20, blank=True)
    apartment = models.CharField("الشقة / المحل", max_length=30, blank=True)
    landmark = models.CharField("أقرب معلم", max_length=120, blank=True)
    details = models.CharField("تفاصيل إضافية", max_length=255, blank=True)
    latitude = models.DecimalField("خط العرض", max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField("خط الطول", max_digits=9, decimal_places=6, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "عنوان"
        verbose_name_plural = "العناوين"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(latitude__isnull=True, longitude__isnull=True)
                    | models.Q(latitude__gte=-90, latitude__lte=90, longitude__gte=-180, longitude__lte=180)
                ),
                name="address_valid_coordinates",
            ),
        ]

    def __str__(self):
        return f"{self.label} - {self.city}"

    @property
    def has_pin(self):
        return self.latitude is not None and self.longitude is not None

    @property
    def full_text(self):
        """Street-level description in one line, e.g.
        «شارع فيصل، بناية 12، الطابق 3، شقة/محل 5 · أقرب معلم: مقابل المسجد».
        Numbers get a prefix; free text («عمارة النور»، «مشغل 2») is shown as typed."""

        def labelled(prefix, value):
            value = (value or "").strip()
            if not value:
                return ""
            return f"{prefix} {value}" if value.isdigit() else value

        parts = [
            self.street,
            labelled("بناية", self.building),
            f"الطابق {self.floor.strip()}" if self.floor.strip() else "",
            labelled("شقة/محل", self.apartment),
            self.details,
        ]
        text = "، ".join(p.strip() for p in parts if p and p.strip())
        landmark = self.landmark.strip()
        if landmark:
            text = f"{text} · أقرب معلم: {landmark}" if text else f"أقرب معلم: {landmark}"
        return text

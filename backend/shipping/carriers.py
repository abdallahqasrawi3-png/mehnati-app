"""Carrier integration layer.

Each adapter declares the capabilities it really supports. No real carrier API
is configured yet (no company/credentials were supplied), so only:
  * ManualAdapter  - data entered by the sender, no external calls.
  * SimulatorAdapter - for automated tests/demo ONLY; it is not a real carrier
    and is available only when SHIPPING_SIMULATOR_ENABLED=true.
To add a real carrier: subclass CarrierAdapter, implement the documented calls,
register it in ADAPTERS, and set Carrier.integration to its key.
"""
import uuid

from django.conf import settings


class CarrierError(Exception):
    """The carrier could not be reached or refused the request."""


class CreateResult:
    def __init__(self, confirmed, external_reference="", tracking_number="", cost=None, estimated_arrival=None):
        self.confirmed = confirmed
        self.external_reference = external_reference
        self.tracking_number = tracking_number
        self.cost = cost
        self.estimated_arrival = estimated_arrival


class CarrierAdapter:
    key = ""
    capabilities = frozenset()  # subset of {"create", "quote", "track"}

    def supports(self, capability):
        return capability in self.capabilities

    def create_shipment(self, shipment, idempotency_key):
        raise NotImplementedError

    def track(self, shipment):
        raise NotImplementedError


class ManualAdapter(CarrierAdapter):
    key = "manual"
    capabilities = frozenset()


class SimulatorAdapter(CarrierAdapter):
    """Fake carrier used in tests. Never presented as a real connection."""

    key = "simulator"
    capabilities = frozenset({"create", "track"})
    fail_next = False  # tests can flip this to simulate an outage
    _created = {}

    def create_shipment(self, shipment, idempotency_key):
        if not settings.SHIPPING_SIMULATOR_ENABLED:
            raise CarrierError("محاكي التوصيل غير مفعّل.")
        if SimulatorAdapter.fail_next:
            raise CarrierError("تعذر الاتصال بشركة التوصيل (محاكاة).")
        # Same idempotency key => same remote shipment (no duplicates)
        if idempotency_key not in SimulatorAdapter._created:
            SimulatorAdapter._created[idempotency_key] = "SIM-" + uuid.uuid4().hex[:10].upper()
        ref = SimulatorAdapter._created[idempotency_key]
        return CreateResult(confirmed=True, external_reference=ref, tracking_number=ref)


ADAPTERS = {a.key: a for a in (ManualAdapter(), SimulatorAdapter())}


def get_adapter(carrier):
    if carrier is None:
        return ADAPTERS["manual"]
    adapter = ADAPTERS.get(carrier.integration)
    if adapter is None:
        raise CarrierError("لا يوجد مكوّن تكامل مُعدّ لهذه الشركة؛ استخدم الإدخال اليدوي.")
    return adapter

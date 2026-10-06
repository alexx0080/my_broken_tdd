"""Order checkout.

The rules live in `src/shop/specs/checkout.md` - read it first.
Both functions below are stubs: their signature is final, the bodies are yours.
Do not change the constants: the tests rely on them.
"""

from shop.money import percent_of

PROMO_CODES = {"WELCOME10": 10, "SUMMER15": 15, "VIP35": 35}
SUPPORTED_CITIES = ("msk", "spb")
MAX_DISCOUNT_PERCENT = 30
VAT_PERCENT = 20
SHIPPING_KOPEKS = 49_000
FREE_DELIVERY_FROM_KOPEKS = 500_000
TIER_DISCOUNTS = ((10, 5), (25, 10), (50, 15))
REQUIRED_LINE_KEYS = ("sku", "qty", "unit_price_kopecks")


def _validate_qty(raw_qty: str) -> str | None:
    """Валидация количества одной строки заказа (выделена ради сложности C901)."""
    try:
        qty = int(raw_qty)
    except ValueError:
        return "Quantity must be an integer"
    if qty <= 0:
        return "Quantity must be greater than zero"
    if qty > 1_000_000:
        return "Quantity is too large"
    return None


def _validate_price(raw_price: str) -> str | None:
    """Валидация цены одной строки заказа (выделена ради сложности C901)."""
    try:
        price = int(raw_price)
    except ValueError:
        return "Price must be an integer"
    if price < 0:
        return "Price cannot be negative"
    return None


def _validate_line(line: dict[str, str], seen_skus: set[str]) -> str | None:
    """Вспомогательная функция для проверки одной строки заказа (снижает сложность C901)."""
    # Проверка обязательных ключей
    for key in REQUIRED_LINE_KEYS:
        if key not in line:
            return f"Missing required key: {key}"

    # Валидация SKU
    sku = line["sku"]
    if not sku:
        return "SKU cannot be empty"
    if sku in seen_skus:
        return f"Duplicate SKU found: {sku}"
    seen_skus.add(sku)

    qty_error = _validate_qty(line["qty"])
    if qty_error is not None:
        return qty_error

    price_error = _validate_price(line["unit_price_kopecks"])
    if price_error is not None:
        return price_error

    return None


def validate_order(
    lines: list[dict[str, str]],
    promo_code: str = "",
    shipping_city: str = "",
) -> str | None:
    """Return a human readable reason why the order is invalid, or None if it is fine."""
    if not lines:
        return "Order cannot be empty"

    seen_skus: set[str] = set()

    for line in lines:
        error = _validate_line(line, seen_skus)
        if error is not None:
            return error

    # Валидация промокода
    if promo_code and promo_code not in PROMO_CODES:
        return "Unknown promo code"

    # Валидация города доставки
    if shipping_city and shipping_city not in SUPPORTED_CITIES:
        return "Unsupported shipping city"

    return None


def calculate_order_total(
    lines: list[dict[str, str]],
    promo_code: str = "",
    shipping_city: str = "",
) -> int | None:
    """Return the order total in kopecks, or None if the order is invalid."""
    if validate_order(lines, promo_code, shipping_city) is not None:
        return None

    subtotal = 0
    total_qty = 0

    for line in lines:
        qty = int(line["qty"])
        price = int(line["unit_price_kopecks"])
        subtotal += qty * price
        total_qty += qty

    # Определение ярусной скидки
    tier_discount_percent = 0
    for threshold, percent in sorted(TIER_DISCOUNTS, key=lambda x: x):
        if total_qty >= threshold:
            tier_discount_percent = percent

    # Определение скидки по промокоду
    promo_discount_percent = PROMO_CODES.get(promo_code, 0) if promo_code else 0

    # Выбор максимального процента и ограничение лимитом
    discount_percent = max(tier_discount_percent, promo_discount_percent)
    if discount_percent > MAX_DISCOUNT_PERCENT:
        discount_percent = MAX_DISCOUNT_PERCENT

    # Расчёт стоимости с учётом скидки
    discount = percent_of(subtotal, discount_percent)
    discounted_subtotal = subtotal - discount

    # Начисление стоимости доставки
    shipping = 0
    if shipping_city and discounted_subtotal < FREE_DELIVERY_FROM_KOPEKS:
        shipping = SHIPPING_KOPEKS

    base = discounted_subtotal + shipping
    vat = percent_of(base, VAT_PERCENT)

    return base + vat

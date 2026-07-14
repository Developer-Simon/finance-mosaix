from __future__ import annotations


def _to_float(value, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except Exception:
        return default


def calculate_goods_current_value(
    purchase_value,
    depreciation_input,
    previous_value,
    months_diff: int,
) -> float:
    purchase_value = _to_float(purchase_value)
    depreciation_input = _to_float(depreciation_input)

    if previous_value is None or previous_value == "":
        previous_value = purchase_value
    previous_value = _to_float(previous_value, purchase_value)

    if depreciation_input == 0:
        return round(purchase_value, 2)

    monthly_change = purchase_value / (depreciation_input * 12)
    if purchase_value > 0:
        return round(max(previous_value - (monthly_change * months_diff), 0.0), 2)
    return round(min(previous_value - (monthly_change * months_diff), 0.0), 2)

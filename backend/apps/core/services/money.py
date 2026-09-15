"""amount_in_words(Decimal) — the Indian numbering system (crore, lakh,
thousand), for the direct-admission receipt and the printed form. Rendered
only, never stored and never accepted as API input — see
Admission.fee_total_in_words.
"""

from decimal import Decimal

_ONES = [
    "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
    "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen",
    "Eighteen", "Nineteen",
]
_TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _two_digit_words(n: int) -> str:
    if n == 0:
        return ""
    if n < 20:
        return _ONES[n]
    tens, ones = divmod(n, 10)
    return _TENS[tens] + (f" {_ONES[ones]}" if ones else "")


def _hundred_group_words(n: int) -> str:
    """0-999 — the rightmost group in the Indian system; every group above
    it (thousand, lakh, crore) is two digits, handled by _two_digit_words.
    """
    hundred, rest = divmod(n, 100)
    parts = []
    if hundred:
        parts.append(f"{_ONES[hundred]} Hundred")
    if rest:
        parts.append(_two_digit_words(rest))
    return " ".join(parts)


def amount_in_words(amount: Decimal) -> str:
    """Whole rupees only — a fee amount with paise still renders the
    rupee part; nothing in this feature collects paise-precision fees.
    """
    n = int(amount)
    if n == 0:
        return "Rupees Zero only"

    crore, n = divmod(n, 10_000_000)
    lakh, n = divmod(n, 100_000)
    thousand, n = divmod(n, 1_000)
    hundred_group = n

    parts = []
    if crore:
        parts.append(f"{_two_digit_words(crore)} Crore")
    if lakh:
        parts.append(f"{_two_digit_words(lakh)} Lakh")
    if thousand:
        parts.append(f"{_two_digit_words(thousand)} Thousand")
    if hundred_group:
        parts.append(_hundred_group_words(hundred_group))

    return f"Rupees {' '.join(parts)} only"

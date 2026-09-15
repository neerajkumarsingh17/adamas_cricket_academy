from decimal import Decimal

import pytest

from apps.core.services.money import amount_in_words


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (Decimal("25500"), "Rupees Twenty Five Thousand Five Hundred only"),
        (Decimal("100000"), "Rupees One Lakh only"),
        (Decimal("0"), "Rupees Zero only"),
        (Decimal("1"), "Rupees One only"),
        (Decimal("100"), "Rupees One Hundred only"),
        (Decimal("1000"), "Rupees One Thousand only"),
        (Decimal("10000000"), "Rupees One Crore only"),
        (
            Decimal("12345678"),
            "Rupees One Crore Twenty Three Lakh Forty Five Thousand Six Hundred "
            "Seventy Eight only",
        ),
    ],
)
def test_amount_in_words(amount, expected):
    assert amount_in_words(amount) == expected

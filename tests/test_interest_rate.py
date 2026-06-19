from models.interest_rate import InterestRate


def test_interest_rate_has_all_fields():
    record = InterestRate(
        date="2026-06-19",
        bank="Techcombank",
        channel="counter",
        rate_1m=3.5,
        rate_3m=4.0,
        rate_6m=5.0,
        rate_12m=5.5,
        rate_18m=None,
        rate_24m=5.8,
        rate_36m=6.0,
    )
    assert record.date == "2026-06-19"
    assert record.bank == "Techcombank"
    assert record.channel == "counter"
    assert record.rate_1m == 3.5
    assert record.rate_18m is None


def test_interest_rate_fields_are_typed_correctly():
    record = InterestRate(
        date="2026-06-19",
        bank="VCB",
        channel="online",
        rate_1m=3.2,
        rate_3m=None,
        rate_6m=4.5,
        rate_12m=5.0,
        rate_18m=None,
        rate_24m=5.5,
        rate_36m=5.8,
    )
    assert isinstance(record.rate_1m, float)
    assert record.rate_3m is None

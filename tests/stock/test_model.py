from stock.model import StockPrice


def test_stock_price_fields():
    sp = StockPrice(
        date="2026-06-18",
        symbol="HPG",
        open=24050,
        high=24150,
        low=23650,
        close=23650,
        volume=18040500,
    )
    assert sp.date == "2026-06-18"
    assert sp.symbol == "HPG"
    assert sp.open == 24050
    assert sp.high == 24150
    assert sp.low == 23650
    assert sp.close == 23650
    assert sp.volume == 18040500


def test_stock_price_optional_fields_can_be_none():
    sp = StockPrice(
        date="2026-06-18",
        symbol="TST",
        open=None,
        high=None,
        low=None,
        close=None,
        volume=None,
    )
    assert sp.open is None
    assert sp.high is None
    assert sp.low is None
    assert sp.close is None
    assert sp.volume is None

_OHLC_URL = "https://services.entrade.com.vn/chart-api/v2/ohlcs/stock"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def _to_vnd(raw: float) -> int:
    return int(round(raw * 1000))

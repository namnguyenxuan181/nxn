import sys
from unittest.mock import MagicMock


def _cache_data(func=None, **kwargs):
    if func is not None:
        return func
    return lambda f: f


mock_st = MagicMock()
mock_st.cache_data = _cache_data
sys.modules["streamlit"] = mock_st

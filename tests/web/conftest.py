import sys
from unittest.mock import MagicMock

mock_st = MagicMock()
mock_st.cache_data = lambda f: f
sys.modules["streamlit"] = mock_st

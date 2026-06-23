from unittest.mock import patch, MagicMock
from alerts.notifier import notify


def test_notify_calls_osascript_on_darwin():
    with patch("alerts.notifier.sys") as mock_sys, \
         patch("alerts.notifier.subprocess.run") as mock_run:
        mock_sys.platform = "darwin"
        notify("Test Title", "Test Body")
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert args[0] == "osascript"
    assert "Test Title" in args[2]
    assert "Test Body" in args[2]


def test_notify_noop_on_non_darwin():
    with patch("alerts.notifier.sys") as mock_sys, \
         patch("alerts.notifier.subprocess.run") as mock_run:
        mock_sys.platform = "linux"
        notify("Title", "Body")
    mock_run.assert_not_called()


def test_notify_silently_ignores_exception():
    with patch("alerts.notifier.sys") as mock_sys, \
         patch("alerts.notifier.subprocess.run", side_effect=Exception("fail")):
        mock_sys.platform = "darwin"
        notify("Title", "Body")  # must not raise

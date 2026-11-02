from streamlit.testing.v1 import AppTest


def test_dashboard_renders_without_errors():
    at = AppTest.from_file("../app.py", default_timeout=60).run()
    assert not at.exception
    assert "decarbonising" in at.title[0].value
    assert len(at.metric) == 3


def test_dashboard_handles_empty_selection():
    at = AppTest.from_file("../app.py", default_timeout=60).run()
    at.sidebar.multiselect[0].set_value([]).run()
    assert not at.exception
    assert any("Pick at least one country" in i.value for i in at.info)

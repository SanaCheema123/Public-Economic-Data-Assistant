from app.services.connectors.http_connectors import _html_text_lines


def test_html_text_lines_uses_stdlib_and_ignores_scripts():
    html = """<html><body><div>1.8%</div><h3>Inflation, July 2026</h3><script>hidden text</script></body></html>"""
    lines = _html_text_lines(html)
    assert "1.8%" in lines
    assert "Inflation, July 2026" in lines
    assert "hidden text" not in lines

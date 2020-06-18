from universum.lib.utils import read_multiline_option


def test_success_multiline_variable(tmp_path, monkeypatch):
    text = "This is text\nwith some line breaks\n"

    # Direct input
    assert read_multiline_option(text) == text

    # File
    var_path = tmp_path / "variable.txt"
    var_path.write_text(text)
    assert read_multiline_option(f"@{str(var_path)}") == text

    # Stdin
    monkeypatch.setattr('sys.stdin.read', lambda: text)
    assert read_multiline_option('-') == text

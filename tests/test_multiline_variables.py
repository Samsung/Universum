from universum.lib.module_arguments import ModuleArgumentParser, multiline_argument


def test_multiline_vars(tmp_path, monkeypatch):
    text = "This is text\nwith some line breaks\n"
    parser = ModuleArgumentParser()
    parser.add_argument("--argument", type=multiline_argument)

    # Usual value
    namespace = parser.parse_args(["--argument", text])
    assert namespace.argument == text

    # File
    tmp_file = tmp_path / "myfile.txt"
    tmp_file.write_text(text)
    namespace = parser.parse_args(["--argument", '@' + str(tmp_file)])
    assert namespace.argument == text

    # Stdin
    monkeypatch.setattr('sys.stdin.read', lambda: text)
    namespace = parser.parse_args(["--argument", '-'])
    assert namespace.argument == text

from pathlib import Path

from codex_buddy import shell_integration


def test_install_zprofile_block_creates_managed_block(tmp_path):
    zprofile = tmp_path / ".zprofile"

    shell_integration.install_path_block(zprofile, Path("/Users/tester/.code-buddy/bin"))

    text = zprofile.read_text(encoding="utf-8")
    assert shell_integration.BLOCK_START in text
    assert 'export PATH="$HOME/.code-buddy/bin:$PATH"' in text
    assert shell_integration.BLOCK_END in text


def test_install_zprofile_block_is_idempotent(tmp_path):
    zprofile = tmp_path / ".zprofile"

    shell_integration.install_path_block(zprofile, Path("/Users/tester/.code-buddy/bin"))
    shell_integration.install_path_block(zprofile, Path("/Users/tester/.code-buddy/bin"))

    text = zprofile.read_text(encoding="utf-8")
    assert text.count(shell_integration.BLOCK_START) == 1
    assert text.count(shell_integration.BLOCK_END) == 1


def test_remove_zprofile_block_preserves_surrounding_content(tmp_path):
    zprofile = tmp_path / ".zprofile"
    zprofile.write_text("export FOO=1\n", encoding="utf-8")
    shell_integration.install_path_block(zprofile, Path("/Users/tester/.code-buddy/bin"))

    shell_integration.remove_path_block(zprofile)

    assert zprofile.read_text(encoding="utf-8") == "export FOO=1\n"

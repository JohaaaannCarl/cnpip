"""测试包管理器下载源的覆盖检测与诊断输出。"""

from types import SimpleNamespace

import cnpip.cnpip as cnpip
import cnpip.integrations as integrations


def _clear_source_environment(monkeypatch):
    for names in cnpip.SOURCE_ENV_VARS.values():
        for name in names:
            monkeypatch.delenv(name, raising=False)


def test_pip_environment_index_wins_over_config_output(monkeypatch):
    output = "\n".join(
        (
            ":env:.index-url='https://env.example/simple'",
            "install.index-url='https://install.example/simple'",
            "global.index-url='https://config.example/simple'",
        )
    )
    monkeypatch.setattr(
        cnpip.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=output, stderr=""),
    )

    index_url, _trusted_host = cnpip.get_pip_config()

    assert index_url == "https://env.example/simple"


def test_pip_pypi_url_alias_wins_over_config_output(monkeypatch):
    output = "\n".join(
        (
            ":env:.pypi-url='https://alias.example/simple'",
            "global.index-url='https://config.example/simple'",
        )
    )
    monkeypatch.setattr(
        cnpip.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=output, stderr=""),
    )

    index_url, _trusted_host = cnpip.get_pip_config()

    assert index_url == "https://alias.example/simple"


def test_pip_install_section_wins_over_global_config(monkeypatch):
    output = "\n".join(
        (
            "install.index-url='https://install.example/simple'",
            "global.index-url='https://config.example/simple'",
        )
    )
    monkeypatch.setattr(
        cnpip.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=output, stderr=""),
    )

    index_url, _trusted_host = cnpip.get_pip_config()

    assert index_url == "https://install.example/simple"


def test_source_environment_ignores_false_boolean_override(monkeypatch):
    _clear_source_environment(monkeypatch)
    monkeypatch.setenv("PIP_NO_INDEX", "false")
    monkeypatch.setenv("PIP_INDEX_URL", "https://env.example/simple")

    assert cnpip.get_source_environment("pip") == [
        ("PIP_INDEX_URL", "https://env.example/simple")
    ]


def test_uv_project_config_is_reported_from_current_directory(tmp_path, monkeypatch):
    _clear_source_environment(monkeypatch)
    project = tmp_path / "project"
    child = project / "src"
    child.mkdir(parents=True)
    config = project / "pyproject.toml"
    config.write_text("[tool.uv]\nno-cache = true\n", encoding="utf-8")
    monkeypatch.chdir(child)
    monkeypatch.setattr(cnpip, "get_uv_config_path", lambda: tmp_path / "user.toml")

    assert cnpip.get_uv_project_config_path() == config
    assert cnpip.get_source_context_overrides("uv") == [("项目配置", str(config))]


def test_uv_config_file_is_not_reported_twice(tmp_path, monkeypatch):
    _clear_source_environment(monkeypatch)
    config = tmp_path / "selected.toml"
    monkeypatch.setenv("UV_CONFIG_FILE", str(config))

    overrides = cnpip.get_source_overrides("uv")

    assert overrides == [("UV_CONFIG_FILE", str(config))]


def test_uv_isolated_does_not_hide_project_config(tmp_path, monkeypatch):
    _clear_source_environment(monkeypatch)
    config = tmp_path / "pyproject.toml"
    config.write_text("[tool.uv]\nno-cache = true\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("UV_ISOLATED", "1")
    monkeypatch.setattr(cnpip, "get_uv_config_path", lambda: tmp_path / "user.toml")

    assert cnpip.get_source_context_overrides("uv") == [("项目配置", str(config))]


def test_pdm_pyproject_source_is_reported(tmp_path, monkeypatch):
    _clear_source_environment(monkeypatch)
    config = tmp_path / "pyproject.toml"
    config.write_text(
        '[[tool.pdm.source]]\nname = "mirror"\nurl = "https://mirror.example/simple"\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    assert cnpip.get_source_context_overrides("pdm") == [("PDM 项目源", str(config))]


def test_pdm_toml_source_is_reported(tmp_path, monkeypatch):
    _clear_source_environment(monkeypatch)
    config = tmp_path / "pdm.toml"
    config.write_text(
        '[[source]]\nname = "mirror"\nurl = "https://mirror.example/simple"\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    assert cnpip.get_source_context_overrides("pdm") == [("PDM 项目源", str(config))]


def test_override_output_redacts_url_credentials(monkeypatch, capsys):
    _clear_source_environment(monkeypatch)
    monkeypatch.setenv("PIP_INDEX_URL", "https://alice:secret@example.com/simple")

    assert cnpip.print_source_overrides("pip")
    output = capsys.readouterr().out

    assert "alice" not in output
    assert "secret" not in output
    assert "example.com" in output


def test_set_warning_names_active_override(monkeypatch, capsys):
    _clear_source_environment(monkeypatch)
    monkeypatch.setenv("PDM_PYPI_URL", "https://env.example/simple")

    cnpip.print_set_override_warning("pdm")

    output = capsys.readouterr().out
    assert "配置已写入" in output
    assert "PDM_PYPI_URL" in output


def test_pdm_persistent_read_ignores_environment_override(monkeypatch):
    monkeypatch.setenv("PDM_PYPI_URL", "https://env.example/simple")
    monkeypatch.setattr(integrations.shutil, "which", lambda name: "/usr/bin/pdm")

    def fake_run(command, **kwargs):
        assert command == ["/usr/bin/pdm", "config", "pypi.url"]
        assert "PDM_PYPI_URL" not in kwargs["env"]
        return SimpleNamespace(
            returncode=0, stdout="https://config.example/simple\n", stderr=""
        )

    monkeypatch.setattr(integrations.subprocess, "run", fake_run)

    assert integrations.get_pdm_configured_mirror() == "https://config.example/simple"


def test_conda_effective_config_uses_native_json(monkeypatch):
    monkeypatch.setattr(integrations.shutil, "which", lambda name: "/usr/bin/conda")
    monkeypatch.setattr(
        integrations,
        "_run",
        lambda command: SimpleNamespace(
            returncode=0,
            stdout=(
                '{"channels": ["defaults"], '
                '"default_channels": ["https://mirror.example/pkgs/main"]}'
            ),
        ),
    )

    result = integrations.get_conda_effective_config()

    assert result["channels"] == ["defaults"]
    assert result["default_channels"] == ["https://mirror.example/pkgs/main"]

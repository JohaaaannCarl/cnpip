# cnpip

[中文](./README.md) · [PyPI](https://pypi.org/project/cnpip/) · [Issues](https://github.com/caoergou/cnpip/issues)

![PyPI](https://img.shields.io/pypi/v/cnpip)
![Python](https://img.shields.io/pypi/pyversions/cnpip)
![Tests](https://github.com/caoergou/cnpip/actions/workflows/test.yml/badge.svg)
![Quality](https://github.com/caoergou/cnpip/actions/workflows/quality.yml/badge.svg)
![License](https://img.shields.io/github/license/caoergou/cnpip)

**Configure Python package indexes for faster, more reliable dependency installs from China.** `cnpip` probes available mirrors and applies your selection to `pip`, `uv`, `PDM`, `Poetry`, or `Conda`. Use it for local development, Docker builds, and CI jobs that install public Python dependencies.

When the upstream package index is slow or unreliable, an available mirror can shorten the dependency-install phase. `cnpip` finds a mirror, probes it, writes configuration, and restores it when needed.

> cnpip only manages mirror configuration. It is not a proxy, download cache, or private package registry. It measures index response time; build time also depends on the environment, mirror health, dependency size, and cache hits.

## Start in 30 seconds

```bash
python -m pip install cnpip
cnpip
```

In an interactive terminal, `cnpip` detects package managers, selects `pip` by default, then chooses the available PyPI mirror with the lowest response time. When you have a fixed mirror, name its alias explicitly:

```bash
cnpip set tuna --user --yes     # Set TUNA for pip without prompts
cnpip set tuna --uv             # Configure uv only
cnpip set tuna --pdm            # Configure PDM only
cnpip set tuna --poetry         # Configure the current Poetry project
cnpip set --conda --yes         # Probe and configure a Conda-specific mirror
```

Or run it without installing it permanently:

```bash
uvx cnpip
```

Under `uvx`, cnpip targets the user-level `uv.toml`, not the short-lived tool environment.

## For agents and CI

In automation, name a mirror alias, specify a scope, and pass `--yes`. The command will not prompt and its result is more repeatable. Do not probe for a different mirror on every build.

```yaml
# GitHub Actions: configure pip before installing project dependencies
- name: Configure Python package index
  run: |
    python -m pip install --disable-pip-version-check cnpip
    cnpip set tuna --user --yes

- name: Install dependencies
  run: python -m pip install -r requirements.txt
```

Use cnpip as follows:

- Self-hosted CI in China: bake cnpip into the base image or install it from an approved internal source.
- GitHub-hosted CI: compare dependency-install time once; keep the step only when it helps.

### Dockerfile

Copy the dependency manifest before application source so Docker can reuse the dependency layer when source files change.

- This example requires BuildKit.
- Container builds normally run as root, so it uses `--global`.

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install cnpip \
    && cnpip set tuna --global --yes \
    && python -m pip install -r requirements.txt \
    && python -m pip uninstall -y cnpip

COPY . .
```

cnpip writes the package index; the BuildKit cache reuses downloaded content. Do not apply this example unchanged to images with private-index credentials, internal proxy configuration, or an existing package-cache policy.

### For AI agents

| Condition | Recommendation |
| --- | --- |
| Installing public PyPI or Conda dependencies and the runner is slow or unreliable to upstream | Run `cnpip set <built-in-mirror-alias> --user --yes`, then install dependencies |
| The team already has a trusted mirror policy | Name an alias from cnpip's mirror catalog explicitly; do not rely on dynamic probing |
| Using a private registry, proxy, credentials, or an internal cache | Do not replace the existing policy with cnpip without confirming that it is preserved |
| A lock file contains direct package URLs, or the job uses `uv sync --frozen` | Inspect the lock file first; persistent index configuration cannot rewrite already pinned URLs |

Use `cnpip info` before running cnpip to check the environment, configuration target, and recognizable source overrides:

```bash
cnpip info
cnpip set tuna --user --yes
cnpip info
```

## Supported package managers

| Tool | What cnpip changes | Configuration target |
| --- | --- | --- |
| `pip` | PyPI `index-url`, at user, system, or virtual-environment scope | Determined by `pip config` and the active environment |
| `uv` | Adds or restores an index named `cnpip` | User-level `uv.toml` |
| `PDM` | Sets or restores `pypi.url` | PDM user configuration |
| `Poetry` | Adds or removes a source named `cnpip` | The current project's `pyproject.toml` |
| `Conda` | Configures or restores `default_channels`, conda-forge, and pytorch community channels | `CONDARC`, normally `~/.condarc` |

Conda has its own mirror catalog; do not use a PyPI mirror for Conda.

## Common commands

| Goal | Command |
| --- | --- |
| List PyPI mirrors and current response times | `cnpip list` |
| Probe and configure automatically | `cnpip` or `cnpip set` |
| Set a known PyPI mirror | `cnpip set tuna --user --yes` |
| Configure one tool only | `cnpip set tuna --uv`, `--pdm`, `--poetry`, or `--conda` |
| See the environment, config files, and recognizable overrides | `cnpip info` |
| Restore configuration managed by cnpip | `cnpip unset`, with tool or scope flags as needed |
| Refresh the mirror manifest | `cnpip sync` |

In a terminal, `cnpip set` without a tool or scope flag prompts for a tool. Scripts, CI, explicit tool flags, and `--yes` do not prompt.

## Speed, reliability, and safety

- PyPI probes `simple/pip/` three times; Conda probes `pkgs/main/noarch/repodata.json`. A mirror needs two successful requests, then cnpip uses the median response time.
- Probing measures index response, not guaranteed wheel or large-file download speed. Benchmark real dependencies for build-speed claims.
- `unset` restores only unchanged configuration that cnpip owns. It refuses to overwrite later changes.
- pip and uv file changes use atomic replacement. PDM, Poetry, and Conda use their own CLIs. Failed batch changes attempt to restore earlier operations.
- HTTPS mirrors never get pip's `trusted-host` option, preserving TLS verification.

## Configuration overrides

Environment variables, project configuration, dependency files, and command-line flags can override cnpip. `cnpip info` shows recognizable overrides in the current environment.

| Tool | Common overrides to check |
| --- | --- |
| `pip` | `PIP_INDEX_URL`, `PIP_EXTRA_INDEX_URL`, `PIP_CONFIG_FILE`, requirements files, command-line flags |
| `uv` | Project `uv.toml` or `pyproject.toml`, `UV_INDEX`, `UV_DEFAULT_INDEX`, `UV_CONFIG_FILE`, command-line flags |
| `PDM` | Project sources and `PDM_PYPI_URL` |
| `Poetry` | Project source priority and dependency source constraints |
| `Conda` | Layered condarc files, `CONDA_CHANNELS`, `-c` / `--override-channels` |

Extra indexes are not always fallbacks. Assess dependency-confusion risk before adding multiple pip indexes. Run `cnpip info` before and after use, and state the intended source policy in CI.

## Mirrors

| Name | Alias | PyPI URL |
| --- | --- | --- |
| Tsinghua University TUNA | `tuna` | https://pypi.tuna.tsinghua.edu.cn/simple |
| University of Science and Technology of China | `ustc` | https://pypi.mirrors.ustc.edu.cn/simple |
| Aliyun | `aliyun` | https://mirrors.aliyun.com/pypi/simple |
| Tencent | `tencent` | https://mirrors.cloud.tencent.com/pypi/simple |
| Huawei | `huawei` | https://repo.huaweicloud.com/repository/pypi/simple |
| Westlake University | `westlake` | https://mirrors.westlake.edu.cn/pypi/simple |
| Southern University of Science and Technology | `sustech` | https://mirrors.sustech.edu.cn/pypi/web/simple |
| Official PyPI | `default` | https://pypi.org/simple |

- `cnpip sync` fetches an updated mirror catalog. Entries must be HTTPS PEP 503 URLs without credentials, ports, or query strings.
- `set` accepts a mirror alias such as `tuna`, not an arbitrary URL.

## Related tooling

cnpip manages Python package managers only. For system package managers, container images, or other language ecosystems, see [chsrc](https://github.com/RubyMetric/chsrc). Let one tool manage each package manager's configuration.

## Verification and contributing

- GitHub Actions covers Python 3.7, 3.8, 3.10, and 3.12 on Linux, macOS, and Windows.
- Package-manager code changes also run integration tests against real PDM, Poetry, and Conda CLIs.
- Use [issues](https://github.com/caoergou/cnpip/issues) for mirror availability, platform compatibility, and documentation reports.

## License

[MIT](LICENSE)

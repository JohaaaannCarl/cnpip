# cnpip

[English](./README_EN.md) · [PyPI](https://pypi.org/project/cnpip/) · [Issues](https://github.com/caoergou/cnpip/issues)

![PyPI](https://img.shields.io/pypi/v/cnpip)
![Python](https://img.shields.io/pypi/pyversions/cnpip)
![Tests](https://github.com/caoergou/cnpip/actions/workflows/test.yml/badge.svg)
![Quality](https://github.com/caoergou/cnpip/actions/workflows/quality.yml/badge.svg)
![License](https://img.shields.io/github/license/caoergou/cnpip)

**为中国网络环境配置 Python 包管理镜像。**
`cnpip` 会测试可用镜像，并把选择写入 `pip`、`uv`、`PDM`、`Poetry` 或 `Conda`。
适用于本地开发、Docker 构建和 CI 环境中的公共 Python 依赖。

官方包索引响应慢或不稳定时，切换到可用镜像可以缩短依赖安装等待。
`cnpip` 负责找镜像、测响应、写配置和恢复配置。

> `cnpip` 只管理镜像配置，不提供代理、下载缓存或私有仓库。它测的是索引响应时间；实际构建耗时还取决于构建环境、镜像状态、依赖体积和缓存命中率。

## 30 秒开始

```bash
python -m pip install cnpip
cnpip
```

在交互终端中，`cnpip` 会检测包管理工具，默认选择 `pip`，再选取响应最快的可用 PyPI 镜像。已有固定镜像时，直接指定别名：

```bash
cnpip set tuna --user --yes     # 为 pip 设置清华镜像，不提问
cnpip set tuna --uv             # 只配置 uv
cnpip set tuna --pdm            # 只配置 PDM
cnpip set tuna --poetry         # 为当前 Poetry 项目配置镜像
cnpip set --conda --yes         # 为 Conda 测试并选择其专用镜像
```

也可以临时运行：

```bash
uvx cnpip
```

`uvx cnpip` 的默认目标是用户级 `uv.toml`，不会把配置写进短生命周期的工具环境。

## CI 与自动化

自动化中请指定镜像别名、作用域和 `--yes`。命令不会交互，结果也更稳定。不要在每次构建中重新测速选源。

```yaml
# GitHub Actions：安装项目依赖前配置 pip
- name: Configure Python package index
  run: |
    python -m pip install --disable-pip-version-check cnpip
    cnpip set tuna --user --yes

- name: Install dependencies
  run: python -m pip install -r requirements.txt
```

使用建议：

- 中国网络环境中的自托管 CI：将 `cnpip` 预装进基础镜像，或从已信任的内部源安装。
- GitHub 托管 CI：先比较一次依赖安装耗时；确认有效后再固定进 workflow。

### Dockerfile

先复制依赖清单，再复制源码。源码变更时，Docker 就能复用依赖安装层。

- 下例需要 BuildKit。
- 容器构建通常以 root 运行，因此使用 `--global`。

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

`cnpip` 只写入包索引；跨构建复用下载内容依赖 BuildKit 缓存。包含私有索引凭据、内部代理或已有缓存策略的基础镜像，不应直接套用此示例。

### AI agent 的采用条件

| 条件 | 建议 |
| --- | --- |
| 安装公开 PyPI／Conda 依赖，CI 环境访问官方源慢或不稳定 | 使用 `cnpip set <预置镜像别名> --user --yes`，再执行安装 |
| 团队已有固定、受信任的镜像策略 | 显式指定 cnpip 镜像清单中的别名；不要依赖动态测速 |
| 使用私有包仓库、代理、凭据或自建缓存 | 不要用 cnpip 替代现有策略；先确认镜像不会覆盖它 |
| 锁文件含有直接包 URL，或使用 `uv sync --frozen` | 先检查锁文件；持久索引配置不能改写其中已固定的 URL |

执行前可用 `cnpip info` 检查环境、配置位置和可识别的下载源覆盖：

```bash
cnpip info
cnpip set tuna --user --yes
cnpip info
```

## 支持范围

| 工具 | cnpip 会做什么 | 配置位置 |
| --- | --- | --- |
| `pip` | 设置 PyPI `index-url`，支持用户、系统或虚拟环境作用域 | 由 `pip config` 和当前环境决定 |
| `uv` | 添加或恢复名为 `cnpip` 的索引 | 用户级 `uv.toml` |
| `PDM` | 设置或恢复 `pypi.url` | PDM 用户级配置 |
| `Poetry` | 添加或移除名为 `cnpip` 的源 | 当前项目的 `pyproject.toml` |
| `Conda` | 配置或恢复 `default_channels`、conda-forge 与 pytorch 社区源 | `CONDARC` 指定的文件，默认 `~/.condarc` |

Conda 有独立镜像清单，不能直接使用 PyPI 镜像。

## 常用命令

| 目的 | 命令 |
| --- | --- |
| 查看 PyPI 镜像及当前响应时间 | `cnpip list` |
| 测试并自动设置 | `cnpip` 或 `cnpip set` |
| 设置明确的 PyPI 镜像 | `cnpip set tuna --user --yes` |
| 只配置一个工具 | `cnpip set tuna --uv`、`--pdm`、`--poetry`、`--conda` |
| 查看环境、配置文件与可识别覆盖项 | `cnpip info` |
| 恢复 cnpip 管理的配置 | `cnpip unset`，或追加工具／作用域参数 |
| 更新镜像清单 | `cnpip sync` |

终端中，未指定工具或作用域的 `cnpip set` 会提示选择工具。脚本、CI、显式工具参数和 `--yes` 都不会触发交互。

## 速度、可靠性与安全性

- PyPI 对 `simple/pip/` 连续请求三次，至少成功两次后取中位数；Conda 测试 `pkgs/main/noarch/repodata.json`。
- 测速只反映索引响应，不能代表轮子或大文件的下载速度。构建速度应以真实依赖为准。
- `unset` 只恢复 cnpip 管理且未被后续修改的配置。发现人工或其他工具的修改时会拒绝覆盖。
- pip、uv 的文件修改使用原子替换；PDM、Poetry、Conda 使用各自的 CLI。批量设置失败时会尝试恢复已完成的操作。
- HTTPS 镜像不会写入 pip 的 `trusted-host`，以保留 TLS 校验。

## 配置覆盖

环境变量、项目配置、依赖文件和命令行参数可能覆盖 cnpip 的设置。`cnpip info` 可查看当前可识别的覆盖项。

| 工具 | 常见覆盖来源 |
| --- | --- |
| `pip` | `PIP_INDEX_URL`、`PIP_EXTRA_INDEX_URL`、`PIP_CONFIG_FILE`、requirements 文件、命令行参数 |
| `uv` | 项目 `uv.toml`／`pyproject.toml`、`UV_INDEX`、`UV_DEFAULT_INDEX`、`UV_CONFIG_FILE`、命令行参数 |
| `PDM` | 项目 source、`PDM_PYPI_URL` |
| `Poetry` | 项目 source 优先级和依赖 source 约束 |
| `Conda` | 多层 condarc、`CONDA_CHANNELS`、`-c`／`--override-channels` |

额外索引不一定只在主镜像缺包时使用。pip 配置多个索引还要评估依赖混淆（dependency confusion）风险。

## 镜像清单

| 名称 | 简写 | PyPI 地址 |
| --- | --- | --- |
| 清华大学 TUNA | `tuna` | https://pypi.tuna.tsinghua.edu.cn/simple |
| 中国科学技术大学 USTC | `ustc` | https://pypi.mirrors.ustc.edu.cn/simple |
| 阿里云 Aliyun | `aliyun` | https://mirrors.aliyun.com/pypi/simple |
| 腾讯 Tencent | `tencent` | https://mirrors.cloud.tencent.com/pypi/simple |
| 华为 Huawei | `huawei` | https://repo.huaweicloud.com/repository/pypi/simple |
| 西湖大学 Westlake | `westlake` | https://mirrors.westlake.edu.cn/pypi/simple |
| 南方科技大学 SUSTech | `sustech` | https://mirrors.sustech.edu.cn/pypi/web/simple |
| 官方 PyPI | `default` | https://pypi.org/simple |

- `cnpip sync` 可更新镜像清单，只接受符合格式要求的 HTTPS PEP 503 地址。
- `set` 只接受镜像别名，例如 `tuna`，不接受任意 URL。

## 相关工具

cnpip 只管理 Python 包管理器。
系统包管理器、容器镜像或其他语言工具可使用 [chsrc](https://github.com/RubyMetric/chsrc)。

## 验证与贡献

- GitHub Actions 覆盖 Linux、macOS、Windows 以及 Python 3.7、3.8、3.10、3.12。
- 包管理器相关代码变更会使用真实的 PDM、Poetry、Conda CLI 运行集成测试。
- 欢迎通过 [issue](https://github.com/caoergou/cnpip/issues) 报告镜像可用性、平台兼容性和文档问题。

## 许可证

本项目使用 [MIT 许可证](LICENSE)。

# localtrans

[English](./README.md) | **简体中文**

> 面向技术文本的命令行翻译器，基于本地 OpenAI 兼容接口（LM Studio / Ollama / vLLM 等）将中文翻译为专业英文。

提供 `localtrans` 与 `lt` 两个等价命令。

---

## 目录

- [安装](#安装)
- [首次配置 `lt init`](#首次配置-lt-init)
- [使用](#使用)
- [配置](#配置)
  - [环境变量](#环境变量)
  - [配置文件](#配置文件)
  - [后端示例：LM Studio / Ollama / vLLM](#后端示例)
- [升级与卸载](#升级与卸载)

---

## 安装

推荐使用 `uv`。在项目根目录执行：

```bash
# 推荐
uv tool install .

# 或
pipx install .

# 或
python -m pip install .
```

安装完成后，shell 会暴露 `localtrans` 与 `lt` 两个命令。

---

## 首次配置 `lt init`

**第一次安装后请先运行此命令**，用于写入默认模型名到本地配置文件：

```bash
lt init
```

交互式地输入要使用的模型名（例如 `gemma-3-4b-it`、`qwen2.5:7b` 等），随后写入：

```
~/.config/localtrans/config.json
```

> 后续若需修改后端地址、超时、思考模式等，见下方 [配置](#配置) 部分。

---

## 使用

### 基本翻译

```bash
lt "这个函数会导致线程阻塞"
echo "内存泄漏" | lt
```

### `-p` / `--paste`：复制到剪贴板

翻译结果写入剪贴板而不输出到终端。

```bash
lt -p "这个函数会导致线程阻塞"
```

依赖（选其一）：`wl-clipboard` / `xclip` / `xsel`（Linux），`pbcopy`（macOS），`clip`（Windows）。

### `-s` / `--selection`：翻译当前选区

读取系统主选区（primary selection），为空时回退到剪贴板；翻译结果写回剪贴板并弹出系统通知。无终端输出，适合绑定全局快捷键。

```bash
lt -s
```

窗口管理器示例：

```conf
# i3 / sway
bindsym $mod+t exec --no-startup-id lt -s

# Hyprland
bind = SUPER, T, exec, lt -s
```

依赖：`wl-clipboard` / `xclip` / `xsel` 其一 + `libnotify`（`notify-send`）。

---

## 配置

### 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `TRANS_BASE_URL` | `http://localhost:1234/v1` | OpenAI 兼容接口地址 |
| `TRANS_MODEL` | 配置文件 / `gemma-4-e4b` | 模型名，环境变量优先级最高 |
| `TRANS_TIMEOUT` | `60` | 请求超时（秒） |
| `TRANS_DISABLE_THINKING` | `false` | 设为 `true` 时发送 `reasoning_effort` 字段以关闭思考模式 |
| `TRANS_REASONING_EFFORT` | `none` | 配合上一项使用 |
| `LOCALTRANS_CONFIG_PATH` | — | 覆盖配置文件路径 |
| `XDG_CONFIG_HOME` | — | 改变配置目录根路径 |

### 配置文件

路径：`~/.config/localtrans/config.json`（可通过 `LOCALTRANS_CONFIG_PATH` / `XDG_CONFIG_HOME` 覆盖）。

`lt init` 只写入 `model` 字段。如需切换后端地址或其他参数，直接编辑该文件，或者通过环境变量覆盖。

### 后端示例

<details>
<summary><b>LM Studio</b>（默认）</summary>

LM Studio 默认监听 `http://localhost:1234/v1`，无需额外设置：

```bash
lt init   # 输入 LM Studio 中已加载的模型名
```
</details>

<details>
<summary><b>Ollama</b></summary>

Ollama 在 `11434` 端口提供 OpenAI 兼容接口。通过环境变量指向它：

```bash
export TRANS_BASE_URL="http://localhost:11434/v1"
lt init   # 输入 Ollama 模型名，例如 qwen2.5:7b
```

或写入 shell rc（`.zshrc` / `.bashrc`）使其持久生效。
</details>

<details>
<summary><b>vLLM / 其他 OpenAI 兼容服务</b></summary>

只要服务暴露 `/v1/chat/completions`，设置 `TRANS_BASE_URL` 即可：

```bash
export TRANS_BASE_URL="http://your-host:8000/v1"
export TRANS_MODEL="your-model-id"
```
</details>

<details>
<summary><b>关闭思考模式（Qwen3 / DeepSeek-R1 等）</b></summary>

```bash
export TRANS_DISABLE_THINKING=true
export TRANS_REASONING_EFFORT=none
```
</details>

---

## 升级与卸载

| 工具 | 升级 | 卸载 |
|---|---|---|
| `uv tool` | `uv tool install --reinstall .` | `uv tool uninstall localtrans` |
| `pipx` | `pipx reinstall localtrans --spec .` | `pipx uninstall localtrans` |
| `pip` | `python -m pip install --upgrade .` | `python -m pip uninstall localtrans` |

# localtrans

**English** | [简体中文](./README.zh-CN.md)

> A command-line translator for technical text. Translates Chinese to professional English via any OpenAI-compatible local backend (LM Studio / Ollama / vLLM / …).

Ships two equivalent commands: `localtrans` and `lt`.

---

## Table of Contents

- [Install](#install)
- [First-time setup: `lt init`](#first-time-setup-lt-init)
- [Usage](#usage)
- [Configuration](#configuration)
  - [Environment variables](#environment-variables)
  - [Config file](#config-file)
  - [Backend recipes: LM Studio / Ollama / vLLM](#backend-recipes)
- [Upgrade & Uninstall](#upgrade--uninstall)

---

## Install

`uv` is recommended. From the project root:

```bash
# recommended
uv tool install .

# or
pipx install .

# or
python -m pip install .
```

Both `localtrans` and `lt` will be available on your `PATH`.

---

## First-time setup: `lt init`

**Run this right after installing.** It prompts for the model name and writes it to the local config file:

```bash
lt init
```

Enter the model identifier to use (e.g. `gemma-3-4b-it`, `qwen2.5:7b`). It is written to:

```
~/.config/localtrans/config.json
```

> To change the backend URL, timeout, reasoning mode, etc., see [Configuration](#configuration) below.

---

## Usage

### Basic translation

```bash
lt "这个函数会导致线程阻塞"
echo "内存泄漏" | lt
```

### `-p` / `--paste`: copy result to clipboard

The translation is written to the clipboard instead of stdout.

```bash
lt -p "这个函数会导致线程阻塞"
```

Requires one of: `wl-clipboard` / `xclip` / `xsel` (Linux), `pbcopy` (macOS), `clip` (Windows).

### `-s` / `--selection`: translate the current selection

Reads the system primary selection (falls back to the clipboard if empty), writes the result back to the clipboard, and sends a desktop notification. No terminal output — ideal for a global hotkey.

```bash
lt -s
lt -v
```

Window-manager examples:

```conf
# i3 / sway
bindsym $mod+t exec --no-startup-id lt -s

# Hyprland
bind = SUPER, T, exec, lt -s
```

Requires: one of `wl-clipboard` / `xclip` / `xsel`, plus `libnotify` (`notify-send`).

---

`-v` / `--replace` 参数会先模拟一次 `Ctrl+C` 把选中文本抓进剪贴板，翻译后再把译文写入剪贴板并模拟一次 `Ctrl+V` 覆盖选区，适合在浏览器、编辑器、聊天窗口等任何可输入控件中"原地替换"（Chromium 系应用在 Wayland 下不支持主选区读取，这种抓取方式是可靠的）。执行结束后剪贴板内容为译文，不会自动恢复。

按键注入后端优先级：`ydotool` → `wtype` → `xdotool`。**在 Wayland（niri / Hyprland / sway 等）下强烈建议装 `ydotool` 并启用 `ydotoold` 服务**——它走 `/dev/uinput` 从内核注入，经过真实输入设备路径，compositor 用真实 keymap 解析；而 `wtype` 通过 virtual-keyboard 协议合成自己的 keymap，部分 compositor（包括 niri）在虚拟键盘断开后没能正确给 focused surface 重发真实 keymap，表现就是"替换完成后当前应用里按键错位（比如 Esc 变 v），切换一次窗口后恢复"。

可以用环境变量 `LOCALTRANS_INJECT` 强制指定后端，例如 `LOCALTRANS_INJECT=ydotool lt -v`。

> ⚠️ **`-v` 必须绑定到窗口管理器快捷键使用，不能在终端里直接 `lt -v` 运行。** 从终端运行时焦点在终端上，模拟出来的 Ctrl+C 会被终端截获并杀掉本进程自己。典型绑定示例：
>
> ```
> # Hyprland
> bind = SUPER, T, exec, lt -v
>
> # sway / i3
> bindsym $mod+t exec --no-startup-id lt -v
> ```

## Configuration

### Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `TRANS_BASE_URL` | `http://localhost:1234/v1` | OpenAI-compatible endpoint |
| `TRANS_MODEL` | config file / `gemma-4-e4b` | Model id (env var wins over config) |
| `TRANS_TIMEOUT` | `60` | Request timeout, seconds |
| `TRANS_DISABLE_THINKING` | `false` | When `true`, sends `reasoning_effort` to disable thinking |
| `TRANS_REASONING_EFFORT` | `none` | Paired with the option above |
| `LOCALTRANS_CONFIG_PATH` | — | Override config file path |
| `XDG_CONFIG_HOME` | — | Override the config root directory |

### Config file

Path: `~/.config/localtrans/config.json` (overridable via `LOCALTRANS_CONFIG_PATH` / `XDG_CONFIG_HOME`).

`lt init` only writes the `model` field. For other settings, edit the file directly or use environment variables.

### Backend recipes

<details>
<summary><b>LM Studio</b> (default)</summary>

LM Studio listens on `http://localhost:1234/v1` out of the box — no extra setup needed:

```bash
lt init   # enter the model name currently loaded in LM Studio
```
</details>

<details>
<summary><b>Ollama</b></summary>

Ollama exposes an OpenAI-compatible API on port `11434`. Point `localtrans` at it:

```bash
export TRANS_BASE_URL="http://localhost:11434/v1"
lt init   # enter an Ollama model name, e.g. qwen2.5:7b
```

Add the `export` line to your shell rc (`.zshrc` / `.bashrc`) to make it persistent.
</details>

<details>
<summary><b>vLLM / other OpenAI-compatible servers</b></summary>

Any server exposing `/v1/chat/completions` works — just set the base URL:

```bash
export TRANS_BASE_URL="http://your-host:8000/v1"
export TRANS_MODEL="your-model-id"
```
</details>

<details>
<summary><b>Disable thinking mode (Qwen3 / DeepSeek-R1 / …)</b></summary>

```bash
export TRANS_DISABLE_THINKING=true
export TRANS_REASONING_EFFORT=none
```
</details>

---

## Upgrade & Uninstall

| Tool | Upgrade | Uninstall |
|---|---|---|
| `uv tool` | `uv tool install --reinstall .` | `uv tool uninstall localtrans` |
| `pipx` | `pipx reinstall localtrans --spec .` | `pipx uninstall localtrans` |
| `pip` | `python -m pip install --upgrade .` | `python -m pip uninstall localtrans` |

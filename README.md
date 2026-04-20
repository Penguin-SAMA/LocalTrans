# localtrans

Command line translator for technical Chinese to English using a local LM Studio model.

## Install

### Option 1 (recommended): `uv tool install`

```bash
uv tool install .
```

After cloning this repository, run the command above in the project root.
`uv` will install the tool into your current user environment and expose both `localtrans` and `lt`.

### Option 2: `python -m pip install`

```bash
python -m pip install .
```

This installs the package in the current Python environment and provides `localtrans` / `lt`.

### Option 3: `pipx install`

```bash
pipx install .
```

`pipx` installs the tool in an isolated environment for your current user, while still exposing `localtrans` / `lt` globally for your shell.

## Upgrade and Uninstall

### `uv tool`

```bash
# upgrade/reinstall from current repository
uv tool install --reinstall .

# uninstall
uv tool uninstall localtrans
```

### `python -m pip`

```bash
# upgrade
python -m pip install --upgrade .

# uninstall
python -m pip uninstall localtrans
```

### `pipx`

```bash
# upgrade from current repository
pipx reinstall localtrans --spec .

# uninstall
pipx uninstall localtrans
```

## Usage

```bash
localtrans "这个函数会导致线程阻塞"
echo "内存泄漏" | localtrans
localtrans init
lt "这个函数会导致线程阻塞"
echo "内存泄漏" | lt
lt init
lt -p "这个函数会导致线程阻塞"
lt -s
lt -v
```

`localtrans init` 会提示输入模型名，并写入本地配置文件。

`-p` / `--paste` 参数会将翻译结果复制到系统剪贴板，不在命令行输出；使用前需安装 `wl-clipboard`、`xclip` 或 `xsel`（macOS/Windows 分别使用内置的 `pbcopy` / `clip`）。

`-s` / `--selection` 参数会读取系统主选区（primary selection），若为空则回退到剪贴板，翻译后写回剪贴板，并通过系统通知（Linux `notify-send` / macOS `osascript`）提示结果。整个流程无终端输出，适合绑定窗口管理器快捷键，例如：

```
# i3 / sway
bindsym $mod+t exec --no-startup-id localtrans -s

# Hyprland
bind = SUPER, T, exec, localtrans -s
```

触发前先用鼠标选中任意一段文本即可。需安装 `wl-clipboard` / `xclip` / `xsel` 其一用于读写剪贴板，以及 `libnotify`（提供 `notify-send`）用于通知。

`-v` / `--replace` 参数会先模拟一次 `Ctrl+C` 把选中文本抓进剪贴板，翻译后再把译文写入剪贴板并模拟一次 `Ctrl+V` 覆盖选区，适合在浏览器、编辑器、聊天窗口等任何可输入控件中"原地替换"（Chromium 系应用在 Wayland 下不支持主选区读取，这种抓取方式是可靠的）。需要额外安装 `wtype`（Wayland）、`ydotool` 或 `xdotool`（X11）其一用于 `Ctrl+C` / `Ctrl+V` 的按键注入。执行结束后剪贴板内容为译文，不会自动恢复。

## Configuration

- `TRANS_BASE_URL` (default: `http://localhost:1234/v1`)
- `TRANS_MODEL` (highest priority, default from config or `gemma-4-e4b`)
- `TRANS_TIMEOUT` in seconds (default: `60`)
- `TRANS_DISABLE_THINKING` (default: `false`; set to `true` to send `reasoning_effort` and disable thinking mode)
- `TRANS_REASONING_EFFORT` (default: `none`)
- Config file: `~/.config/localtrans/config.json` (`XDG_CONFIG_HOME`/`LOCALTRANS_CONFIG_PATH` 可覆盖)

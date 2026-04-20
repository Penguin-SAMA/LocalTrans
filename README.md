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
```

`localtrans init` 会提示输入模型名，并写入本地配置文件。

## Configuration

- `TRANS_BASE_URL` (default: `http://localhost:1234/v1`)
- `TRANS_MODEL` (highest priority, default from config or `gemma-4-e4b`)
- `TRANS_TIMEOUT` in seconds (default: `60`)
- `TRANS_DISABLE_THINKING` (default: `false`; set to `true` to send `reasoning_effort` and disable thinking mode)
- `TRANS_REASONING_EFFORT` (default: `none`)
- Config file: `~/.config/localtrans/config.json` (`XDG_CONFIG_HOME`/`LOCALTRANS_CONFIG_PATH` 可覆盖)

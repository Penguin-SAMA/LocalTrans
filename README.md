# localtrans

Command line translator for technical Chinese to English using a local LM Studio model.

## Install

```bash
mamba create -y -p .mamba-venv python=3.12
uv pip install --python .mamba-venv/bin/python -e .
mamba activate .mamba-venv
```

If your system only has `micromamba`, replace `mamba` with `micromamba`.

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

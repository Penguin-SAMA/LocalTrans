import argparse
import os
import shutil
import signal
import subprocess
import sys
import time

from localtrans_cli.translator import TranslationError, configure_model, translate_text


def _read_input_text(parts: list[str]) -> str:
    if parts:
        return " ".join(parts).strip()
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    return ""


def _run_capture(cmd: list[str]) -> str | None:
    try:
        result = subprocess.run(cmd, capture_output=True, check=True)
    except (subprocess.CalledProcessError, OSError):
        return None
    return result.stdout.decode("utf-8", errors="replace")


def _read_from_selection() -> str:
    primary: list[list[str]] = []
    if shutil.which("wl-paste"):
        primary.append(["wl-paste", "--primary", "--no-newline"])
    if shutil.which("xclip"):
        primary.append(["xclip", "-o", "-selection", "primary"])
    if shutil.which("xsel"):
        primary.append(["xsel", "--primary", "--output"])

    clipboard: list[list[str]] = []
    if shutil.which("wl-paste"):
        clipboard.append(["wl-paste", "--no-newline"])
    if shutil.which("xclip"):
        clipboard.append(["xclip", "-o", "-selection", "clipboard"])
    if shutil.which("xsel"):
        clipboard.append(["xsel", "--clipboard", "--output"])
    if sys.platform == "darwin" and shutil.which("pbpaste"):
        clipboard.append(["pbpaste"])

    for cmd in primary + clipboard:
        out = _run_capture(cmd)
        if out and out.strip():
            return out.strip()
    return ""


def _copy_to_clipboard(text: str) -> None:
    candidates: list[list[str]] = []
    if shutil.which("wl-copy"):
        candidates.append(["wl-copy"])
    if shutil.which("xclip"):
        candidates.append(["xclip", "-selection", "clipboard"])
    if shutil.which("xsel"):
        candidates.append(["xsel", "--clipboard", "--input"])
    if sys.platform == "darwin" and shutil.which("pbcopy"):
        candidates.append(["pbcopy"])
    if sys.platform.startswith("win") and shutil.which("clip"):
        candidates.append(["clip"])

    if not candidates:
        raise TranslationError(
            "未找到剪贴板工具，请安装 wl-clipboard / xclip / xsel 后重试。"
        )

    last_error: Exception | None = None
    for cmd in candidates:
        try:
            subprocess.run(cmd, input=text.encode("utf-8"), check=True)
            return
        except (subprocess.CalledProcessError, OSError) as exc:
            last_error = exc

    raise TranslationError(f"写入剪贴板失败: {last_error}")


_EVDEV_KEYCODES = {"c": 46, "v": 47}


def _build_inject_cmd(tool: str, key: str) -> list[str] | None:
    if tool == "ydotool":
        keycode = _EVDEV_KEYCODES[key]
        # Kernel-level /dev/uinput injection via ydotoold. Preferred on
        # Wayland because it bypasses the virtual-keyboard protocol whose
        # keymap handoff is buggy on several compositors (including niri):
        # wtype-style injection can leave the focused surface stuck with
        # wtype's synthetic keymap until the user refocuses.
        return [
            "ydotool",
            "key",
            "29:1",
            f"{keycode}:1",
            f"{keycode}:0",
            "29:0",
        ]
    if tool == "wtype":
        # -k dispatches as a key event so Ctrl actually combines with it.
        return ["wtype", "-M", "ctrl", "-k", key, "-m", "ctrl"]
    if tool == "xdotool":
        return ["xdotool", "key", "--clearmodifiers", f"ctrl+{key}"]
    return None


def _resolve_inject_order() -> list[str]:
    override = os.environ.get("LOCALTRANS_INJECT", "").strip().lower()
    if override:
        tools = [t.strip() for t in override.split(",") if t.strip()]
    else:
        tools = ["ydotool", "wtype", "xdotool"]
    return [t for t in tools if shutil.which(t)]


def _send_ctrl_key(key: str) -> None:
    if key not in _EVDEV_KEYCODES:
        raise TranslationError(f"不支持的组合键: ctrl+{key}")

    tools = _resolve_inject_order()
    if not tools:
        raise TranslationError(
            "未找到按键注入工具，请安装 ydotool / wtype / xdotool 后重试。"
        )

    last_error: Exception | None = None
    for tool in tools:
        cmd = _build_inject_cmd(tool, key)
        if cmd is None:
            continue
        try:
            subprocess.run(cmd, check=True)
            return
        except (subprocess.CalledProcessError, OSError) as exc:
            last_error = exc

    raise TranslationError(f"按键注入失败: {last_error}")


def _read_clipboard() -> str:
    clipboard: list[list[str]] = []
    if shutil.which("wl-paste"):
        clipboard.append(["wl-paste", "--no-newline"])
    if shutil.which("xclip"):
        clipboard.append(["xclip", "-o", "-selection", "clipboard"])
    if shutil.which("xsel"):
        clipboard.append(["xsel", "--clipboard", "--output"])
    if sys.platform == "darwin" and shutil.which("pbpaste"):
        clipboard.append(["pbpaste"])

    for cmd in clipboard:
        out = _run_capture(cmd)
        if out and out.strip():
            return out.strip()
    return ""


def _notify(title: str, body: str, *, urgency: str = "normal") -> None:
    body = body.strip()
    if sys.platform == "darwin" and shutil.which("osascript"):
        safe_title = title.replace('"', '\\"')
        safe_body = body.replace('"', '\\"')
        script = f'display notification "{safe_body}" with title "{safe_title}"'
        try:
            subprocess.run(["osascript", "-e", script], check=False)
        except OSError:
            pass
        return

    if shutil.which("notify-send"):
        try:
            subprocess.run(
                ["notify-send", "-u", urgency, "-a", "localtrans", title, body],
                check=False,
            )
        except OSError:
            pass
        return


def _run_init(extra_args: list[str]) -> int:
    if extra_args:
        print("Usage: localtrans init", file=sys.stderr)
        return 2

    try:
        model = input("请输入模型名: ").strip()
    except EOFError:
        print("模型名输入失败。", file=sys.stderr)
        return 2

    if not model:
        print("模型名不能为空。", file=sys.stderr)
        return 2

    try:
        config_path = configure_model(model)
    except TranslationError as exc:
        print(f"Init failed: {exc}", file=sys.stderr)
        return 1

    print(f"模型已配置: {model}")
    print(f"配置文件: {config_path}")
    return 0


def _run_selection() -> int:
    text = _read_from_selection()
    if not text:
        _notify("翻译失败", "未读取到选中文本", urgency="critical")
        return 2

    try:
        translated = translate_text(text)
    except TranslationError as exc:
        _notify("翻译失败", str(exc), urgency="critical")
        return 1

    try:
        _copy_to_clipboard(translated)
    except TranslationError as exc:
        _notify("翻译失败", str(exc), urgency="critical")
        return 1

    preview = translated if len(translated) <= 200 else translated[:200] + "…"
    _notify("翻译完成", preview)
    return 0


def _run_replace() -> int:
    if sys.stdout.isatty() or sys.stdin.isatty():
        print(
            "警告: -v 在终端里直接运行无效——模拟的 Ctrl+C 会被本终端截获并终止本进程。\n"
            "请把它绑定到窗口管理器快捷键（例如 Hyprland: bind = SUPER, T, exec, lt -v），\n"
            "然后在浏览器/编辑器里选中文本后触发。",
            file=sys.stderr,
        )

    # Ignore SIGINT during the replace flow: our injected Ctrl+C can land on
    # the calling terminal and SIGINT this process, producing a confusing
    # traceback even though the underlying flow is otherwise fine.
    prev_sigint = signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        # Give the user a moment to physically release the shortcut's
        # modifier keys (e.g. Super+Shift+T) before we start injecting our
        # own Ctrl+C / Ctrl+V. If we inject while Super/Shift are still
        # held, the compositor sees Ctrl+Super+Shift+C which is neither
        # "copy" nor anything sensible, and leaves the modifier state
        # confused.
        time.sleep(0.25)

        try:
            _send_ctrl_key("c")
        except TranslationError as exc:
            _notify("替换失败", str(exc), urgency="critical")
            return 1

        time.sleep(0.15)

        text = _read_clipboard()
        if not text:
            _notify(
                "替换失败",
                "未读取到选中文本（Ctrl+C 未抓到内容，请确认已选中）",
                urgency="critical",
            )
            return 2

        try:
            translated = translate_text(text)
        except TranslationError as exc:
            _notify("替换失败", str(exc), urgency="critical")
            return 1

        try:
            _copy_to_clipboard(translated)
        except TranslationError as exc:
            _notify("替换失败", str(exc), urgency="critical")
            return 1

        time.sleep(0.12)

        try:
            _send_ctrl_key("v")
        except TranslationError as exc:
            _notify("替换失败", str(exc), urgency="critical")
            return 1

        preview = translated if len(translated) <= 200 else translated[:200] + "…"
        _notify("替换完成", preview)
        return 0
    finally:
        signal.signal(signal.SIGINT, prev_sigint)


def main() -> int:
    argv = sys.argv[1:]
    if argv and argv[0] == "init":
        return _run_init(argv[1:])

    parser = argparse.ArgumentParser(
        prog="localtrans",
        description="Translate text to professional English using LM Studio.",
    )
    parser.add_argument(
        "-p",
        "--paste",
        action="store_true",
        help="将翻译结果复制到剪贴板，不在命令行输出。",
    )
    parser.add_argument(
        "-s",
        "--selection",
        action="store_true",
        help="读取系统主选区/剪贴板中的文本翻译后写回剪贴板，并通过系统通知提示。",
    )
    parser.add_argument(
        "-v",
        "--replace",
        action="store_true",
        help="对当前选中文本发起 Ctrl+C 抓取、翻译后再通过 Ctrl+V 粘贴覆盖选区。",
    )
    parser.add_argument("text", nargs="*", help="Text to translate.")
    args = parser.parse_args(argv)

    if args.selection and args.replace:
        print("--selection 与 --replace 不能同时使用。", file=sys.stderr)
        return 2

    if args.selection:
        if args.text:
            print("--selection 不接受位置参数。", file=sys.stderr)
            return 2
        return _run_selection()

    if args.replace:
        if args.text:
            print("--replace 不接受位置参数。", file=sys.stderr)
            return 2
        return _run_replace()

    text = _read_input_text(args.text)
    if not text:
        print("No input text. Use: localtrans \"...\" or echo \"...\" | localtrans", file=sys.stderr)
        return 2

    try:
        translated = translate_text(text)
    except TranslationError as exc:
        print(f"Translation failed: {exc}", file=sys.stderr)
        return 1

    if args.paste:
        try:
            _copy_to_clipboard(translated)
        except TranslationError as exc:
            print(f"Translation failed: {exc}", file=sys.stderr)
            return 1
        return 0

    print(translated)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

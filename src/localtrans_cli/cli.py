import argparse
import shutil
import subprocess
import sys

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


def _type_text(text: str) -> None:
    candidates: list[list[str]] = []
    if shutil.which("wtype"):
        candidates.append(["wtype", "--", text])
    if shutil.which("ydotool"):
        candidates.append(["ydotool", "type", "--", text])
    if shutil.which("xdotool"):
        candidates.append(["xdotool", "type", "--clearmodifiers", "--", text])

    if not candidates:
        raise TranslationError(
            "未找到按键注入工具，请安装 wtype / ydotool / xdotool 后重试。"
        )

    last_error: Exception | None = None
    for cmd in candidates:
        try:
            subprocess.run(cmd, check=True)
            return
        except (subprocess.CalledProcessError, OSError) as exc:
            last_error = exc

    raise TranslationError(f"按键注入失败: {last_error}")


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
    text = _read_from_selection()
    if not text:
        _notify("替换失败", "未读取到选中文本", urgency="critical")
        return 2

    try:
        translated = translate_text(text)
    except TranslationError as exc:
        _notify("替换失败", str(exc), urgency="critical")
        return 1

    try:
        _type_text(translated)
    except TranslationError as exc:
        _notify("替换失败", str(exc), urgency="critical")
        return 1

    preview = translated if len(translated) <= 200 else translated[:200] + "…"
    _notify("替换完成", preview)
    return 0


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
        help="读取系统主选区/剪贴板中的文本，翻译后通过模拟键入直接替换选中内容。",
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

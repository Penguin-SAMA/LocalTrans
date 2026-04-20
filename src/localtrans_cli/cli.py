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
    parser.add_argument("text", nargs="*", help="Text to translate.")
    args = parser.parse_args(argv)

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

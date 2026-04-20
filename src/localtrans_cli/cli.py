import argparse
import sys

from localtrans_cli.translator import TranslationError, configure_model, translate_text


def _read_input_text(parts: list[str]) -> str:
    if parts:
        return " ".join(parts).strip()
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    return ""


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

    print(translated)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

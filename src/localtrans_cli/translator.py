import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request


DEFAULT_BASE_URL = "http://localhost:1234/v1"
DEFAULT_MODEL = "gemma-4-e4b"
DEFAULT_TIMEOUT = 60.0
DEFAULT_REASONING_EFFORT = "none"

SYSTEM_PROMPT = (
    "You are a senior technical translator for computer science and software engineering. "
    "Translate the user text into natural, precise English. "
    "Preserve code, commands, paths, API names, identifiers, and error text exactly when needed. "
    "Use professional technical terminology. "
    "Do not output your reasoning process. "
    "Do not provide options, explanations, or notes. "
    "Return only the final translation in one line."
)


class TranslationError(RuntimeError):
    """Raised when translation request fails."""


_THINK_TAG_RE = re.compile(r"<think>.*?</think>", flags=re.IGNORECASE | re.DOTALL)
_TRANSLATION_MARKER_RE = re.compile(
    r"(?:^|\n)\s*(?:translation|translated text|final translation|译文|翻译)\s*[:：]\s*(.+)\Z",
    flags=re.IGNORECASE | re.DOTALL,
)
_FULL_REPEAT_RE = re.compile(r"(.{4,}?)\1+\Z", flags=re.DOTALL)
_META_LINE_PREFIX_RE = re.compile(
    r"^\s*(?:plan|analysis|reasoning|thoughts?|思路|分析)\s*[:：]\s*",
    flags=re.IGNORECASE,
)
_REASONING_HINT_RE = re.compile(
    r"(the user input is|as a .*translator|i need to|i should|i will provide|"
    r"depending on context|literal and safest|there is no technical content|"
    r"plan\s*[:：]|analysis\s*[:：])",
    flags=re.IGNORECASE,
)


_FIRST_ALPHA_TOKEN_RE = re.compile(r"[A-Za-z]+")


def _is_phrase_or_term(source_text: str, translated_text: str) -> bool:
    raw_source = source_text.strip()
    if not raw_source:
        return False
    if "\n" in raw_source:
        return False
    if re.search(r"[。！？.!?]", raw_source):
        return False
    if re.search(r"[，；：,:;]", raw_source):
        return False

    raw_translated = translated_text.strip()
    if not raw_translated:
        return False
    if "\n" in raw_translated:
        return False
    if re.search(r"[。！？.!?]\s*$", raw_translated):
        return False

    english_tokens = re.findall(
        r"[A-Za-z0-9_]+(?:[-/][A-Za-z0-9_]+)*", raw_translated
    )
    if english_tokens:
        return len(english_tokens) <= 3

    cjk_count = len(re.findall(r"[\u4e00-\u9fff]", raw_translated))
    if cjk_count:
        return cjk_count <= 12

    return len(raw_translated) <= 24


def _decapitalize_first_alpha_word(text: str) -> str:
    match = _FIRST_ALPHA_TOKEN_RE.search(text)
    if not match:
        return text

    token = match.group(0)
    if len(token) >= 2 and token[0].isupper() and token[1:].islower():
        start = match.start()
        return text[:start] + token[0].lower() + text[start + 1 :]
    return text


def _capitalize_first_alpha_word(text: str) -> str:
    match = _FIRST_ALPHA_TOKEN_RE.search(text)
    if not match:
        return text

    token = match.group(0)
    if token.islower() and len(token) >= 2:
        start = match.start()
        return text[:start] + token[0].upper() + text[start + 1 :]
    return text


def _format_translation(text: str, source_text: str) -> str:
    if _is_phrase_or_term(source_text, text):
        return _decapitalize_first_alpha_word(text)
    return _capitalize_first_alpha_word(text)


def _parse_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default

    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise TranslationError(f"{name} must be a boolean value (true/false or 1/0).")


def get_reasoning_config() -> tuple[bool, str]:
    disable_thinking = _parse_bool_env("TRANS_DISABLE_THINKING", False)
    reasoning_effort = os.getenv(
        "TRANS_REASONING_EFFORT", DEFAULT_REASONING_EFFORT
    ).strip()
    if not reasoning_effort:
        raise TranslationError("TRANS_REASONING_EFFORT is empty.")
    return disable_thinking, reasoning_effort


def _strip_wrapper_quotes(text: str) -> str:
    pairs = [('"', '"'), ("'", "'"), ("`", "`"), ("“", "”"), ("‘", "’")]
    cleaned = text.strip()
    for left, right in pairs:
        if cleaned.startswith(left) and cleaned.endswith(right) and len(cleaned) >= 2:
            return cleaned[1:-1].strip()
    return cleaned


def _dedupe_full_repeat(text: str) -> str:
    match = _FULL_REPEAT_RE.fullmatch(text)
    if not match:
        return text
    return match.group(1).strip()


def _extract_translation(content: str) -> str:
    cleaned = _THINK_TAG_RE.sub("", content).strip()
    marker_match = _TRANSLATION_MARKER_RE.search(cleaned)
    if marker_match:
        cleaned = marker_match.group(1).strip()
    elif _REASONING_HINT_RE.search(cleaned):
        blocks = [b.strip() for b in re.split(r"\n\s*\n", cleaned) if b.strip()]
        if blocks:
            tail = blocks[-1]
            tail = _META_LINE_PREFIX_RE.sub("", tail).strip()
            sentence_tail = [s.strip() for s in re.split(r"[。！？.!?]+\s*", tail) if s.strip()]
            if sentence_tail:
                tail = sentence_tail[-1]
            cleaned = tail

    cleaned = _strip_wrapper_quotes(cleaned)
    cleaned = _dedupe_full_repeat(cleaned)

    if not cleaned:
        raise TranslationError("Model returned empty translation.")
    return cleaned


def _config_path() -> Path:
    raw_path = os.getenv("LOCALTRANS_CONFIG_PATH", "").strip()
    if raw_path:
        return Path(raw_path).expanduser()

    config_home = os.getenv("XDG_CONFIG_HOME", "").strip()
    if config_home:
        root = Path(config_home).expanduser()
    else:
        root = Path.home() / ".config"
    return root / "localtrans" / "config.json"


def _load_file_config() -> dict[str, object]:
    config_path = _config_path()
    if not config_path.exists():
        return {}

    try:
        parsed = json.loads(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise TranslationError(f"Cannot read config file: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise TranslationError(f"Config file is not valid JSON: {config_path}") from exc

    if not isinstance(parsed, dict):
        raise TranslationError(f"Config file must be a JSON object: {config_path}")
    return parsed


def configure_model(model: str) -> Path:
    model_name = model.strip()
    if not model_name:
        raise TranslationError("Model name cannot be empty.")

    config_path = _config_path()
    config = _load_file_config()
    config["model"] = model_name

    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps(config, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise TranslationError(f"Cannot write config file: {config_path}") from exc

    return config_path


def get_config() -> tuple[str, str, float]:
    file_config = _load_file_config()
    base_url = os.getenv("TRANS_BASE_URL", DEFAULT_BASE_URL).strip()
    timeout_raw = os.getenv("TRANS_TIMEOUT", str(DEFAULT_TIMEOUT)).strip()
    model_env = os.getenv("TRANS_MODEL")
    if model_env is None:
        model_raw = file_config.get("model", DEFAULT_MODEL)
        model = str(model_raw).strip()
    else:
        model = model_env.strip()

    if not base_url:
        raise TranslationError("TRANS_BASE_URL is empty.")
    if not model:
        raise TranslationError("TRANS_MODEL is empty.")

    try:
        timeout = float(timeout_raw)
    except ValueError as exc:
        raise TranslationError("TRANS_TIMEOUT must be a number.") from exc
    if timeout <= 0:
        raise TranslationError("TRANS_TIMEOUT must be greater than 0.")

    return base_url.rstrip("/"), model, timeout


def translate_text(text: str) -> str:
    if not text.strip():
        raise TranslationError("Input text is empty.")

    base_url, model, timeout = get_config()
    disable_thinking, reasoning_effort = get_reasoning_config()
    endpoint = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
    }
    if disable_thinking:
        payload["reasoning_effort"] = reasoning_effort

    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise TranslationError(
            f"LM Studio HTTP {exc.code}: {detail[:200].strip()}"
        ) from exc
    except urllib.error.URLError as exc:
        raise TranslationError(f"Cannot reach LM Studio: {exc.reason}") from exc
    except TimeoutError as exc:
        raise TranslationError("LM Studio request timed out.") from exc

    try:
        parsed = json.loads(body)
        content = parsed["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise TranslationError("Unexpected response format from LM Studio.") from exc

    extracted = _extract_translation(str(content))
    return _format_translation(extracted, text)

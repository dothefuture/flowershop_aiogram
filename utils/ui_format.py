"""Декоративное оформление сообщений бота."""


def frame_open(title: str, *, emoji: str = "🌸") -> str:
    return f"╭─ {emoji} <b>{title}</b> ─╮"


def frame_line(content: str) -> str:
    return f"│ {content}"


def frame_close() -> str:
    return "╰──────────────────────╯"


def frame_block(title: str, lines: list[str], *, emoji: str = "🌸") -> str:
    parts = [frame_open(title, emoji=emoji), ""]
    for line in lines:
        parts.append(frame_line(line))
    parts.extend(["", frame_close()])
    return "\n".join(parts)

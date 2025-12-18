import logging
import re

# Regex để bắt các ANSI escape code (màu, bold, v.v.)
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


class StripAnsiFilter(logging.Filter):
    """Filter dùng để xoá mã màu ANSI khỏi log record (phù hợp cho file log)."""

    def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
        if isinstance(record.msg, str):
            record.msg = ANSI_ESCAPE_RE.sub("", record.msg)
        return True


def attach_strip_ansi_to_file_handlers() -> None:
    """
    Gắn StripAnsiFilter vào tất cả FileHandler hiện có.

    Nên gọi sau khi logging.config.fileConfig(...) đã chạy,
    để các handler từ logging.ini đã được khởi tạo đầy đủ.
    """
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        if isinstance(handler, logging.FileHandler):
            handler.addFilter(StripAnsiFilter())



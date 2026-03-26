def _format_log(level: str, **kwargs) -> str:
    # start log message with the log level
    parts = [f"level={level}"]

    # add each key=value pair into the log message
    for key, value in kwargs.items():
        # skip fields that are None so logs stay cleaner
        if value is None:
            continue
        parts.append(f"{key}={value}")

    # join all log fields into one single line
    return " ".join(parts)


def log_info(**kwargs):
    # print an INFO level structured log
    print(_format_log("INFO", **kwargs), flush=True)


def log_warning(**kwargs):
    # print a WARNING level structured log
    print(_format_log("WARNING", **kwargs), flush=True)


def log_error(**kwargs):
    # print an ERROR level structured log
    print(_format_log("ERROR", **kwargs), flush=True)
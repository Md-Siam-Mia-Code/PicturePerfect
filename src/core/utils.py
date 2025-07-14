# src/core/utils.py


def format_size(byte_count: int) -> str:
    """Formats a byte count into a human-readable string (KB, MB, GB)."""
    if byte_count is None:
        return "0 B"

    power = 1024
    n = 0
    power_labels = {0: "B", 1: "KB", 2: "MB", 3: "GB", 4: "TB"}

    while byte_count >= power and n < len(power_labels) - 1:
        byte_count /= power
        n += 1

    return f"{byte_count:.2f} {power_labels[n]}"

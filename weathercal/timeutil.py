import time


def iso_epoch(value):
    if not isinstance(value, str) or len(value) < 19:
        return None
    try:
        year = int(value[0:4])
        month = int(value[5:7])
        day = int(value[8:10])
        hour = int(value[11:13])
        minute = int(value[14:16])
        second = int(value[17:19])
        fields = (year, month, day, hour, minute, second, 0, 0)
        try:
            epoch = time.mktime(fields)
        except TypeError:
            epoch = time.mktime(fields + (-1,))
        if value.endswith("Z"):
            return epoch
        sign_at = max(value.rfind("+"), value.rfind("-"))
        if sign_at > 18:
            sign = 1 if value[sign_at] == "+" else -1
            offset = int(value[sign_at + 1 : sign_at + 3]) * 3600
            offset += int(value[sign_at + 4 : sign_at + 6]) * 60
            epoch -= sign * offset
        return epoch
    except (ValueError, IndexError, TypeError):
        return None


def age_seconds(timestamp, now=None):
    epoch = iso_epoch(timestamp)
    if epoch is None:
        return None
    return max(0, (time.time() if now is None else now) - epoch)

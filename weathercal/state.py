from .compat import json


class WeatherState:
    def __init__(self):
        self.data = {
            "current": {},
            "hourly": [],
            "weather_status": {},
            "generated_at": None,
            "rain": {},
            "wind": {},
            "server": {},
        }
        self.revisions = {}

    def update(self, topic_name, payload):
        if isinstance(payload, bytes):
            payload = payload.decode()
        value = json.loads(payload) if isinstance(payload, str) else payload
        target = "server" if topic_name == "server_status" else topic_name
        previous = self.data.get(target)
        if previous == value:
            return False
        self.data[target] = value
        self.revisions[topic_name] = self.revisions.get(topic_name, 0) + 1
        if topic_name == "weather_status" and isinstance(value, dict):
            self.data["generated_at"] = value.get(
                "generated_at", self.data["generated_at"]
            )
        return True

    def get(self, path, default=None):
        value = self.data
        for component in path.split("."):
            if isinstance(value, dict):
                value = value.get(component, default)
            elif isinstance(value, list):
                try:
                    value = value[int(component)]
                except (ValueError, IndexError):
                    return default
            else:
                return default
            if value is default:
                return default
        return value

    def generated_at(self):
        value = self.data.get("generated_at")
        if isinstance(value, str):
            return value
        return None

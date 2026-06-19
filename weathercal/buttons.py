from .compat import ticks_diff


class ButtonController:
    def __init__(self, specs, pin_factory, debounce_ms=180):
        self.buttons = {}
        self.debounce_ms = debounce_ms
        for action, spec in specs.items():
            pin = pin_factory(spec["pin"], spec.get("active_low", True))
            self.buttons[action] = {
                "pin": pin,
                "active_low": spec.get("active_low", True),
                "last": False,
                "changed_at": 0,
                "emitted": False,
            }

    def poll(self, now_ms):
        actions = []
        for action, state in self.buttons.items():
            raw = bool(state["pin"].value())
            pressed = not raw if state["active_low"] else raw
            if pressed != state["last"]:
                state["last"] = pressed
                state["changed_at"] = now_ms
                state["emitted"] = False
            if (
                pressed
                and not state["emitted"]
                and ticks_diff(now_ms, state["changed_at"]) >= self.debounce_ms
            ):
                state["emitted"] = True
                actions.append(action)
        return actions

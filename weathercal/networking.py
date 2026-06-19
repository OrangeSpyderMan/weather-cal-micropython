import time


class NetworkManager:
    def __init__(self, ssid, password, timeout_s=30):
        self.ssid = ssid
        self.password = password
        self.timeout_s = timeout_s
        self.wlan = None

    def connect(self):
        import network

        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        if not self.wlan.isconnected():
            self.wlan.connect(self.ssid, self.password)
            deadline = time.time() + self.timeout_s
            while not self.wlan.isconnected() and time.time() < deadline:
                time.sleep(0.25)
        if not self.wlan.isconnected():
            raise OSError("Wi-Fi connection timed out")
        return self.wlan.ifconfig()

    def connected(self):
        return bool(self.wlan and self.wlan.isconnected())

    def sync_clock(self):
        try:
            import ntptime

            ntptime.settime()
            return True
        except Exception as exc:
            print("NTP sync failed:", exc)
            return False

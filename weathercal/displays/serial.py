from .base import Display


class SerialDisplay(Display):
    def begin(self, page_id):
        self.commands = [("begin", page_id)]

    def text(self, widget, value):
        self.commands.append(("text", widget, value))

    def icon(self, widget, name):
        self.commands.append(("icon", widget, name))

    def hourly(self, widget, entries):
        self.commands.append(("hourly", widget, entries))

    def badge(self, value, secondary=False):
        self.commands.append(("badge", value, secondary))

    def end(self):
        for command in self.commands:
            print(command)

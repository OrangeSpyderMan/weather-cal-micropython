class Display:
    def begin(self, page_id):
        raise NotImplementedError

    def text(self, widget, value):
        raise NotImplementedError

    def icon(self, widget, name):
        raise NotImplementedError

    def summary(self, widget, pieces):
        self.text(widget, " ".join(pieces))

    def hourly(self, widget, entries):
        raise NotImplementedError

    def badge(self, value, secondary=False):
        pass

    def end(self):
        raise NotImplementedError

    def status(self, title, detail=""):
        self.begin("status")
        self.text({"x": 4, "y": 4, "row": 0, "col": 0}, title)
        if detail:
            self.text({"x": 4, "y": 18, "row": 1, "col": 0}, detail)
        self.end()

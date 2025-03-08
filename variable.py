class VariableUpdateListener:

    def on_update(self, value):
        del value
        pass


class Variable:

    value = ""

    listeners = []

    def notify(self, value):
        for listener in self.listeners:
            listener.on_update(value)

    def get(self):
        return self.value

    def set(self, value):
        self.notify(value)
        self.value = value

    def subscribe(self, listener):
        self.listeners.append(listener)

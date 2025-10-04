class BaseAgent:
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role

    def observe(self, task: str):
        print(f"[{self.name}] Task: {task}")

    def act(self, **kwargs):
        raise NotImplementedError("Agent must define its own act() method.")

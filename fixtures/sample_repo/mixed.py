"""Mixed-quality module with a class and a small helper."""


class Greeter:
    """Produce simple greeting strings."""

    def greet(self, name: str) -> str:
        """Return a short greeting for *name*."""
        return f"Hello, {name}!"

    def shout(self, name):
        # No type hints, unused import-style noise via late locals, weak style.
        msg = "HEY " + str(name) + "!!!"
        unused = 42
        return msg


def _private_helper(values):
    total = 0
    for v in values:
        total = total + v
    return total

from lumen import Interpreter


def run(source, inputs=None):
    """Run Lumen code and return everything it printed, as a list of lines."""
    output = []
    feed = iter(inputs or [])
    interp = Interpreter(write=output.append, read=lambda prompt="": next(feed))
    interp.run(source)
    return output

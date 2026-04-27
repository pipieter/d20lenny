from d20 import roll

try:
    import readline  # type: ignore
except:
    pass  # readline not found, don't support history

while True:
    try:
        expr = input("> ").strip().lower()
    except KeyboardInterrupt:
        print()
        break

    if expr == "":
        continue

    stop_words = ["quit", "stop", "halt", "exit"]
    if expr in stop_words:
        break

    try:
        result = roll(expr)
        print(result.result)
    except Exception as e:
        print(f"Could not parse '{expr}': {str(e)}")

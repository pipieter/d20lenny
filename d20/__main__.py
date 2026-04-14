from d20 import roll

try:
    import readline
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
        roll_result = roll(expr, allow_comments=True)
        print(str(roll_result))
    except:
        print(f"Could not parse '{expr}'")

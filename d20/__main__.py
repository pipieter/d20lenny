from d20 import roll

while True:
    expr = input("> ").strip().lower()

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

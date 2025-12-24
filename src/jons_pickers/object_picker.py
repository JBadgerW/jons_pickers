import curses

PROMPT = "Select: "


def _object_picker_ui(stdscr, objects, multi, prompt):
    def first_match_index():
        for i, (_, is_match) in enumerate(display):
            if is_match:
                return i
        return 0

    curses.curs_set(1)
    stdscr.keypad(True)

    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_WHITE, -1)
    curses.init_pair(3, 8, -1)  # gray for non-matches
    curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLUE)  # selected

    stdscr.bkgd(" ", curses.color_pair(1))
    stdscr.clear()
    stdscr.border()

    query = ""
    selected_idx = 0
    scroll = 0
    selected = set()

    prev_query = None

    while True:
        # --- Build display list ---
        def matches(obj):
            return query.lower() in str(obj).lower()

        matching = [(obj, True) for obj in objects if matches(obj)]
        non_matching = [(obj, False) for obj in objects if not matches(obj)]
        display = matching + non_matching

        if selected_idx >= len(display):
            selected_idx = max(0, len(display) - 1)

        h, w = stdscr.getmaxyx()

        # Interior layout (safe from borders)
        list_top = 3
        max_rows = h - list_top - 2
        content_x = 3
        content_width = w - content_x - 1  # never touches right border

        if selected_idx < scroll:
            scroll = selected_idx
        elif selected_idx >= scroll + max_rows:
            scroll = selected_idx - max_rows + 1

        visible = display[scroll: scroll + max_rows]

        stdscr.border()

        # --- Prompt ---
        if query != prev_query:
            stdscr.move(1, 1)
            stdscr.addstr(1, 1, " " * (w - 3))
            stdscr.addstr(
                1,
                1,
                f"{prompt}{query}"[: w - 3]
            )
            prev_query = query

        # --- Draw object list ---
        for i, (obj, is_match) in enumerate(visible):
            y = list_top + i
            idx = scroll + i

            text = str(obj)[:content_width]
            attrs = 0

            if multi and obj in selected:
                attrs |= curses.color_pair(4)
            elif not is_match:
                attrs |= curses.color_pair(3)

            if idx == selected_idx:
                attrs |= curses.A_REVERSE

            stdscr.addstr(y, content_x, " " * content_width)
            stdscr.addstr(y, content_x, text, attrs)

        # --- Clear unused rows (bounded, border-safe) ---
        for y in range(list_top + len(visible), list_top + max_rows):
            stdscr.addstr(y, content_x, " " * content_width)

        stdscr.noutrefresh()
        curses.doupdate()

        # --- Cursor placement (never on border) ---
        cursor_x = min(len(prompt) + len(query) + 1, w - 3)
        stdscr.move(1, cursor_x)

        key = stdscr.get_wch()

        # --- Controls ---
        if key in ('\x1b', curses.KEY_EXIT):
            return None

        elif key == curses.KEY_UP and selected_idx > 0:
            selected_idx -= 1

        elif key == curses.KEY_DOWN and selected_idx < len(display) - 1:
            selected_idx += 1

        elif key == " " and multi:
            obj, _ = display[selected_idx]
            if obj in selected:
                selected.remove(obj)
            else:
                selected.add(obj)

        elif key == "\n":
            obj, _ = display[selected_idx]
            if multi:
                result = selected.copy()
                result.add(obj)
                return list(result)
            else:
                return [obj]

        elif key in (curses.KEY_BACKSPACE, "\b", "\x7f"):
            query = query[:-1]
            selected_idx = first_match_index()
            scroll = 0

        elif isinstance(key, str) and key.isprintable():
            query += key
            selected_idx = first_match_index()
            scroll = 0


def object_picker(objects, multi=True, prompt="Select: "):
    """
    Launch an interactive object picker.

    Args:
        objects: List of objects
        multi: Allow multiple selection
        prompt: Prompt text

    Returns:
        List of selected objects, or None if cancelled
    """
    if not objects:
        return None
    return curses.wrapper(_object_picker_ui, objects, multi, prompt)


if __name__ == "__main__":
    class Thing:
        def __init__(self, name, value):
            self.name = name
            self.value = value

        def __str__(self):
            return f"{self.name} ({self.value})"

    things = [
        Thing("Alpha among the powers of the earth", 10),
        Thing("Beta when in the course of human events", 20),
        Thing("Gamma necessary for one people", 30),
        Thing("Delta bands that have joined them", 40),
    ]

    picked = object_picker(things, multi=True)
    print(picked)

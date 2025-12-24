import curses

PROMPT = "Select: "


def _object_picker_ui(stdscr, objects, multi):
    """
    Curses UI for object picking with file_picker-like UX.
    """
    def matches(text: str) -> bool:
        return query.lower() in text.lower()

    def first_match_index():
        for i, (_, is_match) in enumerate(display):
            if is_match:
                return i
        return 0

    curses.curs_set(1)
    stdscr.keypad(True)

    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_WHITE, -1)                 # normal
    curses.init_pair(3, 8, -1)                                  # gray (non-match)
    curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLUE)  # selected (file-style)

    stdscr.bkgd(" ", curses.color_pair(1))

    query = ""
    selected_idx = 0
    scroll = 0
    selected = set()

    prev_query = None

    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()

        list_top = 2
        max_rows = h - list_top - 1

        # ---- Build display list ----
        labeled = [(obj, str(obj)) for obj in objects]

        matching = [(o, True) for o, s in labeled if matches(s)]
        non_matching = [(o, False) for o, s in labeled if not matches(s)]

        display = matching + non_matching

        if not display:
            selected_idx = 0
            scroll = 0
        else:
            selected_idx = max(0, min(selected_idx, len(display) - 1))

        # ---- Scroll handling ----
        if selected_idx < scroll:
            scroll = selected_idx
        elif selected_idx >= scroll + max_rows:
            scroll = selected_idx - max_rows + 1

        visible = display[scroll : scroll + max_rows]

        # ---- Prompt ----
        if query != prev_query:
            stdscr.move(0, 0)
            stdscr.clrtoeol()
            stdscr.addstr(0, 0, f"{PROMPT}{query}")
            prev_query = query

        # ---- Draw objects ----
        for i, (obj, is_match) in enumerate(visible):
            idx = scroll + i
            y = list_top + i

            text = str(obj)[: w - 4]

            attrs = 0
            if obj in selected:
                attrs |= curses.color_pair(4)
            elif not is_match:
                attrs |= curses.color_pair(3)

            if idx == selected_idx:
                attrs |= curses.A_REVERSE

            stdscr.move(y, 2)
            stdscr.clrtoeol()
            stdscr.addstr(y, 2, text, attrs)

        # ---- Cursor position ----
        cursor_x = min(len(PROMPT) + len(query), w - 1)
        stdscr.move(0, cursor_x)

        stdscr.noutrefresh()
        curses.doupdate()

        key = stdscr.get_wch()

        # ---- Cancel ----
        if key in ('\x1b', curses.KEY_EXIT):
            return None

        # ---- Navigation ----
        elif key == curses.KEY_UP and selected_idx > 0:
            selected_idx -= 1

        elif key == curses.KEY_DOWN and selected_idx < len(display) - 1:
            selected_idx += 1

        # ---- Toggle selection ----
        elif key == " " and multi and display:
            obj, _ = display[selected_idx]
            if obj in selected:
                selected.remove(obj)
            else:
                selected.add(obj)

        # ---- Enter ----
        elif key == "\n" and display:
            obj, _ = display[selected_idx]
            if multi:
                result = set(selected)
                result.add(obj)   # always include highlighted object
                return list(result)
            else:
                return [obj]

        # ---- Backspace ----
        elif key in (curses.KEY_BACKSPACE, "\b", "\x7f"):
            query = query[:-1]
            selected_idx = first_match_index()
            scroll = 0

        # ---- Typing ----
        elif isinstance(key, str) and key.isprintable():
            query += key
            selected_idx = first_match_index()
            scroll = 0


def object_picker(objects, multi=True):
    """
    Launch an interactive object picker.

    Args:
        objects: list of objects
        multi: allow multiple selection

    Returns:
        list of selected objects or None
    """
    if not objects:
        return None
    return curses.wrapper(_object_picker_ui, objects, multi)


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
        Thing("Gamma necessary for one people to dissolve", 30),
        Thing("Delta bands that have joined them", 40),
    ]

    print("MULTI MODE")
    result = object_picker(things, multi=True)
    for object in result:
        print(str(object))
    
    # print(result)

    # print("\nSINGLE MODE")
    # result = object_picker(things, multi=False)
    # print(result)

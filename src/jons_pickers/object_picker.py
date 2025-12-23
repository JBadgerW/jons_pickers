import curses

PROMPT = "Select: "

def _object_picker_ui(stdscr, objects, multi):
    """Internal curses UI function."""
    curses.curs_set(0)
    stdscr.keypad(True)

    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_WHITE, -1)
    
    stdscr.bkgd(" ", curses.color_pair(1))

    selected = set()
    selected_idx = 0
    scroll = 0

    n = len(objects)

    while True:
        stdscr.erase()

        h, w = stdscr.getmaxyx()
        list_top = 1
        max_rows = h - list_top - 1

        stdscr.addstr(0, 0, PROMPT)

        # Clamp selection
        if selected_idx < 0:
            selected_idx = 0
        elif selected_idx >= n:
            selected_idx = n - 1

        # Adjust scroll window
        if selected_idx < scroll:
            scroll = selected_idx
        elif selected_idx >= scroll + max_rows:
            scroll = selected_idx - max_rows + 1

        visible = objects[scroll : scroll + max_rows]

        # Draw visible objects
        for i, obj in enumerate(visible):
            y = list_top + i
            idx = scroll + i

            text = str(obj)
            line = text[: w - 4]

            attrs = 0
            if idx == selected_idx or (multi and obj in selected):
                attrs |= curses.A_REVERSE

            stdscr.move(y, 2)
            stdscr.clrtoeol()
            stdscr.addstr(y, 2, line, attrs)

        # Clear unused rows
        for y in range(list_top + len(visible), list_top + max_rows):
            stdscr.move(y, 0)
            stdscr.clrtoeol()

        stdscr.noutrefresh()
        curses.doupdate()

        key = stdscr.get_wch()

        # ---- ESC: cancel ----
        if key in ('\x1b', curses.KEY_EXIT):
            return None

        elif key == curses.KEY_UP and selected_idx > 0:
            selected_idx -= 1

        elif key == curses.KEY_DOWN and selected_idx < n - 1:
            selected_idx += 1

        elif key == " " and multi:
            obj = objects[selected_idx]
            if obj in selected:
                selected.remove(obj)
            else:
                selected.add(obj)

        elif key == "\n":
            if multi:
                return list(selected) if selected else [objects[selected_idx]]
            else:
                return [objects[selected_idx]]


def object_picker(objects, multi=True):
    """
    Launch an interactive object picker.
    
    Args:
        objects: List of objects to choose from
        multi: Allow multiple selection with spacebar (default: True)
    
    Returns:
        List of selected objects, or None if cancelled
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
        Thing("Alpha among the powers of the earth that separate and equal ", 10),
        Thing("Beta when in the course of human events it becomes ", 20),
        Thing("Gamma necessary for one people to dissolve the political ", 30),
        Thing("Delta bands that have joined them to another and assume ", 40),
    ]

    # Multi-select mode (default)
    print("MULTI-SELECT MODE")
    picked = object_picker(things, multi=True)
    
    if picked is None:
        print("Cancelled")
    else:
        print("Selected:")
        for obj in picked:
            print(obj)

    print("\n" + "="*50 + "\n")

    # Single-select mode
    print("SINGLE-SELECT MODE")
    picked = object_picker(things, multi=False)
    
    if picked is None:
        print("Cancelled")
    else:
        print("Selected:")
        for obj in picked:
            print(obj)
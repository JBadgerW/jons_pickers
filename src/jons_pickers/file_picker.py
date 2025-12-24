import curses
from pathlib import Path


def _file_picker_ui(stdscr, start_dir, multi, prompt):
    """Internal curses UI function."""
    def first_match_index():
        if query == "..":
            for i, (p, _, is_match) in enumerate(display):
                if p.name == ".." and is_match:
                    return i
        for i, (p, _, is_match) in enumerate(display):
            if is_match and p.name != "..":
                return i
        return 0

    curses.curs_set(1)
    stdscr.keypad(True)

    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_WHITE, -1)
    curses.init_pair(2, curses.COLOR_CYAN, -1)
    curses.init_pair(3, 8, -1)
    curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(5, curses.COLOR_CYAN, curses.COLOR_BLUE)

    stdscr.bkgd(" ", curses.color_pair(1))
    stdscr.clear()
    stdscr.border()

    cwd = Path(start_dir).expanduser() if start_dir else Path.cwd()
    if not cwd.is_dir():
        cwd = Path.cwd()
    cwd = cwd.resolve()

    query = ""
    selected_idx = 0
    selected = set()
    scroll = 0
    prev_query = None
    prev_selected_count = None

    while True:
        # --- Prepare display ---
        try:
            entries = list(cwd.iterdir())
        except PermissionError:
            entries = []

        dirs = sorted(p for p in entries if p.is_dir())
        files = sorted(p for p in entries if p.is_file())

        def matches(name: str) -> bool:
            return query.lower() in name.lower()

        display = []
        if cwd.parent != cwd:
            display.append((Path(".."), True, matches("..") if query else True))

        display += [(p, True, True) for p in dirs if matches(p.name)]
        display += [(p, False, True) for p in files if matches(p.name)]
        display += [(p, True, False) for p in dirs if not matches(p.name)]
        display += [(p, False, False) for p in files if not matches(p.name)]

        if selected_idx >= len(display):
            selected_idx = max(0, len(display) - 1)

        h, w = stdscr.getmaxyx()
        list_top = 3
        max_rows = h - list_top - 2

        if multi:
            split_col = int(w * 0.65)
            browser_x = 3
            browser_width = split_col - browser_x - 1
            selected_x = split_col + 2
            selected_width = w - selected_x - 1
        else:
            browser_x = 3
            browser_width = w - browser_x - 1
            selected_width = 0

        if selected_idx < scroll:
            scroll = selected_idx
        elif selected_idx >= scroll + max_rows:
            scroll = selected_idx - max_rows + 1

        visible = display[scroll: scroll + max_rows]

        stdscr.border()

        if multi:
            for y in range(1, h - 1):
                stdscr.addch(y, split_col, curses.ACS_VLINE)

        # --- Prompt ---
        if query != prev_query:
            stdscr.addstr(1, 1, " " * (w - 3))
            prompt_line = f"{prompt}{cwd}/{query}"
            stdscr.addstr(1, 1, prompt_line[: w - 3])
            prev_query = query

        # --- Browser pane ---
        for i, (path, is_dir, is_match) in enumerate(visible):
            y = list_top + i
            idx = scroll + i

            name = path.name + ("/" if is_dir else "")
            line = name[:browser_width]

            full_path = (cwd / path).resolve()
            is_selected = multi and full_path in selected
            attrs = 0

            if is_selected:
                attrs |= curses.color_pair(5 if is_dir else 4)
            elif is_dir and is_match:
                attrs |= curses.color_pair(2)
            elif not is_match:
                attrs |= curses.color_pair(3)

            if idx == selected_idx:
                attrs |= curses.A_REVERSE

            stdscr.addstr(y, browser_x, " " * browser_width)
            stdscr.addstr(y, browser_x, line, attrs)

        for y in range(list_top + len(visible), list_top + max_rows):
            stdscr.addstr(y, browser_x, " " * browser_width)

        # --- Selected pane ---
        if multi:
            if len(selected) != prev_selected_count:
                stdscr.addstr(1, selected_x, " " * selected_width)
                stdscr.addstr(1, selected_x, f"Selected ({len(selected)})"[:selected_width])
                stdscr.addstr(2, selected_x, " " * selected_width)
                stdscr.addstr(2, selected_x, "Ctrl+C: clear"[:selected_width], curses.color_pair(3))
                prev_selected_count = len(selected)

            selected_list = sorted(Path(p).name for p in selected)
            for i, name in enumerate(selected_list[:max_rows]):
                y = list_top + i
                stdscr.addstr(y, selected_x, " " * selected_width)
                stdscr.addstr(y, selected_x, name[:selected_width])

            for y in range(list_top + len(selected_list[:max_rows]), list_top + max_rows):
                stdscr.addstr(y, selected_x, " " * selected_width)

        stdscr.noutrefresh()
        curses.doupdate()

        cursor_x = min(len(prompt) + len(str(cwd)) + len(query) + 2, w - 3)
        stdscr.move(1, cursor_x)

        key = stdscr.get_wch()

        if key in ('\x1b', curses.KEY_EXIT):
            return None

        elif key == curses.KEY_UP and selected_idx > 0:
            selected_idx -= 1
        elif key == curses.KEY_DOWN and selected_idx < len(display) - 1:
            selected_idx += 1

        elif key == '\x03' and multi:
            selected.clear()
            prev_selected_count = None

        elif key == '\t':
            names = [p.name for p, _, is_match in display if is_match and p.name != ".."]
            prefix = [n for n in names if n.lower().startswith(query.lower())]
            if prefix:
                query = min(prefix, key=len)
                selected_idx = first_match_index()
                scroll = 0

        elif key == "\n":
            path, is_dir, _ = display[selected_idx]
            target = (cwd / path).resolve()
            if is_dir:
                cwd = target
                query = ""
                selected_idx = scroll = 0
            else:
                result = selected | {target} if multi else {target}
                return sorted(str(p) for p in result)

        elif key == " " and multi:
            path, is_dir, _ = display[selected_idx]
            if not is_dir:
                target = (cwd / path).resolve()
                selected.symmetric_difference_update({target})
                prev_selected_count = None

        elif key in (curses.KEY_BACKSPACE, "\b", "\x7f"):
            query = query[:-1]
            selected_idx = first_match_index()
            scroll = 0

        elif isinstance(key, str) and key.isprintable():
            query += key
            selected_idx = first_match_index()
            scroll = 0


def file_picker(start_dir=None, multi=False, prompt="File: "):
    return curses.wrapper(_file_picker_ui, start_dir, multi, prompt)


if __name__ == "__main__":

    # Single file picker
    print("SINGLE FILE PICKER")
    result = file_picker("~", multi=False)
    print(result)

    # Multi file picker
    print("\nMULTI FILE PICKER")
    result = file_picker("~", multi=True)
    print(result)
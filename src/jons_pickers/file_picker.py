import curses
from time import sleep
from pathlib import Path

PROMPT = "File: "

def _file_picker_ui(stdscr, start_dir, multi):
    """Internal curses UI function."""
    def first_match_index():
        for i, (p, _) in enumerate(display):
            if p.name != "..":
                return i
        return 0

    curses.curs_set(1)
    stdscr.keypad(True)

    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_WHITE, -1)

    stdscr.bkgd(" ", curses.color_pair(1))
    stdscr.clear()

    # --- Initialize cwd ---
    cwd = Path(start_dir).expanduser() if start_dir else Path.cwd()
    if not cwd.is_dir():
        cwd = Path.cwd()
    cwd = cwd.resolve()

    query = ""
    selected_idx = 0
    selected = set()   # only used in multi mode
    scroll = 0
    prev_selected_idx = None
    prev_query = None

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
            display.append((Path(".."), True))
        display += (
            [(p, True) for p in dirs if matches(p.name)] +
            [(p, False) for p in files if matches(p.name)]
        )

        if selected_idx >= len(display):
            selected_idx = max(0, len(display) - 1)

        # --- Layout ---
        h, w = stdscr.getmaxyx()
        list_top = 2
        max_rows = h - list_top - 1

        if selected_idx < scroll:
            scroll = selected_idx
        elif selected_idx >= scroll + max_rows:
            scroll = selected_idx - max_rows + 1

        visible = display[scroll : scroll + max_rows]

        # --- Draw prompt only if query changed ---
        if query != prev_query or prev_selected_idx is None:
            stdscr.move(0, 0)
            stdscr.clrtoeol()
            stdscr.addstr(0, 0, f"{PROMPT}{cwd}/{query}")
            prev_query = query

        # --- Draw file list ---
        for i, (path, is_dir) in enumerate(visible):
            y = list_top + i
            idx = scroll + i

            name = path.name + ("/" if is_dir and path.name != ".." else "")
            line = name[: w - 4]

            full_path = (cwd / path).resolve()
            attrs = 0

            if idx == selected_idx or (multi and full_path in selected):
                attrs |= curses.A_REVERSE

            stdscr.move(y, 2)
            stdscr.clrtoeol()
            stdscr.addstr(y, 2, line, attrs)

        # Clear unused rows
        for y in range(list_top + len(visible), list_top + max_rows):
            stdscr.move(y, 0)
            stdscr.clrtoeol()

        stdscr.noutrefresh()
        curses.doupdate()  # update all at once

        # Keep cursor at input (clamped to terminal width)
        cursor_x = len(PROMPT) + len(str(cwd)) + len(query) + 1
        stdscr.move(0, min(cursor_x, w - 1))

        key = stdscr.get_wch()

        # ---- ESC: cancel ----
        if key in ('\x1b', curses.KEY_EXIT):
            return None

        elif key == curses.KEY_UP and selected_idx > 0:
            selected_idx -= 1
        elif key == curses.KEY_DOWN and selected_idx < len(display) - 1:
            selected_idx += 1

        elif key == '\t':  # TAB autocomplete (bash-style)
            names = [p.name for p, _ in display if p.name != ".."]
            
            # Filter to items that start with query (prefix matches)
            prefix_matches = [n for n in names if n.lower().startswith(query.lower())]
            
            if len(prefix_matches) == 1:
                # Unique prefix match - complete the full name
                query = prefix_matches[0]
                selected_idx = first_match_index()
                scroll = 0
            elif len(prefix_matches) > 1:
                # Multiple prefix matches - complete to longest common prefix
                common = prefix_matches[0]
                for n in prefix_matches[1:]:
                    while not n.startswith(common):
                        common = common[:-1]
                        if not common:
                            break
                if common and common != query:
                    query = common
                    selected_idx = first_match_index()
                    scroll = 0

        elif key == "\n":  # ENTER
            if not display:
                continue

            path, is_dir = display[selected_idx]
            target = (cwd / path).resolve()

            if is_dir:
                cwd = target
                query = ""
                selected_idx = 0
                scroll = 0
                selected.clear()
            else:
                if multi:
                    return sorted(str(p) for p in selected) if selected else [str(target)]
                else:
                    return [str(target)]

        elif key == " " and multi:  # toggle selection
            path, is_dir = display[selected_idx]
            if not is_dir:
                target = (cwd / path).resolve()
                if target in selected:
                    selected.remove(target)
                else:
                    selected.add(target)

        elif key in (curses.KEY_BACKSPACE, "\b", "\x7f"):
            query = query[:-1]
            selected_idx = first_match_index()
            scroll = 0

        elif isinstance(key, str) and key.isprintable():
            query += key
            selected_idx = first_match_index()
            scroll = 0


def file_picker(start_dir=None, multi=False):
    """
    Launch an interactive file picker.
    
    Args:
        start_dir: Starting directory (default: current directory)
        multi: Allow multiple file selection with spacebar (default: False)
    
    Returns:
        List of selected file paths as strings, or None if cancelled
    """
    return curses.wrapper(_file_picker_ui, start_dir, multi)


if __name__ == "__main__":

    # Single file picker
    print("SINGLE FILE PICKER")
    result = file_picker("/home/jon/GitHub", multi=False)
    print(result)
    sleep(2)

    # Multi file picker
    print("\nMULTI FILE PICKER")
    result = file_picker("/home/jon/GitHub", multi=True)
    print(result)
    sleep(2)
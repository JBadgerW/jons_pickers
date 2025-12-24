import curses
from time import sleep
from pathlib import Path


def _file_picker_ui(stdscr, start_dir, multi, prompt):
    """Internal curses UI function."""
    def first_match_index():
        for i, (p, _, is_match) in enumerate(display):
            if is_match:
                return i
        return 0

    curses.curs_set(1)
    stdscr.keypad(True)

    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_WHITE, -1)
    curses.init_pair(2, curses.COLOR_CYAN, -1)  # Cyan for directories
    curses.init_pair(3, 8, -1)  # Gray for non-matches (color 8 is typically bright black/gray)

    stdscr.bkgd(" ", curses.color_pair(1))
    stdscr.clear()
    
    # Draw border
    h, w = stdscr.getmaxyx()
    stdscr.border()

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

        # Build display with match status
        display = []
        if cwd.parent != cwd:
            display.append((Path(".."), True, True))  # (path, is_dir, is_match)
        
        # Separate matches and non-matches
        matching_dirs = [(p, True, True) for p in dirs if matches(p.name)]
        matching_files = [(p, False, True) for p in files if matches(p.name)]
        non_matching_dirs = [(p, True, False) for p in dirs if not matches(p.name)]
        non_matching_files = [(p, False, False) for p in files if not matches(p.name)]
        
        # Matches first, then non-matches
        display += matching_dirs + matching_files + non_matching_dirs + non_matching_files

        if selected_idx >= len(display):
            selected_idx = max(0, len(display) - 1)

        # --- Layout ---
        h, w = stdscr.getmaxyx()
        list_top = 3  # Account for border
        max_rows = h - list_top - 2  # Account for top and bottom border

        if selected_idx < scroll:
            scroll = selected_idx
        elif selected_idx >= scroll + max_rows:
            scroll = selected_idx - max_rows + 1

        visible = display[scroll : scroll + max_rows]

        # Redraw border
        stdscr.border()

        # --- Draw prompt only if query changed ---
        if query != prev_query or prev_selected_idx is None:
            stdscr.move(1, 1)
            stdscr.clrtoeol()
            prompt_line = f"{prompt}{cwd}/{query}"
            stdscr.addstr(1, 1, prompt_line[:w-2])  # Truncate to fit inside border
            prev_query = query

        # --- Draw file list ---
        for i, (path, is_dir, is_match) in enumerate(visible):
            y = list_top + i
            idx = scroll + i

            name = path.name + ("/" if is_dir else "")
            line = name[: w - 4]

            full_path = (cwd / path).resolve()
            attrs = 0

            # Choose color based on match status and directory
            if is_dir and is_match:
                attrs |= curses.color_pair(2)  # Cyan for matching directories
            elif is_dir and not is_match:
                attrs |= curses.color_pair(3)  # Gray for non-matching directories
            elif not is_match:
                attrs |= curses.color_pair(3)  # Gray for non-matching files
            # Otherwise use default white (color_pair 1) for matching files
            
            if idx == selected_idx or (multi and full_path in selected):
                attrs |= curses.A_REVERSE

            stdscr.move(y, 3)  # Indent for border
            # Clear line but preserve border
            stdscr.addstr(y, 3, " " * (w - 4))
            stdscr.addstr(y, 3, line, attrs)

        # Clear unused rows
        for y in range(list_top + len(visible), list_top + max_rows):
            stdscr.move(y, 1)
            stdscr.addstr(y, 1, " " * (w - 2))

        stdscr.noutrefresh()
        curses.doupdate()  # update all at once

        # Keep cursor at input (clamped to terminal width)
        cursor_x = 1 + len(prompt) + len(str(cwd)) + len(query) + 1
        stdscr.move(1, min(cursor_x, w - 2))

        key = stdscr.get_wch()

        # ---- ESC: cancel ----
        if key in ('\x1b', curses.KEY_EXIT):
            return None

        elif key == curses.KEY_UP and selected_idx > 0:
            selected_idx -= 1
        elif key == curses.KEY_DOWN and selected_idx < len(display) - 1:
            selected_idx += 1

        elif key == '\t':  # TAB autocomplete (bash-style)
            names = [p.name for p, _, is_match in display if p.name != ".." and is_match]
            
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

            path, is_dir, is_match = display[selected_idx]
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
            path, is_dir, is_match = display[selected_idx]
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


def file_picker(start_dir=None, multi=False, prompt="File: "):
    """
    Launch an interactive file picker.
    
    Args:
        start_dir: Starting directory (default: current directory)
        multi: Allow multiple file selection with spacebar (default: False)
    
    Returns:
        List of selected file paths as strings, or None if cancelled
    """
    return curses.wrapper(_file_picker_ui, start_dir, multi, prompt)


if __name__ == "__main__":

    # Single file picker
    print("SINGLE FILE PICKER")
    result = file_picker("~", multi=False)
    print(result)
    sleep(2)

    # Multi file picker
    print("\nMULTI FILE PICKER")
    result = file_picker("~", multi=True)
    print(result)
    sleep(2)
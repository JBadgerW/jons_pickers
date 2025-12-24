import curses
from pathlib import Path


def _file_picker_ui(stdscr, start_dir, multi, prompt):
    """Internal curses UI function."""
    def first_match_index():
        # Special case: if query is exactly "..", prioritize the parent directory
        if query == "..":
            for i, (p, _, is_match) in enumerate(display):
                if p.name == ".." and is_match:
                    return i
        # Otherwise, find first match that isn't ".."
        for i, (p, _, is_match) in enumerate(display):
            if is_match and p.name != "..":
                return i
        return 0

    curses.curs_set(1)
    stdscr.keypad(True)

    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_WHITE, -1)
    curses.init_pair(2, curses.COLOR_CYAN, -1)  # Cyan for directories
    curses.init_pair(3, 8, -1)  # Gray for non-matches (color 8 is typically bright black/gray)
    curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLUE)  # White on blue for selected files
    curses.init_pair(5, curses.COLOR_CYAN, curses.COLOR_BLUE)  # Cyan on blue for selected directories

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
    selected = set()   # persistent set of selected file paths
    scroll = 0
    prev_selected_idx = None
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

        # Build display with match status
        display = []
        parent_entry = None
        if cwd.parent != cwd:
            parent_matches = ".." if query else True  # Only match if query is ".."
            if query:
                parent_matches = matches("..")
            else:
                parent_matches = True
            parent_entry = (Path(".."), True, parent_matches)
        
        # Separate matches and non-matches
        matching_dirs = [(p, True, True) for p in dirs if matches(p.name)]
        matching_files = [(p, False, True) for p in files if matches(p.name)]
        non_matching_dirs = [(p, True, False) for p in dirs if not matches(p.name)]
        non_matching_files = [(p, False, False) for p in files if not matches(p.name)]
        
        # Add parent at the beginning
        if parent_entry:
            display.append(parent_entry)
        
        # Matches first, then non-matches
        display += matching_dirs + matching_files + non_matching_dirs + non_matching_files

        if selected_idx >= len(display):
            selected_idx = max(0, len(display) - 1)

        # --- Layout ---
        h, w = stdscr.getmaxyx()
        
        # Calculate split: 65% for file browser, 35% for selected list in multi mode
        if multi:
            split_col = int(w * 0.65)
            browser_width = split_col - 1
            selected_width = w - split_col - 1
        else:
            browser_width = w - 2
            selected_width = 0
        
        list_top = 3  # Account for border
        max_rows = h - list_top - 2  # Account for top and bottom border

        if selected_idx < scroll:
            scroll = selected_idx
        elif selected_idx >= scroll + max_rows:
            scroll = selected_idx - max_rows + 1

        visible = display[scroll : scroll + max_rows]

        # Redraw border
        stdscr.border()
        
        # Draw vertical separator in multi mode
        if multi:
            for y in range(1, h - 1):
                stdscr.addch(y, split_col, curses.ACS_VLINE)

        # --- Draw prompt only if query changed ---
        if query != prev_query or prev_selected_idx is None:
            stdscr.move(1, 1)
            stdscr.clrtoeol()
            prompt_line = f"{prompt}{cwd}/{query}"
            stdscr.addstr(1, 1, prompt_line[:browser_width-1])  # Truncate to fit
            prev_query = query

        # --- Draw file list ---
        for i, (path, is_dir, is_match) in enumerate(visible):
            y = list_top + i
            idx = scroll + i

            name = path.name + ("/" if is_dir else "")
            line = name[: browser_width - 3]

            full_path = (cwd / path).resolve()
            is_selected = multi and full_path in selected
            is_highlighted = idx == selected_idx
            attrs = 0

            # Choose color based on selection and match status
            if is_selected:
                # Selected files get blue background
                if is_dir:
                    attrs |= curses.color_pair(5)  # Cyan on blue for selected directories
                else:
                    attrs |= curses.color_pair(4)  # White on blue for selected files
            elif is_dir and is_match:
                attrs |= curses.color_pair(2)  # Cyan for matching directories
            elif is_dir and not is_match:
                attrs |= curses.color_pair(3)  # Gray for non-matching directories
            elif not is_match:
                attrs |= curses.color_pair(3)  # Gray for non-matching files
            # Otherwise use default white (color_pair 1) for matching files
            
            # Add reverse video for highlighted item (works on top of any background)
            if is_highlighted:
                attrs |= curses.A_REVERSE

            stdscr.move(y, 3)  # Indent for border
            # Clear line but preserve border/separator
            stdscr.addstr(y, 3, " " * (browser_width - 3))
            stdscr.addstr(y, 3, line, attrs)

        # Clear unused rows in browser pane
        for y in range(list_top + len(visible), list_top + max_rows):
            stdscr.move(y, 1)
            stdscr.addstr(y, 1, " " * (browser_width - 1))

        # --- Draw selected files pane (multi mode only) ---
        if multi:
            # Draw header only if selection count changed
            if len(selected) != prev_selected_count or prev_selected_count is None:
                header = f"Selected ({len(selected)})"
                stdscr.move(1, split_col + 2)
                stdscr.clrtoeol()
                stdscr.addstr(1, split_col + 2, header[:selected_width - 3])
                
                # Add help text
                help_text = "Ctrl+C: clear"
                stdscr.move(2, split_col + 2)
                stdscr.clrtoeol()
                stdscr.addstr(2, split_col + 2, help_text[:selected_width - 3], curses.color_pair(3))
                
                prev_selected_count = len(selected)
            
            # Draw selected files list
            selected_list = sorted([Path(p).name for p in selected])
            for i, filename in enumerate(selected_list[:max_rows]):
                y = list_top + i
                truncated = filename[:selected_width - 3]
                stdscr.move(y, split_col + 2)
                stdscr.clrtoeol()
                stdscr.addstr(y, split_col + 2, truncated)
            
            # Clear remaining rows in selected pane
            for y in range(list_top + len(selected_list[:max_rows]), list_top + max_rows):
                stdscr.move(y, split_col + 1)
                stdscr.clrtoeol()

        stdscr.noutrefresh()
        curses.doupdate()  # update all at once

        # Keep cursor at input (clamped to terminal width)
        cursor_x = 1 + len(prompt) + len(str(cwd)) + len(query) + 1
        stdscr.move(1, min(cursor_x, browser_width - 1))

        key = stdscr.get_wch()

        # ---- ESC: cancel ----
        if key in ('\x1b', curses.KEY_EXIT):
            return None

        elif key == curses.KEY_UP and selected_idx > 0:
            selected_idx -= 1
        elif key == curses.KEY_DOWN and selected_idx < len(display) - 1:
            selected_idx += 1

        elif key == '\x03' and multi:  # Ctrl+C: clear selections
            selected.clear()
            prev_selected_count = None  # Force redraw of header

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
                # Don't clear selected files when navigating directories
            else:
                if multi:
                    # Always include the currently highlighted file
                    result_set = selected.copy()
                    result_set.add(target)
                    return sorted(str(p) for p in result_set)
                else:
                    return [str(target)]

        elif key == " " and multi:  # toggle selection
            path, is_dir = display[selected_idx][:2]
            if not is_dir:
                target = (cwd / path).resolve()
                if target in selected:
                    selected.remove(target)
                else:
                    selected.add(target)
                prev_selected_count = None  # Force redraw

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
        prompt: Prompt text to display (default: "File: ")
    
    Controls:
        Arrow keys: Navigate
        Enter: Select file(s) or enter directory
        Space: Toggle file selection (multi mode)
        Tab: Autocomplete
        Ctrl+C: Clear all selections (multi mode)
        Esc: Cancel
    
    Returns:
        List of selected file paths as strings, or None if cancelled
    """
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
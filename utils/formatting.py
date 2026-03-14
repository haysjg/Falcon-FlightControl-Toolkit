"""Formatting utilities for terminal output with colors and styles."""

from colorama import Fore, Back, Style, init
from typing import List, Dict, Any
import sys
import re

# Initialize colorama for Windows compatibility
init(autoreset=True)


class Colors:
    """Color constants for consistent styling."""
    SUCCESS = Fore.GREEN
    ERROR = Fore.RED
    WARNING = Fore.YELLOW
    INFO = Fore.CYAN
    HIGHLIGHT = Fore.MAGENTA
    DIM = Style.DIM
    BRIGHT = Style.BRIGHT
    RESET = Style.RESET_ALL


def strip_ansi_codes(text: str) -> str:
    """
    Remove ANSI color codes from a string to get visible length.

    Args:
        text: String that may contain ANSI codes

    Returns:
        String with ANSI codes removed
    """
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


def get_visible_length(text: str) -> int:
    """
    Get the visible length of a string, excluding ANSI codes.

    Args:
        text: String that may contain ANSI codes

    Returns:
        Visible length of the string
    """
    return len(strip_ansi_codes(text))


def print_header(text: str, char: str = "=", width: int = 80, color: str = Colors.INFO):
    """
    Print a styled header.

    Args:
        text: Header text
        char: Character for the border
        width: Total width
        color: Color to use
    """
    print()
    print(color + char * width + Colors.RESET)
    print(color + Style.BRIGHT + text.center(width) + Colors.RESET)
    print(color + char * width + Colors.RESET)
    print()


def print_section(text: str, char: str = "-", width: int = 80, color: str = Colors.INFO):
    """
    Print a styled section divider.

    Args:
        text: Section text
        char: Character for the border
        width: Total width
        color: Color to use
    """
    print()
    print(color + char * width + Colors.RESET)
    print(color + Style.BRIGHT + text + Colors.RESET)
    print(color + char * width + Colors.RESET)


def print_success(message: str, prefix: str = "✓"):
    """Print a success message in green."""
    print(f"{Colors.SUCCESS}{prefix} {message}{Colors.RESET}")


def print_error(message: str, prefix: str = "✗"):
    """Print an error message in red."""
    print(f"{Colors.ERROR}{prefix} {message}{Colors.RESET}")


def print_warning(message: str, prefix: str = "⚠"):
    """Print a warning message in yellow."""
    print(f"{Colors.WARNING}{prefix} {message}{Colors.RESET}")


def print_info(message: str, prefix: str = "ℹ"):
    """Print an info message in cyan."""
    print(f"{Colors.INFO}{prefix} {message}{Colors.RESET}")


def print_highlight(message: str, prefix: str = "→"):
    """Print a highlighted message in magenta."""
    print(f"{Colors.HIGHLIGHT}{prefix} {message}{Colors.RESET}")


def print_progress(current: int, total: int, prefix: str = "", suffix: str = ""):
    """
    Print a progress indicator.

    Args:
        current: Current progress
        total: Total items
        prefix: Text before progress bar
        suffix: Text after progress bar
    """
    percentage = int((current / total) * 100) if total > 0 else 0
    bar_length = 30
    filled = int((bar_length * current) / total) if total > 0 else 0
    bar = "█" * filled + "░" * (bar_length - filled)

    print(f"\r{prefix} [{Colors.INFO}{bar}{Colors.RESET}] {percentage}% {suffix}", end="", flush=True)

    if current >= total:
        print()  # New line when complete


def print_table(headers: List[str], rows: List[List[str]], col_widths: List[int] = None):
    """
    Print a formatted table.

    Args:
        headers: List of header strings
        rows: List of row data (each row is a list)
        col_widths: Optional list of column widths
    """
    if not rows:
        print_warning("No data to display")
        return

    # Auto-calculate column widths if not provided
    if col_widths is None:
        col_widths = []
        for i in range(len(headers)):
            max_width = get_visible_length(headers[i])
            for row in rows:
                if i < len(row):
                    max_width = max(max_width, get_visible_length(str(row[i])))
            col_widths.append(max_width + 2)

    # Helper function to pad text to visible width
    def pad_to_width(text: str, width: int) -> str:
        visible_len = get_visible_length(text)
        padding_needed = width - visible_len
        return text + (" " * padding_needed)

    # Print header
    header_parts = [f" {pad_to_width(h, w)} " for h, w in zip(headers, col_widths)]
    header_line = "│".join(header_parts)
    separator = "─" * (sum(col_widths) + len(headers) * 3 - 1)

    print(f"{Colors.INFO}{separator}{Colors.RESET}")
    print(f"{Colors.INFO}{Style.BRIGHT}{header_line}{Colors.RESET}")
    print(f"{Colors.INFO}{separator}{Colors.RESET}")

    # Print rows
    for row in rows:
        padded_row = [str(cell) if i < len(row) else "" for i, cell in enumerate(row)]
        row_parts = [f" {pad_to_width(cell, w)} " for cell, w in zip(padded_row, col_widths)]
        row_line = "│".join(row_parts)
        print(row_line)

    print(f"{Colors.INFO}{separator}{Colors.RESET}")


def print_summary_box(title: str, items: Dict[str, Any], width: int = 60):
    """
    Print a styled summary box.

    Args:
        title: Box title
        items: Dictionary of label: value pairs
        width: Box width
    """
    print()
    print(f"{Colors.INFO}╔{'═' * (width - 2)}╗{Colors.RESET}")
    print(f"{Colors.INFO}║{Style.BRIGHT}{title.center(width - 2)}{Colors.RESET}{Colors.INFO}║{Colors.RESET}")
    print(f"{Colors.INFO}╠{'═' * (width - 2)}╣{Colors.RESET}")

    for label, value in items.items():
        # Color value based on type/content
        if isinstance(value, bool):
            value_str = f"{Colors.SUCCESS}Yes{Colors.RESET}" if value else f"{Colors.ERROR}No{Colors.RESET}"
        elif isinstance(value, (int, float)) and value == 0:
            value_str = f"{Colors.ERROR}{value}{Colors.RESET}"
        else:
            value_str = str(value)

        label_formatted = f"{Colors.HIGHLIGHT}{label}:{Colors.RESET}"
        print(f"{Colors.INFO}║{Colors.RESET} {label_formatted:<30} {value_str}")

    print(f"{Colors.INFO}╚{'═' * (width - 2)}╝{Colors.RESET}")
    print()


def print_status_indicator(label: str, status: bool, true_text: str = "EXISTS", false_text: str = "MISSING"):
    """
    Print a status indicator with colored status.

    Args:
        label: Label text
        status: Boolean status
        true_text: Text to show when True
        false_text: Text to show when False
    """
    if status:
        print(f"  {label:<50} [{Colors.SUCCESS}{true_text}{Colors.RESET}]")
    else:
        print(f"  {label:<50} [{Colors.ERROR}{false_text}{Colors.RESET}]")


def print_coverage_bar(label: str, current: int, total: int, width: int = 40):
    """
    Print a coverage bar showing completion percentage.

    Args:
        label: Description label
        current: Current count
        total: Total count
        width: Bar width in characters
    """
    if total == 0:
        percentage = 0
    else:
        percentage = (current / total) * 100

    filled = int((width * current) / total) if total > 0 else 0
    bar = "█" * filled + "░" * (width - filled)

    # Color based on percentage
    if percentage >= 75:
        color = Colors.SUCCESS
    elif percentage >= 50:
        color = Colors.WARNING
    else:
        color = Colors.ERROR

    print(f"{label:<30} {color}[{bar}]{Colors.RESET} {current}/{total} ({percentage:.0f}%)")


def print_role_item(number: int, name: str, description: str, role_id: str, indent: int = 2):
    """
    Print a formatted role item.

    Args:
        number: Item number
        name: Role name
        description: Role description
        role_id: Role ID
        indent: Indentation spaces
    """
    spaces = " " * indent
    print(f"\n{spaces}{Colors.HIGHLIGHT}[{number}]{Colors.RESET} {Colors.BRIGHT}{name}{Colors.RESET}")
    if description:
        print(f"{spaces}    {Colors.DIM}Description: {description}{Colors.RESET}")
    print(f"{spaces}    {Colors.DIM}ID: {role_id}{Colors.RESET}")


def print_child_item(number: int, name: str, cid: str, indent: int = 2):
    """
    Print a formatted child CID item.

    Args:
        number: Item number
        name: Child name
        cid: Child CID
        indent: Indentation spaces
    """
    spaces = " " * indent
    print(f"\n{spaces}{Colors.HIGHLIGHT}[{number}]{Colors.RESET} {Colors.BRIGHT}{name}{Colors.RESET}")
    print(f"{spaces}    {Colors.DIM}CID: {cid}{Colors.RESET}")


def create_summary_table(role_coverage: Dict[str, Any], children: List[Dict[str, Any]]) -> None:
    """
    Create and print a visual summary table of role coverage.

    Args:
        role_coverage: Coverage data dictionary
        children: List of child CIDs
    """
    print_header("COVERAGE SUMMARY", width=100, color=Colors.SUCCESS)

    # Create matrix view
    child_names = [child.get('name', 'Unknown')[:20] for child in children]

    # Header row
    headers = ["Role Name"] + child_names + ["Coverage"]

    rows = []
    for role_name, data in role_coverage.items():
        row = [role_name[:30]]

        children_status = data.get('children_status', {})
        exists_count = 0

        for child in children:
            child_cid = child.get('child_cid')
            status = children_status.get(child_cid, {})

            if status.get('exists'):
                row.append(f"{Colors.SUCCESS}✓{Colors.RESET}")
                exists_count += 1
            else:
                row.append(f"{Colors.ERROR}✗{Colors.RESET}")

        # Coverage percentage
        coverage_pct = (exists_count / len(children) * 100) if children else 0
        if coverage_pct == 100:
            coverage_str = f"{Colors.SUCCESS}{coverage_pct:.0f}%{Colors.RESET}"
        elif coverage_pct > 0:
            coverage_str = f"{Colors.WARNING}{coverage_pct:.0f}%{Colors.RESET}"
        else:
            coverage_str = f"{Colors.ERROR}{coverage_pct:.0f}%{Colors.RESET}"

        row.append(coverage_str)
        rows.append(row)

    print_table(headers, rows)


def print_action_items(role_coverage: Dict[str, Any], children: List[Dict[str, Any]]) -> None:
    """
    Print action items - what needs to be done.

    Args:
        role_coverage: Coverage data
        children: List of children
    """
    print_section("ACTION ITEMS", color=Colors.WARNING)

    has_actions = False

    for role_name, data in role_coverage.items():
        children_status = data.get('children_status', {})
        missing_in = []

        for child in children:
            child_cid = child.get('child_cid')
            child_name = child.get('name', 'Unknown')
            status = children_status.get(child_cid, {})

            if not status.get('exists'):
                missing_in.append(child_name)

        if missing_in:
            has_actions = True
            print(f"\n{Colors.WARNING}▶ {Colors.BRIGHT}{role_name}{Colors.RESET}")
            print(f"  {Colors.ERROR}Missing in {len(missing_in)} child(ren):{Colors.RESET}")
            for child_name in missing_in:
                print(f"    • {child_name}")

    if not has_actions:
        print_success("All roles exist in all selected children!", prefix="✓")

    print()


def print_credentials_source(source: str):
    """Print the credentials source with appropriate styling."""
    source_map = {
        "config_file": ("Config File", Colors.INFO),
        "cli_args": ("CLI Arguments", Colors.HIGHLIGHT),
        "env_vars": ("Environment Variables", Colors.SUCCESS)
    }

    label, color = source_map.get(source, (source, Colors.INFO))
    print(f"{Colors.DIM}Credentials source:{Colors.RESET} {color}{label}{Colors.RESET}")
    print()


def print_jg_logo():
    """Print the JG logo in green and yellow."""
    logo_lines = [
        "     ██╗   ██████╗",
        "     ██║  ██╔════╝",
        " ██╗ ██║  ██║  ███╗",
        " ╚████╔╝  ╚██████╔╝",
        "  ╚═══╝    ╚═════╝"
    ]

    print()
    for line in logo_lines:
        j_part = line[:11]
        g_part = line[11:]
        print(Fore.GREEN + j_part + Fore.YELLOW + g_part + Style.RESET_ALL)
    print()

#!/usr/bin/env python3
"""
Display JG logo with colors
"""
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False
    print("Note: Install colorama for colors (pip install colorama)")

logo = """
       ████╗    ██████╗
       ████║   ██╔════╝
       ████║   ██║  ███╗
  ██╗  ████║   ██║   ██║
  ╚███████╔╝   ╚██████╔╝
   ╚══════╝     ╚═════╝
"""

if HAS_COLOR:
    print("\n=== Option 1: Cyan + Magenta ===")
    lines = logo.strip().split('\n')
    for line in lines:
        j_part = line[:19]
        g_part = line[19:]
        print(Fore.CYAN + j_part + Fore.MAGENTA + g_part)

    print("\n=== Option 2: Green + Yellow ===")
    for line in lines:
        j_part = line[:19]
        g_part = line[19:]
        print(Fore.GREEN + j_part + Fore.YELLOW + g_part)

    print("\n=== Option 3: Blue + Cyan ===")
    for line in lines:
        j_part = line[:19]
        g_part = line[19:]
        print(Fore.BLUE + j_part + Fore.CYAN + g_part)

    print("\n=== Option 4: Red + Yellow ===")
    for line in lines:
        j_part = line[:19]
        g_part = line[19:]
        print(Fore.RED + j_part + Fore.YELLOW + g_part)

    print("\n=== Option 5: Magenta + Blue ===")
    for line in lines:
        j_part = line[:19]
        g_part = line[19:]
        print(Fore.MAGENTA + j_part + Fore.BLUE + g_part)

    print(Style.RESET_ALL)
else:
    print(logo)

#!/usr/bin/env python3
"""
JG Logo - Green + Yellow
"""
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False

logo = """
       ████╗    ██████╗
       ████║   ██╔════╝
       ████║   ██║  ███╗
  ██╗  ████║   ██║   ██║
  ╚███████╔╝   ╚██████╔╝
   ╚══════╝     ╚═════╝
"""

if HAS_COLOR:
    lines = logo.strip().split('\n')
    for line in lines:
        j_part = line[:19]
        g_part = line[19:]
        print(Fore.GREEN + j_part + Fore.YELLOW + g_part)
    print(Style.RESET_ALL)
else:
    print(logo)

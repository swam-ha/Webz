#!/usr/bin/python3

import logging
from threading import Thread
from time import time
from database import Database
from cli import UserInterface
from modules import REGISTERY
from rich.console import Console
from rich.panel import Panel
from rich.logging import RichHandler
from rich.theme import Theme
from Web.server import app
import time

logging.basicConfig(
    level=logging.DEBUG,
    format="%(message)s",
    handlers=[RichHandler(
        rich_tracebacks=True,
        show_time=False,
        show_path=True
    )]
)

logger = logging.getLogger(__name__)

"""
webz/
│
├── database.py       # Handles connections and raw SQL operations
├── menu.py           # Defines menu
├── cli.py            # Handles user input and menus
├── main.py           # Entry point
│
└── modules/          # Drop new scanner modules here
    ├── __init__.py   # Makes it a package, can auto-load modules
    ├── base.py       # Base class that all modules must inherit from
    ├── port_scan.py
    └── etc...
"""

title = """
▗▖ ▗▖▗▞▀▚▖▗▖   ▄▄▄▄▄ 
▐▌ ▐▌▐▛▀▀▘▐▌    ▄▄▄▀ 
▐▌ ▐▌▝▚▄▄▖▐▛▀▚▖█▄▄▄▄ 
▐▙█▟▌     ▐▙▄▞▘                               
""".strip() # DiamFont

custom_theme = Theme({
"info": "dim cyan",
"warning": "bold yellow",
"error": "bold red",
"success": "bold green",
"header": "bold magenta",
})
HOST = "0.0.0.0"
PORT = 5000
console = Console(theme=custom_theme)

def run_server():
    logger = logging.getLogger("werkzeug")
    logger.setLevel(logging.ERROR)  # Suppress Flask's default logging
    logger.propagate = False  # Prevent propagation to the root logger
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)

def main():
    print(title)

    db = Database() # load database
    print("")

    UserInterface(console, db, tools=REGISTERY)

if __name__ == "__main__":
    flask_thread = Thread(target=run_server)
    flask_thread.daemon = True
    flask_thread.start()

    console.print(Panel(f"Starting Flask server on http://{HOST}:{PORT}", title="Server Status", subtitle="Ready", style="on green"))
    console.print("[info]If you encounters database permission problems, run `chmod 666 webz.db` or whatever the database file is[/info]") 
    try:
        time.sleep(2)
        main()
    except KeyboardInterrupt:
        console.print("\nStopping application...")

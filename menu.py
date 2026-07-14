from typing import Dict, Callable, List, Any, TypedDict
from rich.table import Table

class MenuItem(TypedDict):
    label: str
    action: Callable | None
    args: List[Any]



class Menu:
    def __init__(self, console):
        self.console = console
        # key, {label, action}
        self.items: Dict[str, MenuItem] = {}

        self.add_item("help", "Show help message", self.__help)

    def add_item(self, key: str, label: str, action: Callable | None = None, args: List[Any] | None = None):
        self.items[str(key)] = {
            "label": label,
            "action": action,
            "args": args or []
        }
    
    def display(self):

        table = Table()
        table.add_column("Command", style="green", no_wrap=True)
        table.add_column("Description", style="white")
        for key, value in self.items.items():
            table.add_row(key, value["label"])
        
        self.console.print(table)
        
    def __help(self): # helper function
        self.display()
 
    def run(self, key):
        selected_item = self.items[key]
        action = selected_item["action"]
        args = selected_item["args"]

        if action is not None:
            action(*args)
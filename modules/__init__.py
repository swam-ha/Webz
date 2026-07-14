import pkgutil
import importlib
import inspect
from modules.base import BaseScanner

REGISTERY = {}

def load_module():
    # loop through modules directory
    print(f"DEBUG: Loading modules from {__path__}")
    for _, name, _ in pkgutil.iter_modules(__path__):
        if name == "base": continue # skip base.py

        module = importlib.import_module(f"modules.{name}")

        # Find any classes that inherit BaseScanner and add them to the register
        for obj_name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and issubclass(obj, BaseScanner) and obj is not BaseScanner:
                instance = obj()

                # map registery name to actual object instance
                REGISTERY[instance.name] = instance

load_module()
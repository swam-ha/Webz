import logging
from menu import Menu
from typing import List, Dict
from rich.panel import Panel
from rich.table import Table
import readline # to make arrow keys work in input()

logger = logging.getLogger(__name__)

class UserInterface:
    def __init__(self, console, db, tools):
        self.console = console # rich console
        self.project_menu = self.__build_project_menu("") # for startup menu purely
        self.selected_project = ""
        self.state = "main"
        self.tools = tools # tools in modules folder __init__.py REGISTERY
        self.db = db
        self.__list_projects_in_format()
        print("Enter `help` to see available commands")
        self.__handle_user()

    def __handle_user(self):
        try: # handle keyboard interrupt


            self.project_menu.display() # starup menu

            # main logic
            user = ""
            while user != "q":
                if self.state == "main":
                    prompt = "webz[project]-> "
                elif self.state == "project":
                    prompt = "webz[project]-> "
                elif self.state == "tool":
                    prompt = "webz[tool]-> "

                user = input(prompt).strip()
                if self.state == "main" or self.state == "project":
                    self.__project_selection(user)
                else:
                    self.__tool_selection(user)

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt triggered.")
        finally:
            logger.info("Quitting graceully...")
            self.db.close()
            logger.info("Closed database connection")
        return
    

    # functionalities #

    def __clear(self):
        print("\033[H\033[2J", end="")

    def __back(self):
        if self.state == "project":
            self.state = "main"
        elif self.state == "tool":
            self.state = "project"
        return
    
    def __list(self):
        if self.state == "project" or self.state == "main":
            self.__list_projects_in_format()
        else:
            self.__list_tools_in_fomrat()
    
    def __create_project(self, user: str) -> None:
        args = self.__get_parameter(user)
        if args:
            new_project_name = args["args"][0]
        else: return
        
        if self.db.add_new_project(new_project_name) == 0:
            logger.info(f"Project name: {new_project_name} created.")

    def __delete_project(self, user):
        args = self.__get_parameter(user)
        if args:
            delete_project_id = args["args"][0]
        else: return
        
        if self.db.delete_project_by_id(delete_project_id):
            logger.info(f"Deleted a project - id: {delete_project_id}")
    
    def __select_project(self, user: str) -> None:
        args = self.__get_parameter(user)
        if args:
            selected_project_id = args["args"][0]
        else: return

        project = self.db.get_project(selected_project_id)
        if project:
            self.selected_project = project[0] # 0 is id 1 is name
            self.state = "tool"
   
    
    def __build_project_menu(self, user: str) -> Menu: # to be able to display at startup
        menu = Menu(self.console)
        menu.add_item("clear", "Clear screen", self.__clear)
        menu.add_item("list", "List commands", self.__list)
        menu.add_item("create", "create <name> Create new project", self.__create_project, [user])
        menu.add_item("delete", "delete <id> Delete a project", self.__delete_project, [user])
        menu.add_item("select", "select <id> Select a project", self.__select_project, [user])
      
        return menu

    # interfaces #

    def __show_selected_project(self) -> None:
        print(f"Selected Project: ID={self.selected_project}, Name={self.db.get_project(self.selected_project)[1]}")

    def __project_selection(self, user: str) -> None: # project logic
        menu = self.__build_project_menu(user)

        self.state = "project"
        key = user.split(" ")[0].strip()
        if key in menu.items:
            menu.run(key)

    def __tool_selection(self, user: str) -> None:
        menu = Menu(self.console)
        self.state = "tool"

        menu.add_item("clear", "Clear screen", self.__clear)
        menu.add_item("b", "Back", self.__back)
        menu.add_item("list", "List available modules", self.__list)
        menu.add_item("showp", "Show selected project", self.__show_selected_project)
        key = user.split(" ")[0].strip()
        if key in menu.items:
            menu.run(key)
        else: # run tools

            args = self.__get_parameter(user)
            if args:
                command = args["command"]
                parameters = args["args"]
            else:
                return
            
            if command in self.tools.keys():
                tool = self.tools[command]

                response = tool.run(parameters)
                if not response: return

                name, target, result = response.values()
                body = Panel(str(result), title=name, border_style="green")
                self.console.print(body)

                if target is None:
                    return

                # database functions #

                # register the target
     
                target_id = self.db.save_target(self.selected_project, target)
                if not target_id: return

                # register scan record
                scan_id = self.db.save_scan(target_id, command, parameters)
                if not scan_id: return

                #save result
                self.db.save_result(scan_id, name, result)   
            elif command == "q": pass
            else:
                self.console.print("[error]Command not found! Enter \"help\" to seek help.[/]")
        

    # helper functions #

    # helper function to get extra parameters user supply
    # for example: port_scan 127.0.0.1
    def __get_parameter(self, user_input) -> Dict[str, List] | None: # helper function
        parameters = [p for p in user_input.split(" ") if p]
        
        if not parameters: return None
        return {
                "command": parameters[0],
                "args": parameters[1:]
        }

    
    def __list_projects_in_format(self): # helper function
        projects = self.db.get_projects()
        if projects == []:
            logger.error("[No projects exist yet]")
        else:
            table = Table(title="Available Projects", header_style="bold magenta")
            table.add_column("ID", justify="center", style="cyan", no_wrap=True)
            table.add_column("Project Name", style="white")

            for project_id, project_name in projects:
                table.add_row(str(project_id), project_name)

            self.console.print(table)
    
    def __list_tools_in_fomrat(self):
        tools = self.tools
        if not tools:
                self.console.print("[bold red]No tools detected.[/bold red]")
        else:
            table = Table(title="Available Tools", header_style="bold green")
            
            table.add_column("Command", style="cyan", justify="left")
            table.add_column("Description", style="white")

            # Iterate over keys and values
            for command, tool_obj in tools.items():
                # Assuming your tool objects have a 'description' attribute
                # If they don't, you can just use the name or a placeholder
                description = getattr(tool_obj, 'description', 'No description available')
                table.add_row(command, description)

            self.console.print(table)
            self.console.print("")

# Webz
A Modular web recon framework that keep your scans organized ;)
`First uploaded on Jul 12 2026, around 12:33PM`

# Contents
- What's the point?
- How to install?
- How to use?
- How do I add my own modules/scanners?

## What's the point?
In the world of security testing, most tools are bloated, overwhelming, and loaded with useless jargon that has little to no real impact.

**If you've ever done recon, you know that the more research you do, the more overwhelming and complicated is it to keep track of your project and your ADHD brain starts wandering off to mars**(even with advance note-taking).

They say the best way to get things done is to stay organized. Behold `Webz`. I developed this tool to solve these problems by implementing a plugin architecture, making it easy for anyone to add their own modules or scripts. Plus, it saves your results in an organized SQLite database that you can easily navigate through a clean web interface.

## How to install?
```
git clone https://github.com/swam-ha/Webz.git
cd Webz
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## How to use?
Well... it's pretty intuitive, isn't it? Figure it out yourself.

Enter the help command if you get lost. Each module has its own options and flags. The modules I made use `argparse`, so you can just run `module_name -h` to figure out the usage.

Database permission error? Just run `chmod 666 <database_file>`

## How do I add my own modules/scanners?
Read the base.py file in the modules folder—it's the blueprint.

The framework calls `run`, which is the main function that must be defined in your module. The framework passes the command-line parameters as a list into the `run` function, and it's up to the module developer to handle those arguments however they please.

Always return a ScanResult from your module's entry function, as the framework uses it to print the output and save it directly to the database:
```
class ScanResult(TypedDict):
    name: str
    target: str|None
    result: Any
```
In short, just check out some existing files in the modules folder for reference, and put your intended scripts in it to make them part of the framework.
Happy hacking... ;)

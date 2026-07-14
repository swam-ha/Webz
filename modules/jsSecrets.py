from modules.base import BaseScanner, ScanResult
from typing import List
import re
import requests
from bs4 import BeautifulSoup
import argparse
import json

class JavaScriptSuspiciousStringScanner(BaseScanner):
    @property
    def name(self) -> str:
        return "js_scan"

    @property
    def description(self) -> str:
        return "Finds high-risk strings like API keys, secrets, or eval calls inside linked JS files."

    def run(self, args: List) -> ScanResult | None:
        parser = argparse.ArgumentParser(description=self.description)
        parser.add_argument("url", help="Target website URL")
        parsed_args = parser.parse_args(args)

        url = parsed_args.url

        # High-risk patterns to look for inside Javascript source code
        patterns = {
            "eval_usage": re.compile(r"eval\s*\("),
            "potential_api_key": re.compile(r"(api[-_]?key|secret|password|token)\s*=\s*['\"][a-zA-Z0-9_\-]{16,}['\"]", re.IGNORECASE),
            "internal_ip": re.compile(r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}"),
            "todo_leak": re.compile(r"//\s*(TODO|FIXME)", re.IGNORECASE)
        }

        found_issues = {}

        try:
            # 1. Fetch main page and parse out script tags
            response = requests.get(url, timeout=10, headers={"User-Agent": "Scanner/1.0"})
            soup = BeautifulSoup(response.text, 'html.parser')
            script_tags = soup.find_all('script')

            for script in script_tags:
                src = script.get('src')
                js_content = ""
                source_label = ""

                if src:
                    if isinstance(src, list):
                        src = " ".join(src)
                    else:
                        src = str(src)
                    # Resolve relative URLs
                    js_url = src if src.startswith('http') else f"{url.rstrip('/')}/{src.lstrip('/')}"
                    source_label = js_url
                    try:
                        js_content = requests.get(js_url, timeout=5).text
                    except requests.RequestException:
                        continue
                else:
                    source_label = f"{url} (Inline Script)"
                    js_content = script.string or ""

                lines = js_content.splitlines()
                # 2. Scan the JS content against our regular expressions
                for line_num, line_content in enumerate(lines, start=1):
                    for issue_type, regex in patterns.items():
                        # Use finditer to get the exact location of every match on this line
                        for match in regex.finditer(line_content):
                            matched_text = match.group(0)
                            match_start = match.start()
                            match_end = match.end()

                            # Grab 40 characters before and after the match
                            snippet_start = max(0, match_start - 40)
                            snippet_end = min(len(line_content), match_end + 40)
                            
                            snippet = line_content[snippet_start:snippet_end].strip()
                            
                            # Add ellipses if we clipped the text
                            if snippet_start > 0:
                                snippet = f"... {snippet}"
                            if snippet_end < len(line_content):
                                snippet = f"{snippet} ..."

                            if source_label not in found_issues:
                                found_issues[source_label] = []

                            found_issues[source_label].append({
                                "type": issue_type,
                                "line": line_num,
                                "match": matched_text, # <--- Tells you EXACTLY what triggered the flag
                                "snippet": snippet     # <--- Centered right around the trigger
                            })
                            
            result = {"suspicious_findings": found_issues}
            result = json.dumps(result, indent=4)
            return self.return_value(result, url)

        except Exception as e:
            return self.return_value({"error": str(e)}, url)
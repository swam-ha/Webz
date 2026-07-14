from modules.base import BaseScanner, ScanResult
from typing import List
import requests
import json
import argparse

class WebBugScanner(BaseScanner):
    @property
    def name(self) -> str:
        return "exposed_config"

    @property
    def description(self) -> str:
        return "Checks the target website for common deployment bugs and exposed configurations."

    def run(self, args: List) -> ScanResult:
        parser = argparse.ArgumentParser(description=self.description)
        parser.add_argument("url", help="Target website URL")
        parsed_args = parser.parse_args(args)
        url = parsed_args.url

        # Common files/endpoints left exposed by accident
        common_vulnerabilities = {
            ".env file": ".env",
            "Git repository metadata": ".git/HEAD",
            "WordPress Config backup": "wp-config.php.bak",
            "Exposed backup archive": "backup.zip"
        }

        findings = []
        base_url = url.rstrip('/')

        for bug_name, path in common_vulnerabilities.items():
            target_endpoint = f"{base_url}/{path}"
            try:
                # Use a HEAD or GET request to check existence safely
                res = requests.get(target_endpoint, timeout=5, allow_redirects=False)
                if res.status_code == 200:
                    findings.append({
                        "bug": bug_name,
                        "exposed_url": target_endpoint,
                        "severity": "High"
                    })
            except requests.RequestException:
                continue

        result = {"exposed_bugs": findings or "None found"}
        result = json.dumps(result, indent=4)
        return self.return_value(result, url)
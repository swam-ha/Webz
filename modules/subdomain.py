import argparse
import json

import requests
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Set
from fake_useragent import UserAgent
from modules.base import BaseScanner, ScanResult
import logging
from typing import List

logger = logging.getLogger(__name__)

# Clear headers to blend in as a typical web visitor
HEADERS = {
    "User-Agent": UserAgent().random
}

TIMEOUT = 12  # Drop dead after 12 seconds per source to avoid hanging

class SubdomainScanner(BaseScanner):
    def __init__(self):
        super().__init__()

    @property
    def name(self) -> str:
        return "subdomain_scanner"

    @property
    def description(self) -> str:
        return "Performs passive subdomain enumeration using multiple sources."


    def run(self, args: List) -> ScanResult:

        parser = argparse.ArgumentParser(description="Subdomain Scanner", exit_on_error=False)
        parser.add_argument("target", help="Target domain")

        try: 
            parsed_args = parser.parse_args(args)
        except argparse.ArgumentError:
            return self.return_value(parser.format_help(), None)
        except SystemExit:
            logging.warning("Invlid argument")
            return
        
        target = parsed_args.target


        logger.info(f"Starting passive subdomain enumeration for: {target}")
        discovered_subdomains = self.run_passive_recon(target)
        logger.info(f"Total unique subdomains found: {len(discovered_subdomains)}")
        
        return self.return_value(json.dumps({"subdomains": list(discovered_subdomains)}, indent=4), target)
    
    def clean_subdomain(self, subdomain: str, target_domain: str) -> str:
        """Standardizes strings, strips wildcards, and ensures it belongs to target."""
        sub = subdomain.strip().lower().lstrip("*.")
        if sub.endswith("."):
            sub = sub[:-1]
        if sub.endswith(target_domain) and sub != target_domain:
            return sub
        return ""

    def fetch_hackertarget(self, domain: str) -> Set[str]:
        url = f"https://api.hackertarget.com/hostsearch/?q={domain}"
        subs = set()
        try:
            res = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            if res.status_code == 200 and "error" not in res.text:
                for line in res.text.splitlines():
                    if "," in line:
                        parts = line.split(",")
                        cleaned = self.clean_subdomain(parts[0], domain)
                        if cleaned: subs.add(cleaned)
        except Exception:
            pass
        return subs

    def fetch_anubis(self, domain: str) -> Set[str]:
        url = f"https://jldc.me/anubis/subdomains/{domain}"
        subs = set()
        try:
            res = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            if res.status_code == 200:
                for item in res.json():
                    cleaned = self.clean_subdomain(item, domain)
                    if cleaned: subs.add(cleaned)
        except Exception:
            pass
        return subs

    def fetch_certspotter(self, domain: str) -> Set[str]:
        url = f"https://api.certspotter.com/v1/issuances?domain={domain}&include_subdomains=true&expand=dns_names"
        subs = set()
        try:
            res = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            if res.status_code == 200:
                for cert in res.json():
                    for name in cert.get("dns_names", []):
                        cleaned = self.clean_subdomain(name, domain)
                        if cleaned: subs.add(cleaned)
        except Exception:
            pass
        return subs

    def fetch_jldc_papi(self, domain: str) -> Set[str]:
        # Aggregated threat intel feed
        url = f"https://api.subdomain.center/api/v1/subdomains?domain={domain}"
        subs = set()
        try:
            res = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            if res.status_code == 200:
                for item in res.json():
                    cleaned = self.clean_subdomain(item, domain)
                    if cleaned: subs.add(cleaned)
        except Exception:
            pass
        return subs

    def run_passive_recon(self, target: str) -> Set[str]:
        logger.info(f"[*] Firing parallel passive recon for: {target}")
        all_subdomains = set() # use set to avoid duplicates
        
        # List of worker functions
        sources = [self.fetch_hackertarget, self.fetch_anubis, self.fetch_certspotter, self.fetch_jldc_papi]
        
        # Run all sources simultaneously using threads
        with ThreadPoolExecutor(max_workers=len(sources)) as executor:
            futures = {executor.submit(source, target): source.__name__ for source in sources}
            
            for future in as_completed(futures):
                source_name = futures[future]
                try:
                    results = future.result()
                    if results:
                        logger.info(f"[+] {source_name} uncovered {len(results)} raw subdomains.")
                        all_subdomains.update(results)
                except Exception as e:
                    logger.error(f"[-] {source_name} threw an exception: {e}")
                    
        return all_subdomains

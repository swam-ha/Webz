import requests
import re
import json
import logging
import threading
import argparse
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from modules.base import BaseScanner, ScanResult
from fake_useragent import UserAgent
from pypdf import PdfReader
import io

# Silence noisy third-party loggers
logging.getLogger("requests").propagate = False
logging.getLogger("urllib3").propagate = False
logging.getLogger("charset_normalizer").propagate = False

class EmailScan(BaseScanner):
    def __init__(self):
        self.session = requests.Session()
        self.ua = UserAgent()
        self.reset()

    def reset(self):
        self.scanned_links = set()
        self.email_list = set()
        self.results = []
        self.lock = threading.Lock()
        self.results_lock = threading.Lock()
        # Synchronization for recursive task tracking
        self.active_tasks = 0
        self.cv = threading.Condition()
        self.stop_requested = threading.Event()

    @property
    def name(self) -> str: return "get_emails"
    
    @property
    def description(self) -> str: return "Extracts emails from all reachable links on a target domain."

    def run(self, args: list) -> ScanResult:
        parser = argparse.ArgumentParser(exit_on_error=False)
        parser.add_argument("url", help="target url")
        parser.add_argument("-th", "--threads", type=int, default=10)

        try:
            parsed = parser.parse_args(args)
            self.reset()
            self.crawl(parsed.url, parsed.threads)
            
            output = json.dumps(self.results, indent=4)
            return self.return_value(output, parsed.url)
        except KeyboardInterrupt:
            # Return whatever was found up to the point of interruption
            output = json.dumps(self.results, indent=4)
            return self.return_value(output, parsed.url)
        except Exception as e:
            return self.return_value(f"Error: {str(e)}", None)

    def _extract_emails(self, text):
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.(?!png|jpg|jpeg|gif|pdf|svg|css|js)[a-zA-Z]{2,}'
        return list(set(re.findall(pattern, text, re.IGNORECASE)))

    def process_url(self, url, target_domain, executor):
        if self.stop_requested.is_set():
            return
        # Mark task as active
        with self.cv:
            self.active_tasks += 1

        try:
            with self.lock:
                if url in self.scanned_links:
                    return
                self.scanned_links.add(url)

            if self.stop_requested.is_set(): return
            print(f"\033[94m[*]\033[0m Trying {url}")
            if self.stop_requested.is_set(): return
            response = self.session.get(url, headers={"User-Agent": self.ua.random}, timeout=(3.05, 10))
            if self.stop_requested.is_set(): return
            content_type = response.headers.get('Content-Type', '').lower()
            text_to_scan = ""

            # check if its a pdf
            if 'application/pdf' in content_type or url.lower().endswith('.pdf'):
                try:
                    print(f"\033[92m[+]\033[0m PDF file detected at {url} ")
                    pdf_file = io.BytesIO(response.content)
                    reader = PdfReader(pdf_file)
                    for page in reader.pages:
                        text_to_scan += page.extract_text() + '\n'
                except Exception:
                    # if pdf file is encrypted or corrupted, skip it
                    return
            else:
                text_to_scan = response.text
                
            emails = self._extract_emails(text_to_scan)
            
            if emails:
                with self.results_lock:
                    new = [e for e in emails if e not in self.email_list]
                    if new:
                        print(f"\033[92m[+]\033[0m Found: {new}")
                        self.email_list.update(new)
                        self.results.append({"emails": new, "url": url})

            # Queue discovery
            if target_domain in urlparse(url).netloc.lower():
                soup = BeautifulSoup(response.text, "html.parser")
                for a in soup.find_all("a", href=True):
                    full_url = urljoin(url, a["href"]).split('#')[0]
                    if full_url.startswith("http"):
                        # Submit new task to executor
                        executor.submit(self.process_url, full_url, target_domain, executor)
        except Exception:
            pass
        finally:
            # Decrement active count and notify if we are finished
            with self.cv:
                self.active_tasks -= 1
                if self.active_tasks == 0:
                    self.cv.notify_all()

    def crawl(self, base_url, workers):
        target_domain = urlparse(base_url).netloc.lower()
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            executor.submit(self.process_url, base_url, target_domain, executor)
            
            try:
                with self.cv:
                    while self.active_tasks > 0:
                        self.cv.wait(timeout=1.0)
            except KeyboardInterrupt:
                self.stop_requested.set()
                self.session.close()
                print("\n[!] Stopping crawler...")
                self.session = requests.Session() # recreate session for next time
                # Force the executor to stop accepting new tasks
                executor.shutdown(wait=True, cancel_futures=True)
                # Re-raise to be caught by run()
                raise KeyboardInterrupt

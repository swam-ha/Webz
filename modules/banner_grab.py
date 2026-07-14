import requests
from fake_useragent import UserAgent
from typing import List, TypedDict, NotRequired
from modules.base import BaseScanner, ScanResult
import logging
import json
import argparse

logger = logging.getLogger(__name__)

timeout = 5

class HttpResponse(TypedDict):
    headers: dict | None
    body: NotRequired[str]



class BannerGrabber(BaseScanner):
    def __init__(self):
        super().__init__()

    @property
    def name(self): return "banner_grab"
    
    @property
    def description(self) -> str:
        return "Grab multiple http banners of various methods"

    def __get_custom_headers(self):
        ua = UserAgent()
        headers = {
            'User-Agent': ua.random,
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive'
        }
        return headers
    

    def head_req(self, url) -> HttpResponse | None:
        try:
            response = requests.head(url, headers=self.__get_custom_headers())
            return {
                #"body": None,
                "headers": dict(response.headers)
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send head request: {e}")
            return
    
    def get_req(self, url) -> HttpResponse | None:
        try:
            response = requests.get(url, headers=self.__get_custom_headers(), timeout=timeout)
            return {
                #"body": response.text,
                "headers": dict(response.headers)
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send head request: {e}")
            return
        
    def post_req(self, url) -> HttpResponse | None:
        try:
            response = requests.post(url, headers=self.__get_custom_headers(), timeout=timeout)
            return {
                #"body": response.text,
                "headers": dict(response.headers)
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send head request: {e}")
            return
        
    def options_req(self, url) -> HttpResponse | None:
        try:
            response = requests.options(url, headers=self.__get_custom_headers(), timeout=timeout)
            return {
                #"body": response.text,
                "headers": dict(response.headers)
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send head request: {e}")
            return
        
    
    def run(self, args: List) -> ScanResult | None:
        parser = argparse.ArgumentParser(
            description="HTTP Banner Grabber"
        )

        parser.add_argument("target_url", help="target website")
        try: 
            parsed_args = parser.parse_args(args)
        except argparse.ArgumentError:
            return self.return_value(parser.format_help(), None)

        except SystemExit:
            logging.warning("Invlid argument")
            return
        
        target = parsed_args.target_url
        self.target = target

        get = self.head_req(target)
        post = self.post_req(target)
        head = self.head_req(target)
        options = self.options_req(target)

        result = {
            "GET": get,
            "POST": post,
            "HEAD": head,
            "OPTIONS": options
        }

        result = json.dumps(result, indent=4)
        return self.return_value(result, target)
        
    
    
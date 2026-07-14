import os

from scapy.all import IP, TCP, sr1 # type: ignore
import logging
from modules.base import BaseScanner, ScanResult
from concurrent.futures import ThreadPoolExecutor, as_completed 
from threading import Event
from typing import List
import socket
import argparse
import ctypes

logger = logging.getLogger(__name__)

class SynScan(BaseScanner):

    def __init__(self) -> None:
        super().__init__() # self.target = None
        self.__stop_event = Event() # signal threads to stop
    
    @property
    def name(self) -> str:
        return "port_scan"
    
    @property
    def description(self) -> str:
        return "TCP SYN port scanner"
    
    def __check_port(self, target, port):
        if self.__stop_event.is_set():
            return None
        tcpRequest = IP(dst=target)/TCP(dport=port, flags="S")
        tcpResponse = sr1(tcpRequest, timeout=1, verbose=0)

        try:
            if tcpResponse.getlayer(TCP).flags == "SA": # type: ignore
                sr1(IP(dst=target) / TCP(dport=port, flags="R"), timeout=1, verbose=0)
                return port
        except AttributeError: # no response / closed port
            pass
        return None
    
    def __scan(self, target, port: int|None=0, thread: int|None=0) -> List:
        self.__stop_event.clear()
        #num_of_ports =  65535
        ports_to_scan = [
            1, 3, 4, 6, 7, 9, 13, 17, 19, 21, 22, 23, 24, 25, 26, 30, 32, 33, 37, 42, 
            43, 49, 53, 70, 79, 80, 81, 82, 83, 84, 85, 88, 89, 90, 99, 100, 106, 109, 
            110, 111, 113, 119, 125, 135, 139, 143, 144, 146, 161, 163, 179, 199, 211, 
            212, 222, 254, 255, 256, 259, 264, 280, 301, 306, 311, 340, 366, 389, 406, 
            407, 416, 417, 425, 427, 443, 444, 445, 458, 464, 465, 481, 497, 500, 512, 
            513, 514, 515, 524, 541, 543, 544, 545, 548, 554, 555, 563, 587, 593, 616, 617, 625
        ]

        workers = 10

        if port:
            if port > 0: ports_to_scan=[port]      
        if thread:
            if thread > 0: workers = thread
        

        logger.info(f"Scanning {target} for [{len(ports_to_scan)}] port/s with {workers} max workers...")

        open_ports = []

        try:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [executor.submit(self.__check_port, target, port) for port in ports_to_scan]

                for future in as_completed(futures):
                    try:
                        result = future.result()
                        if result:
                            logger.info(f"PORT: {result} is listening")
                            open_ports.append(result)
                    except Exception:
                        pass
        except KeyboardInterrupt:
            logger.info("\n[!] Ctrl+C detected. Shutting down scan...")
            self.__stop_event.set()
        
        return open_ports if open_ports else  [f"Scanned {len(ports_to_scan)} ports. No port was listening."]

    def run(self, args: List) -> ScanResult | None:
        # setup parser
        parser = argparse.ArgumentParser(
            description='TCP SYN port scanner',
            exit_on_error=False
        )
        parser.add_argument("target", help="Target IP or domain")
        parser.add_argument("-p", "--port", type=int, help="Single port to scan")
        parser.add_argument("-th", "--thread", type=int, help="Number of threads")
        
        try: 
            parsed_args = parser.parse_args(args)
        except argparse.ArgumentError:
            return self.return_value(parser.format_help(), None)
        except SystemExit:
            logging.warning("Invlid argument")
            return
        
        target = parsed_args.target
        self.target = target    


        if os.name == "posix":
            is_root = os.getuid() == 0
        elif os.name == "nt":
            try:
                is_root = ctypes.windll.shell32.IsUserAnAdmin() != 0
            except Exception as e:
                logger.error(f"Failed to check admin privileges: {e}")
                return
        
        if is_root:
            logger.info("Running with root/administrator privileges.")
        else:
            logger.error("Running as a standard user. Required admin privileges for packet manipulation. Please run as root/administrator.")    
            return
        try:
            # This will raise error if the hostname/IP is invalid
            target = socket.gethostbyname(target)
        except Exception as e:
            error_msg = f"Invalid target: '{target}' could not be resolved."
            logger.error(error_msg)
            return
        
        result = self.__scan(target, port=parsed_args.port, thread=parsed_args.thread)
        return self.return_value(result, *[target])
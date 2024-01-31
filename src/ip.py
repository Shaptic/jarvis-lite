from typing import *

import time
import os.path
import threading
import ipaddress
import csv

import requests

from log import L
from env import ENV


class IPLookupDB:
    """ Provides a simple database for finding geographical locations from IPs.
    """

    def __init__(self,
        condition: Optional[threading.Condition]=None,
        filename: str=os.path.join(ENV.get("data"), "dbip-city.csv")
    ):
        self.cond = condition
        self.filename = filename
        self.db = []

    def load(self):
        self.db = []
        L.info(f"Loading geolocation database from {self.filename} ...")
        with open(self.filename, 'rt') as f:
            for start, end, _, country, region, city, lat, long in csv.reader(f):
                if start == '::': break     # no IPv6 addresses
                # print(start, end, _, country, city, region, lat, long)
                ip1, ip2 = map(ipaddress.IPv4Address, (start, end))
                # bits = math.floor(math.log2(int(ip2) - int(ip1))) - 1
                # network = ipaddress.IPv4Network(f"{str(ip1)}/{32 - bits}")

                self.db.append((
                    int(ip1), int(ip2),
                    f"{city}, {region}, {country}",
                    (float(lat), float(long))
                ))

        L.info(f"Processed {len(self.db)} rows into database.")
        if self.cond: self.cond.notify_all()

    def get_city(self) -> str:
        if os.path.isfile('ipcache.txt'):
            with open('ipcache.txt', 'rt') as f:
                ip = f.read().strip()
        else:
            resp = requests.get("https://api.ipify.org?format=json")
            if resp.status_code != 200:
                raise ValueError(str(resp))

            ip = resp.json()['ip']
            with open('ipcache.txt', 'wt') as f:
                f.write(ip)

        # resp = requests.get(f'https://ipapi.co/{ip}/json')
        L.info(f"Looking up geolocation info for {ip} ...")
        start = time.time()
        result = self.find(ip)[0]
        L.debug(f"Geolocation took {time.time() - start}ms.")
        L.info(f"Geolocation info found: {result}.")
        return result

    def find(self, ip:  Union[str | ipaddress.IPv4Address]) -> Tuple:
        if isinstance(ip, str): ip = ipaddress.IPv4Address(ip)
        if isinstance(ip, ipaddress.IPv4Address):
            ip = int(ip)
        else:
            raise TypeError(f"invalid type: {ip}, need IPv4 or string")

        row = self._find(ip)
        assert ip >= row[0] and ip <= row[1], "failure :("
        return row[2:]

    def _find(self, ip: int) -> Tuple:
        if not self.db:
            self.load()

        lo, hi = 0, len(self.db)
        while lo <= hi:
            mid = (hi + lo) // 2

            row = self.db[mid]
            if row[0] < ip:
                if ip < row[1]:
                    return row
                lo = mid + 1
            elif row[0] > ip:
                hi = mid - 1
            else:
                return row

        return ValueError(f"failed to find range for {ip}")

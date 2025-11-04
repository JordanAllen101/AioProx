import asyncio
import threading
import time
import aiohttp
from aiohttp_socks import ProxyConnector
import logging
"""
TODO
Add save to file flag -- done
Add function to fetch live proxies and save to file every x ammount -- in progress
Prehaps ability to fetch proxies from sources other than github 
(Although technically we aren't bound by github ATM due to us just checking HTML in current state)

"""

# Asyncio Throws a fit about unreliable proxies
logging.getLogger("asyncio").setLevel(logging.CRITICAL)


class AsyncLoopThread:
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _run_loop(self, coro=None):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def run(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result()


_LOOP_THREAD = AsyncLoopThread()


class Proxy:
    def __init__(
        self,
        proxy_type="http",
        source="speedx",
        concurrency=50,
        test_urls=["http://httpbin.org/get"],
        latency=False,
        custom_source=None,
        debug=False,
        timeout=3,
        filename = None
    ):
        self.test_urls = test_urls
        self.proxy_type = proxy_type.lower()
        self.source = source.lower() if source else None
        self.concurrency = concurrency
        self.latency = latency
        self.custom_source = custom_source
        self.debug = debug
        self.timeout = timeout
        self._proxy_cache = None
        self.good_proxies = []
        self.filename = filename

        self.sources = {
            "speedx": {
                "http": "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/refs/heads/master/http.txt",
                "socks4": "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
                "socks5": "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
            },
            "proxifly": {
                "http": "https://raw.githubusercontent.com/proxifly/free-proxy-list/refs/heads/main/proxies/protocols/http/data.txt",
                "socks4": "https://raw.githubusercontent.com/proxifly/free-proxy-list/refs/heads/main/proxies/protocols/socks4/data.txt",
                "socks5": "https://raw.githubusercontent.com/proxifly/free-proxy-list/refs/heads/main/proxies/protocols/socks5/data.txt",
            },
            "databay": {
                "http": "https://raw.githubusercontent.com/databay-labs/free-proxy-list/refs/heads/master/http.txt",
                "socks5": "https://raw.githubusercontent.com/databay-labs/free-proxy-list/refs/heads/master/socks5.txt",
            },
        }

        if self.custom_source:
            self.proxy_url = None
        else:
            try:
                self.proxy_url = self.sources[self.source][self.proxy_type]
            except KeyError:
                raise ValueError(
                    f"Unsupported combination or missing source: source='{self.source}', type='{self.proxy_type}'"
                )

    async def _get_list_async(self, force_refresh=False):
        if self._proxy_cache and not force_refresh:
            return self._proxy_cache

        proxy_list = []

        if self.custom_source:
            try:
                if isinstance(self.custom_source, list):
                    proxy_list = [p.strip() for p in self.custom_source if p.strip()]
                elif isinstance(self.custom_source, str):
                    if self.custom_source.startswith(("http://", "https://")):
                        async with aiohttp.ClientSession() as session:
                            async with session.get(self.custom_source, timeout=10) as resp:
                                text = await resp.text()
                    else:
                        with open(self.custom_source, "r", encoding="utf-8") as f:
                            text = f.read()
                    proxy_list = [p.strip() for p in text.splitlines() if p.strip()]
            except Exception as e:
                if self.debug:
                    print(f"[ERROR] Failed to fetch custom source: {e}")
        elif self.proxy_url:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(self.proxy_url, timeout=10) as resp:
                        text = await resp.text()
                proxy_list = [p.strip() for p in text.splitlines() if p.strip()]
            except Exception as e:
                if self.debug:
                    print(f"[ERROR] Failed to fetch proxy URL {self.proxy_url}: {e}")

        clean_list = [p.split("://", 1)[1] if "://" in p else p for p in proxy_list]
        self._proxy_cache = clean_list
        return clean_list

    def save_proxy_file(self, proxies):
        filename = self.filename
        with open(filename, "w", encoding="utf-8") as file:
                for proxy in proxies:
                    # Handle latency = True 
                    if isinstance(proxy, dict):
                        file.write(proxy["proxy"] + "\n")
                    else:
                        file.write(proxy + "\n")
    async def _is_live_async(self, proxy_ip_port, test_urls, timeout=None, latency=False):
        timeout = timeout or self.timeout
        proxy_url = f"{self.proxy_type}://{proxy_ip_port}"
        timeout_obj = aiohttp.ClientTimeout(total=timeout)
        start = time.perf_counter()

        try:
            if self.proxy_type in ("socks4", "socks5"):
                connector = ProxyConnector.from_url(proxy_url)
                async with aiohttp.ClientSession(connector=connector, timeout=timeout_obj) as session:
                    for url in test_urls:
                        passed = await self._fetch_url(session, url)
                        if self.debug:
                            print(f"[DEBUG] {proxy_ip_port} -> {url} {'PASSED' if passed else 'FAILED'}")
                        if not passed:
                            return (False, None) if latency else False
            else:
                async with aiohttp.ClientSession(timeout=timeout_obj) as session:
                    for url in test_urls:
                        passed = await self._fetch_url(session, url, proxy_url)
                        if self.debug:
                            print(f"[DEBUG] {proxy_ip_port} -> {url} {'PASSED' if passed else 'FAILED'}")
                        if not passed:
                            return (False, None) if latency else False

            end = time.perf_counter()
            return (True, end - start) if latency else True

        except Exception as e:
            if self.debug:
                print(f"[DEBUG] {proxy_ip_port} failed with exception: {e}")
            return (False, None) if latency else False

    async def _fetch_url(self, session, url, proxy=None):
        try:
            async with session.get(url, proxy=proxy) as resp:
                return resp.status == 200
        except (aiohttp.ClientError, asyncio.TimeoutError, ConnectionResetError, OSError) as e:
            return False

    async def _find_first_live_proxy_async(self, test_urls_override=None):
        proxy_list = await self._get_list_async()
        if not proxy_list:
            return None

        semaphore = asyncio.Semaphore(self.concurrency)
        test_urls = test_urls_override or self.test_urls
        total = len(proxy_list)
        counter = 0

        async def test_proxy(proxy):
            nonlocal counter
            async with semaphore:
                counter += 1
                if self.debug:
                    print(f"[DEBUG] Testing proxy {counter}/{total}: {proxy}")
                result = await self._is_live_async(proxy, test_urls, latency=self.latency)
                if self.latency:
                    is_live, _ = result
                    return proxy if is_live else None
                else:
                    return proxy if result else None

        tasks = [test_proxy(p) for p in proxy_list]
        for fut in asyncio.as_completed(tasks):
            result = await fut
            if result:
                return result
        return None

    async def _find_all_live_proxies_async(self):
        proxy_list = await self._get_list_async()
        if not proxy_list:
            return []

        semaphore = asyncio.Semaphore(self.concurrency)
        live = []
        total = len(proxy_list)
        counter = 0

        async def test_proxy(proxy):
            nonlocal counter
            async with semaphore:
                counter += 1
                if self.debug:
                    print(f"[DEBUG] Testing proxy {counter}/{total}: {proxy}")
                result = await self._is_live_async(proxy, self.test_urls, latency=self.latency)
                if self.latency:
                    is_live, delay = result
                    if is_live:
                        live.append({"proxy": proxy, "latency": delay})
                else:
                    if result:
                        live.append(proxy)

        tasks = [test_proxy(p) for p in proxy_list]
        for fut in asyncio.as_completed(tasks):
            await fut

        if self.latency:
            live.sort(key=lambda x: x["latency"])

        self.good_proxies = live
        if self.filename:
            self.save_proxy_file(live)
        return live

    def get_random_proxy(self, test_urls=None):
        if self.latency:
            results = _LOOP_THREAD.run(self._find_all_live_proxies_async())
            if results:
                return results[0]["proxy"]
            return None
        return _LOOP_THREAD.run(self._find_first_live_proxy_async(test_urls_override=test_urls))

    def get_good_proxies(self):
        return _LOOP_THREAD.run(self._find_all_live_proxies_async())



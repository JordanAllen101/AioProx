# aioprox

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**aioprox** – Asynchronous proxy manager for Python. Fetch, test, and filter HTTP/SOCKS proxies with optional latency measurement and support for custom sources.

---

## Project Overview

`aioprox` is designed for developers who need a reliable, asynchronous proxy management tool in Python. It allows you to quickly fetch proxies from multiple sources, test them concurrently, and optionally measure latency to select the fastest proxies. Whether you want a single random live proxy or a fully sorted list of working proxies, `aioprox` makes it easy. You can also supply your own proxy lists via a file, URL, or Python list.

---

## Features

- Fetch proxies from multiple built-in sources or user-supplied sources (URL, file, or list).  
- Test proxies asynchronously for availability.  
- Optional latency measurement to find the fastest proxies.  
- Retrieve a single random live proxy or a full list of working proxies.  
- Supports HTTP, SOCKS4, and SOCKS5 proxies.  
- Concurrency control for fast testing of large proxy lists.  
- Easy to integrate in both scripts and larger Python projects.

---

## Installation

```bash
pip install aiohttp aiohttp_socks
```

Then clone this repo or 
```bash
pip install aioprox
```

---

## Usage

### 1. Using a Built-in Source

```python
from aioprox import Proxy

# Initialize with built-in source
p = Proxy(proxy_type="http", source="monosans")

# Get all live proxies
proxies = p.get_good_proxies()
print(proxies)

# Get a single random live proxy
random_proxy = p.get_random_proxy()
print(f"Random proxy: {random_proxy}")
```

### 2. Measuring Latency

```python
# Enable latency measurement
p = Proxy(proxy_type="http", source="monosans", latency=True)

# Get proxies sorted by latency
proxies = p.get_good_proxies()

# Get the fastest proxy
fastest_proxy = p.get_random_proxy()
print(proxies)
print(f"Fastest proxy: {fastest_proxy}")
```

### 3. Using a Custom List of Proxies

```python
custom_list = [
    "123.45.67.89:8080",
    "98.76.54.32:1080",
]

p = Proxy(proxy_type="http", custom_source=custom_list, latency=True)
proxies = p.get_good_proxies()
print(proxies)
```

### 4. Using a Custom URL or File

```python
# From a URL
p = Proxy(proxy_type="socks5", custom_source="https://example.com/proxylist.txt")
proxies = p.get_good_proxies()
print(proxies)

# From a local file
p = Proxy(proxy_type="http", custom_source="proxies.txt")
proxies = p.get_good_proxies()
print(proxies)
```

---

## Supported Proxy Types

- HTTP  
- SOCKS4  
- SOCKS5  

---

## Concurrency

By default, proxy testing uses a concurrency of 50. You can adjust it when creating the `Proxy` object:

```python
p = Proxy(proxy_type="http", source="monosans", concurrency=100)
```

---

## Error Handling

- Failed proxy sources print informative messages.  
- Dead proxies are automatically filtered out.  
- Latency measurement is optional; if not enabled, only live/dead status is returned.

---

## Example Output

```python
[{'proxy': '123.45.67.89:8080', 'latency': 0.234},
 {'proxy': '98.76.54.32:1080', 'latency': 0.421}]
Fastest proxy: 123.45.67.89:8080
```

---

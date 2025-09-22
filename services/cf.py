import ipaddress

with open("cf-ipsv4.txt") as f:
    ipv4List = f.read().splitlines()

with open("cf-ipsv6.txt") as f:
    ipv6List = f.read().splitlines()

networks = [ipaddress.ip_network(cidr) for cidr in ipv4List + ipv6List]


def isFromCloudflare(ip: str) -> bool:
    try:
        ip_addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(ip_addr in net for net in networks)

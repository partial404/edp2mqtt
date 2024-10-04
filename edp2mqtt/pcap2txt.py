"""
Utility program for parsing pcap files and running through the parser.
"""

import sys

import dpkt

from . import parser

if __name__ == "__main__":
    with open(sys.argv[1], "rb") as h:
        for ts, pkt in dpkt.pcap.Reader(h):
            eth = dpkt.ethernet.Ethernet(pkt)
            ip = eth.data
            if ip.p != dpkt.ip.IP_PROTO_UDP:
                print(f"Unsupported protocol, got {ip.type}!")
                continue
            udp = ip.data
            packet = parser.parse_packet(udp.data)
            if packet:
                print(packet)
            if not packet:
                print("Failed to parse, " + " ".join([hex(x) for x in udp.data]))

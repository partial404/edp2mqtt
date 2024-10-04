"""
Main CLI program. Sets up listener server for incoming EDP packages,
decodes and sends them onwards to a MQTT bus.
"""

import argparse
import json
import logging
import os
import socketserver

import paho.mqtt.client

from . import parser
from .structures import PackageRegistry

logger = logging.getLogger(__name__)


# pylint: disable=redefined-outer-name
class EDPHandler(socketserver.DatagramRequestHandler):
    """
    Callback class for the socker server, handles the packages by parsing and
    sending the decoded package onwards as an MQTT message.
    """

    def handle(self):
        logger.info("Received UDP message from %s", self.client_address[0])
        raw_data = self.rfile.read()
        logger.info("Message: %s", raw_data.hex())
        try:
            packet = parser.parse_packet(raw_data)
            if packet:
                logger.info("Parsed package: %s", packet)
                if not self.server.packet_registry.register(packet["package_counter"]):
                    logger.warning(
                        "Already seen packet %d, ignoring", packet["package_counter"]
                    )
                    return
                self.server.mqtt_client.publish(
                    self.server.mqtt_topic, json.dumps(packet)
                )
                return
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception("Exception while parsing package")
        if self.server.unknown_dump:
            logger.info(
                "Failed to parse packet, dumping to %s, %s",
                self.server.unknown_dump,
                raw_data.hex(),
            )
            with open(self.server.unknown_dump, "a", encoding="utf-8") as h:
                h.write(raw_data.hex())
                h.write("\n")
        else:
            logger.info("Failed to parse packet, %s", raw_data.hex())

    def finish(self):
        # Do nothing, overrides default that sends response!
        # In the future we should ACK the message here.
        pass


if __name__ == "__main__":

    argp = argparse.ArgumentParser(
        prog="edp2mqtt",
        description="Consumes EDP packages and sends to MQTT",
    )
    argp.add_argument(
        "-l",
        "--listen-host",
        default="0.0.0.0",
        help="Incoming UDP host to listen for EDP packages on",
    )
    argp.add_argument(
        "-p",
        "--listen-port",
        default=50000,
        help="Incoming port and protocol to listen for EDP packages on",
    )
    argp.add_argument(
        "-u",
        "--unknown_dump",
        default=None,
        metavar="unknown-file",
        help="Path to file where hex of unknown packages are dumped (appended)",
    )
    argp.add_argument(
        "-t",
        "--topic",
        default="edp2mqtt",
        help="MQTT topic of outgoing messages",
    )
    argp.add_argument("mqtt_fqdn", metavar="mqtt-fqdn", help="MQTT server FQDN")
    argp.add_argument(
        "mqtt_port",
        metavar="mqtt-port",
        default=1883,
        nargs="?",
        help="MQTT server port",
    )

    args = argp.parse_args()

    logging.basicConfig(level=logging.INFO)

    logger.info("Setting up MQTT...")
    mqtt_client = paho.mqtt.client.Client()
    if os.environ.get("MQTT_USER") and os.environ.get("MQTT_PASS"):
        logger.info(
            "Using MQTT credentials from MQTT_USER and MQTT_PASS environment variables..."
        )
        mqtt_client.username_pw_set(
            os.environ.get("MQTT_USER"), os.environ.get("MQTT_PASS")
        )
    if os.environ.get("MQTT_USER_FILE") and os.environ.get("MQTT_PASS_FILE"):
        logger.info(
            "Using MQTT credentials from MQTT_USER_FILE and MQTT_PASS_FILE environment variables..."
        )
        with open(os.environ.get("MQTT_USER_FILE"), encoding="utf-8") as h:
            username = h.read()
        with open(os.environ.get("MQTT_PASS_FILE"), encoding="utf-8") as h:
            password = h.read()
        mqtt_client.username_pw_set(username, password)

    # pylint: disable=unused-argument, missing-function-docstring
    @mqtt_client.connect_callback()
    def mqtt_connect(client, userdata, flags, rc):
        reason_code = paho.mqtt.client.convert_connack_rc_to_reason_code(rc)
        if reason_code.is_failure:
            logger.error("Failed to connect to MQTT server; %s!", reason_code.getName())
        else:
            logger.info("Connected to MQTT server")

    # pylint: disable=unused-argument, missing-function-docstring
    @mqtt_client.disconnect_callback()
    def mqtt_disconnect(client, userdata, flags):
        logger.error("Disconnected from MQTT server")

    logger.info("Connecting to MQTT server, %s:%s...", args.mqtt_fqdn, args.mqtt_port)
    mqtt_client.connect(args.mqtt_fqdn, args.mqtt_port)
    mqtt_client.loop_start()

    socketserver.UDPServer.allow_reuse_address = True
    logger.info(
        "Starting to listen for incoming UDP packages on %s:%s...",
        args.listen_host,
        args.listen_port,
    )
    serverUDP = socketserver.UDPServer((args.listen_host, args.listen_port), EDPHandler)
    serverUDP.mqtt_client = mqtt_client
    serverUDP.unknown_dump = args.unknown_dump
    serverUDP.packet_registry = PackageRegistry()
    serverUDP.mqtt_topic = args.topic

    serverUDP.serve_forever()

"""
Parser implementation for the EDP protocol
"""

import datetime
import logging

logger = logging.getLogger(__name__)


def parse_payload_panel(state, user_id, parts):
    """
    Parses a package payload of panel type

    :param state: Event state
    :param user_id: ID of user that triggered event
    :param parts: List of payload parts
    :return: Dict containing parsed data
    """
    assert len(parts) == 3
    return {
        "state": state,
        "user_id": user_id,
        "user": parts[0],
        "panel_name": parts[1],
        "panel_id": int(parts[2]),
    }


def parse_payload_programming(state, _, parts):
    """
    Parses a package payload of programming type

    :param state: Event state
    :param _: Unused/Unknown
    :param parts: List of payload parts
    :return: Dict containing parsed data
    """
    assert len(parts) == 1
    return {
        "state": state,
        "message": parts[0],
    }


def parse_payload_zone(state, zone_id, parts):
    """
    Parses a package payload of zone type

    :param state: Event state
    :param zone_id: ID of zone that triggered event
    :param parts: List of payload parts
    :return: Dict containing parsed data
    """
    assert len(parts) == 4
    assert parts[1] == "ZONE"
    return {
        "state": state,
        "zone_id": zone_id,
        "zone_name": parts[0],
        "area_id": int(parts[2]),
        "area_name": parts[3],
    }


def parse_payload_area(state, area_id, parts):
    """
    Parses a package payload of area type

    :param state: Event state
    :param area_id: ID of area that triggered event
    :param parts: List of payload parts
    :return: Dict containing parsed data
    """
    assert len(parts) == 3
    return {
        "state": state,
        "area_id": area_id,
        "area_name": parts[0],
        "user_name": parts[1],
        "user_id": int(parts[2]),
    }


def parse_payload(raw_data):
    """
    Parse raw payload data

    :param raw_data: Raw payload
    :return: Dict containing parsed data
    """
    data = raw_data.decode("latin-1")
    if data[0] != "[":
        logger.error("Incorrect payload start, got %s!", hex(data[0]))
        return None
    if data[-1] != "]":
        logger.error("Incorrect payload end, got %s!", hex(data[-1]))
        return None
    parts = data[1:-1].split("|")
    if len(parts) != 7:
        logger.error(
            "Unexpected number of payload parts, got %s! %s", len(parts), parts
        )
        return None
    res = {
        "edp_panel_id": int(parts[0][1:]),
        "timestamp": datetime.datetime.strptime(parts[1], "%H%M%S%d%m%Y")
        .astimezone()
        .timestamp(),
        "unknown5": parts[5],
        "unknown6": parts[6],
    }
    action_id = int(parts[3])
    state_map = {
        "ZC": ("ZONE_CLOSED", parse_payload_zone),
        "ZO": ("ZONE_OPEN", parse_payload_zone),
        "LB": ("LOCAL_PROGRAMMING", parse_payload_programming),
        "LX": ("LOCAL_PROGRAMMING_ENDED", parse_payload_programming),
        "JP": ("PANEL_LOGON", parse_payload_panel),
        "ZG": ("PANEL_LOGOFF", parse_payload_panel),
        "CG": ("AREA_SET", parse_payload_area),
        "OG": ("AREA_UNSET", parse_payload_area),
    }
    if parts[2] not in state_map:
        logging.error("Unknown event state, %s!", parts[2])
        return None

    (state, state_func) = state_map[parts[2]]
    res.update(state_func(state, action_id, parts[4].split("¦")))
    return res


def parse_v1_header(data):
    """
    Parse header of version 1 packet

    :param data: Complete packet data
    :return: Tuple with header dict and payload data
    """
    payload_length = int.from_bytes(data[12:14], byteorder="little")
    actual_length = len(data) - 14
    if payload_length != actual_length:
        logger.error(
            "Payload length missmatch, header says %d, got %d!",
            payload_length,
            actual_length,
        )
        return None

    return (
        {
            "package_counter": int(data[3]),
            "edp_panel_id": int.from_bytes(data[4:8], byteorder="little"),
            "unknown2": data[8:10].hex(),
            "unknown3": data[10:12].hex(),
            "payload_length": payload_length,
            "unknown4": data[14:16].hex(),
        },
        data[16:],
    )


def parse_v2_header(data):
    """
    Parse header of version 2 packet

    :param data: Complete packet data
    :return: Tuple with header dict and payload data
    """
    payload_length = int.from_bytes(data[19:21], byteorder="little")
    actual_length = len(data) - 21
    if payload_length != actual_length:
        logger.error(
            "Payload length missmatch, header says %d, got %d!",
            payload_length,
            actual_length,
        )
        return None

    return (
        {
            "package_counter": int.from_bytes(data[3:7], byteorder="little"),
            "edp_panel_id": int.from_bytes(data[7:11], byteorder="little"),
            "receiver_id": int.from_bytes(data[11:15], byteorder="little"),
            "unknown2": data[15:17].hex(),
            "unknown3": data[17:19].hex(),
            "payload_length": payload_length,
            "unknown4": data[21:23].hex(),
        },
        data[23:],
    )


def parse_packet(data):  # pylint: disable=too-many-return-statements
    """
    Main parse method, parses the entire packet

    :param data: Packet data to parse
    :return: Packet in dict form or None if failure to parse.
    """
    if len(data) < 3:
        logger.error("Too short header, got %d!", len(data))
        return None

    if data[0] != 0x45:
        logger.error("Incorrect header, got %s!", hex(data[0]))
        return None

    if data[2] == 0x01:
        logger.warning("Encrypted package not supported yet!")
        return None
    if data[2] != 0x00:
        logger.error("Unknown value pos 0x02: got %s!", hex(data[2]))
        return None

    res = {"version": data[1], "encrypted": bool(data[2])}
    version_map = {
        0x01: parse_v1_header,
        0x02: parse_v2_header,
    }
    if data[1] not in version_map:
        logger.warning("Unsupported version, got %d!", data[1])
        return None
    (additional_header, payload_data) = version_map[data[1]](data)
    res.update(additional_header)
    if not payload_data:
        return None
    payload = parse_payload(payload_data)
    if not payload:
        return None
    res.update(payload)
    return res

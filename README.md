# edp2mqtt

Listens for EDP packages send from an SPC panel and emits parsed messages to a
MQTT bus.

## Getting Started
Getting up and running requires two steps, setting up your SPC panel to emit
EDP packages, as well as setting up an edp2mqtt instance that receive and send
parsed packages onwards to MQTT.

### Configure SPC
Login to your SPC panel through the web interface and enable `Engineer mode` so
that EDP reporting can be configured. Configuration of EDP is done under menu
options `Communications`, then `Reporting`, and finally `EDP`. Here two
operations are needed, general settings and adding a receiver.

General setup is done by clicking `Settings` button on the `EDP` page.
Verify the following three settings:
* `Enable` checkbox is checked
* A valid `EDP Panel ID` has been entered
* `Retry Count` is set to zero. This library will handle resent packages by
  filtering repeated packages, but set to zero to be on the safe side, this
  also reduces the amount of traffic.

Add a new receiver by clicking `Add` on the `EDP` page. On the next page,
specify:
* A `Description` of the receiver. The description is only shown in the SPC UI,
  so, set it to something that explains its purpose, e.g.
  `My edp2mqtt receiver`.
* A `Receiver Id`. The id will be sent along in the packages emitted by the
  panel, and can be used to be separate between different receives.

Press `Save`.

On the next page, two things needs to be setup:
* Check `Network Enable`. In the input fields that appear, enter
 `Receiver IP Address` and `Receiver IP Port` to the server where edp2mqtt is
  running. Ensure that UDP is selected. Leave `Always Connected` and 
 `Generate a Network Fault` unchecked.
* Click the `Filter` button. A new `Event Filter` page will appear, ensure that
  all checkboxes are checked, and that all Areas, that are to be monitored, are
  selected.

Finish by pressing `Save` and then leaving `Engineer mode` for changes to take
effect.

### Running In Docker

In its shortest form, the following will start edp2mqtt in docker, lister for
`udp` packages on port `50000`, and send them to a mqtt server named
`mqtt-server`:

    docker run -p 50000:50000/udp partial404/edp2mqtt mqtt-server 

This assumes that no credentials are needed for the MQTT server. If needed,
mqtt credentials can be supplied through an environment file:

    $ cat mqtt-credentials.list
    MQTT_USER=mqtt_username
    MQTT_PASS=super-secret-password

    $ docker run -p 50000:50000/udp --env-file mqtt-credentials.list partial404/edp2mqtt mqtt-server 

For more information about credentials, see `MQTT Credentials` section below,
and for general arguments, see `Arguments` section.

### Running Standalone
For simplicity, and isolation, it is recommended to use docker as per
instructions above, but, for special cases, stubborn users and development,
edp2mqtt can of course be executed standalone. This is done using Poetry.
Assuming this repositroy has been cloned to current working directory:

    $ poetry install
    $ poetry run python -m edp2mqtt.main mqtt-server

First line instructs Poetry to download and install dependencies. Second line
starts an edp2mqtt instance that listens for `UDP` packages on port `50000` and
sends parsed packages to a MQTT server named `mqtt-server`.

### Arguments
Positional arguments

| Argument  | Default Value | Description      |
|-----------|---------------|------------------|
| mqtt-fqdn | <required>    | MQTT server FQDN |
| mqtt-port | 1883          | MQTT server port |

Options:

| Flag               | Default Value | Description                                                      |
|--------------------|---------------|------------------------------------------------------------------|
| -l, --listen-host  | 0.0.0.0       | Incoming UDP host to listen for EDP packages on                  |
| -p, --listen-port  | 50000         | Incoming port and protocol to listen for EDP packages on         |
| -u, --unknown-dump | None          | Path to file where hex of unknown packages are dumped (appended) |
| -t, --topic        | edp2mqtt | MQTT topic of outgoing messages |

### MQTT Credentials
Credentials to MQTT server can be supplied in two ways, as environment
variables, or as files on disk. The latter of the two is more secure and should
be used in situations where the environment variables may end up as part of the
command, e.g. when edp2mqtt is started through docker and using -e arguments to
docker.

Username and password can be supplied directly through the two environment
variables `MQTT_USER` and `MQTT_PASS`. While `MQTT_USER_FILE` and
`MQTT_PASS_FILE` environment variables specifies the path to files containing
username and password.

## Supported Events
Currently supported event types:

| EDP ID | MQTT state              | Description                                                       |
|--------|-------------------------|-------------------------------------------------------------------|
| ZO     | ZONE_OPEN               | Emitted when a zone is opened. E.g. PIR detecting or door opened. |
| ZC     | ZONE_CLOSED             | Emitted when a zone is closed.                                    |
| LB     | LOCAL_PROGRAMMING       | Emitted when an administrator enters programming mode.            |
| LX     | LOCAL_PROGRAMMING_ENDED | Emitted when an administrator leaves programming mode.            |
| JP     | PANEL_LOGON             | Emitted when a user logs on a panel.                              |
| ZG     | PANEL_LOGOFF            | Emitted when a user logs off a panel.                             |
| CG     | AREA_SET                | Emitted when an area is set/armed.                                |
| OG     | AREA_UNSET              | Emitted when an area is unset/unarmed.                            |

## Limitations
Current known limitations:
* Currently only support UDP, not TCP. TCP require proper package
  acknowledgement, and payload of acknowledgement packages is currently
  unknown.
* Received messages aren't acknowledged. As with the bullet above, acknowledge
  package payload is unknown.
* No check sum calculation. Byte 0x17 and 0x18 of v2 packages is suspected to
  be checksum bytes, but algorithm is unknown.
* No encryption support. Encryption algorithm is currently unknown.

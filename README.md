# zbxmonitor

## Description
While monitoring a few hosts with Zabbix, it's easy to send alerts by e-mail or SMS. But when something goes wrong (SMTP server or GSM modem is down, etc.), you will not receive any error message.

ZbxMonitor resolves such problems by adding "second channel" from local desktop to Zabbix Server. ZbxMonitor periodically pulls data from Zabbix Server and shows its status in icon tray.

Presently zbxmonitor is tested with python 2.7 and zabbix 3.x and 4.x

## Usage
If's recommended to not launch zbxmonitor.py directly, but to create symbolic link to this file (eg. `ln -s zbxmonitor.py myzabbix.example.com.py`), then create config file `myzabbix.example.com.config`
and launch this symlink. You can run multiple instances of monitor on multiple Zabbix Servers this way.

## Requirements
All packages listed in `import` \*.py. Pyzabbix has been installed with `pip`.

### Config file
Config file must be named as \<script\>.config, eg. `zbxmonitor.py` uses `zbxmonitor.config` and must be present in script "home" directory. Config should be not readable by others/group.
Path to icons and sounds are relative to ./icons and ./sounds dirs.

Section `zbxCredenials` is described in `zbxmonitor.config.example`. Section `zbxOptions` description:
- icon - default: host in `zbxCredenials`. You must have two files in ./icons dir: `host.example.com-ok.png` and `host.example.com-err.png` in this example.
- wav - default: None. You must have two files (named aka icons) in ./sounds dir if specified.
- wav_player - default: /usr/bin/mpv. External wav player. Ignored if wav is not specified.
- interval - default: 30[s]. Pooling interval
- port - default: 10051
- notify - default: True. Messages will be send to notification daemon (eg. `dunst`). If empty you will be not notified, but status will be still enabled by left or right click on script icon.
- ignore_warn - default: False. True - SSL warnings will be suppressed (when connecting to Zabbix Server via https)
- text_mode - default: False. If True (or not empty) zbxmonitor will work in text mode only. It is rather for testing purpose.
- ackOnly - default: True. Only unacknowledged messages will be shown. If empty monitor will show all (acknowledged and unacknowledged) messages.

#### Filtering messages

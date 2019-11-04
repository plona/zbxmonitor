# zbxmonitor

## Description
While monitoring a few hosts with Zabbix, it's easy to send alerts by e-mail or SMS. But when something goes wrong (SMTP server or GSM modem is down, etc.), you will not receive any error message.

ZbxMonitor resolves such problems by adding "second channel" from local desktop to Zabbix Server. ZbxMonitor periodically pulls data from Zabbix Server and shows its status in icon tray.

Presently zbxmonitor is tested with python 2.7 and zabbix 3.x and 4.x

## Usage
If's recommended to not launch zbxmonitor.py directly, but to create symbolic link to this file (eg. `ln -s zbxmonitor.py myzabbix.example.com.py`), then create config file `myzabbix.example.com.config`
and launch this symlink. You can run multiple instances of monitor on multiple Zabbix Servers this way.

## Requirements
All packages listed in `import` \*.py.

pip:
- pyzabbix
- plyer

### Config file
Config file must be named as \<script\>.config, eg. `zbxmonitor.py` uses `zbxmonitor.config` and must be present in script "home" directory. Config should be not readable by others/group.
Path to icons and sounds are relative to ./icons and ./sounds dirs.

Section `zbxCredenials` is described in `zbxmonitor.config.example`. Section `zbxOptions` description:
- ackOnly - default: True. Only unacknowledged messages will be shown. If False monitor will show all (acknowledged and unacknowledged) messages.
- icon - default: host in `zbxCredenials`. You must have two files in ./icons dir: `host.example.com-ok.png` and `host.example.com-err.png` in this example.
- ignore_warn - default: False. True - SSL warnings will be suppressed (when connecting to Zabbix Server via https)
- interval - default: 30[s]. Pooling interval
- log_truncate - default: False. If True log file in ./log will be truncated at start.
- notify - default: True. Messages will be send to notification daemon (eg. `dunst`). If empty you will be not notified, but status will be still enabled by left or right click on script icon.
- port - default: 10051
- text_mode - default: False. If True (or 0) zbxmonitor will work in text mode only. It is rather for testing purpose.
- wav - default: None. You must have two files (named aka icons) in ./sounds dir if specified.
- wav_player - default: /usr/bin/mpv. External wav player. Ignored if wav is not specified.

#### Filtering messages
re.search() is used.
- exclTg - default: empty list. If not empty `inclTg` is ignored. Example:<br>
`exclTg = [ "^SSL.*certificate", ".*overload.*" ]` - all messages contains strings in list will be suppressed.
- inclTg - default: empty list. Valid only if `exclTg` is empty. Example:<br>
`inclTg = [ ".*\.google\.com" ]` - only messages contains strings in list will be shown.

### Icon in tray
- left click shows current status of Zabbix Server.
- right click brings popup:
    - Close applet
    - Show all (acknowledged and unacknowledged) messages
    - Show unfiltered and unacknowledged messages

## Windows
### Requirements
- Python 2.7.17 (64 bit), python-2.7.17.amd64.msi
- Python 2.7 pycairo-1.10.0 (64-bit), py2cairo-1.10.0.win-amd64-py2.7.exe
- Python 2.7 pygobject-2.28.6 (64-bit), pygobject-2.28.6.win-amd64-py2.7.exe
- Python 2.7 pygtk-2.22.0 (64-bit), pygtk-2.22.0.win-amd64-py2.7.exe

Entries: `wav` and `wav_player` are ignored in windows.<br>
I don't know how to daemonize script - there is no `fork` in windows. But you can launch script with `pythonw` not `python`, eg.:
```
<path_to_pythonw.exe> <path_to_script>
```
Notification in windows sometime works, but sometime doesn't. Icon i tray works fine.

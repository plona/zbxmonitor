# zbxmonitor

## Description
While monitoring a few hosts with Zabbix, it's easy to send alerts by e-mail or SMS. But when something goes wrong (SMTP server or GSM modem is down, etc.), you will not receive any error message.

ZbxMonitor resolves such problems by adding "second channel" from local desktop to Zabbix Server. ZbxMonitor periodically pulls data from Zabbix Server and shows its status in icon tray.

Presently zbxmonitor is tested with python 2.7 and zabbix 3.x and 4.x

## Usage
If's recommended to not launch zbxmonitor.py directly, but to create symbolic link to this file (eg. `ln -s zbxmonitor.py myzabbix.example.com`), then create config file `myzabbix.example.com.config`
and launch this symlink. You can run multiple instances of monitor on multiple Zabbix Servers this way.

## Requirements
All packages listed in `import` \*.py. Pyzabbix has been installed with `pip`.

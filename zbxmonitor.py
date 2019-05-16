#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Zabbix monitor client which talks with zabbix server using API provided by zabbix.
Creates icon in tray which represents current status of monitored server.

OPTIONS
    -h|--host
        hostname or ip
    -c|--command
        start/stop. Default is start.
    -u|--user
        zabbix user name. Should has read-only permission to all monitored hosts
        and should has not access to zabbix WEB GUI.
    -P|--password
        password for zabbix user. If omitted you'll be asked for password.
        It's strongly recommended do omit this option, because your
        password will be visible in process list.
    -C|--credentials
        path to credentials file. Only first line is read (password). File name
        may be absolute path or file in client "home" directory
    Options: host and user are mandatory. Option password has no default value.
    -i|--interval
        pooling interval [s]. Default is 60.
    -p|--port
        communication port. Default is 10051
    -I|--icon
        icon name for OK and ERR status. Icons must be found in client "home"
        directory and must be *.png files. File names are calculated as:
        "homedir/icon-ok.png" and "homedir/icon-err.png", so with
        option --icon=myicon you should have two files: myicon-ok.png and
        myicon-err.png i client home directory. Default icon name is "icon".
    -n|--notify
        If set sends "balloon" notifies. If not, shows icon in tray only.
        Default false.
    -t|--text
        text mode when pick user password. Useful for zab-expect
    -W|--wav
        *.wav files for OK and ERR status. File names are calculated like icon
        files. Default none. If not set no sound will be played.
    -w|--wav-player
        player for *.wav files. Must be installed. Default is "/usr/bin/mpv".

"""

from socket import *
from pyzabbix import *
from subprocess import call
from daemon import Daemon
import time
import os
import sys
import getopt
import getpass
import gobject
import notify2
import syslog
import ConfigParser
from dialog_nix import *


class DataContainer:
    def __init__(self, script_name):
        self.script_full_path = os.path.abspath(script_name)
        self.script_dir = os.path.dirname(self.script_full_path)
        self.script_name = os.path.basename(self.script_full_path)
        self.script_short_name = os.path.splitext(self.script_full_path)[0]

        self.config_file = self.script_short_name + ".config"
        self.credentials_file = self.script_short_name + ".credentials"
        # print self.config_file
        # print self.credentials_file
        self.config = ConfigParser.ConfigParser()

        self.config.read(self.credentials_file)
        self.zbxhost = self.config.get("zbxCredentials", "host")
        self.zbxuser = self.config.get("zbxCredentials", "user")
        try:
            self.zbxpasswd = self.config.get("zbxCredentials", "passwd")
        except:
            self.zbxpasswd = None
        try:
            self.zbxurl = self.config.get("zbxCredentials", "url")
        except:
            self.zbxurl = "https://" + self.zbxhost + "/zabbix"

        self.defaults = {
                        "icon": self.zbxhost,
                        "interval": 60,
                        "notify": True,
                        "port": 10051,
                        "text_mode": True,
                        "wav": None,
                        "waw_player": "/usr/bin/mpv"
                        }
        self.config.read(self.config_file)

        # self.zbxicon = self.config.get("zbxOptions", "icon")
        # self.zbxinterval = int(self.config.get("zbxOptions", "interval"))
        # self.zbxnotify = bool(self.config.get("zbxOptions", "notify"))
        # self.zbxport = int(self.config.get("zbxOptions", "port"))
        # self.zbxtext_mode = bool(self.config.get("zbxOptions", "text_mode"))
        # self.zbxwav_player = self.config.get("zbxOptions", "wav_player")
        # self.zbxwav = self.config.get("zbxOptions", "wav")

        try:
            self.zbxicon = self.config.get("zbxOptions", "icon")
        except:
            self.zbxicon = self.defaults["icon"]
        try:
            self.zbxinterval = int(self.config.get("zbxOptions", "interval"))
        except:
            self.zbxinterval = self.defaults["interval"]
        try:
            self.zbxnotify = bool(self.config.get("zbxOptions", "notify"))
        except:
            self.zbxinterval = self.defaults["interval"]
        try:
            self.zbxport = int(self.config.get("zbxOptions", "port"))
        except:
            self.zbxport = self.defaults["port"]
        try:
            self.zbxtext_mode = bool(self.config.get("zbxOptions", "text_mode"))
        except:
            self.zbxtext_mode = self.defaults["text_mode"]
        try:
            self.zbxwav_player = self.config.get("zbxOptions", "wav_player")
        except:
            self.zbxwav_player = self.defaults["wav_player"]
        try:
            self.zbxwav = self.config.get("zbxOptions", "wav")
        except:
            self.zbxwav = self.defaults["wav"]

        print "-----------------"
        print "passwd", self.zbxpasswd
        print "user", self.zbxuser
        print "host", self.zbxhost
        print "url", self.zbxurl
        print
        print "icon", self.zbxicon
        print "interval", self.zbxinterval
        print "notify", self.zbxnotify
        print "port", self.zbxport
        print "text_mode", self.zbxtext_mode
        print "wav_player", self.zbxwav_player
        print "wav", self.zbxwav
        print "-----------------"

        self.zbx_ver = ''
        self.zbx_ping = 'ok'
        self.zbx_connected = 'ok'  # ok, port_is_down, not_logged, err_getting_data_1, err_getting_data_2
        self.zbx_status = self.zbx_last_status = 'ok'  # ok, >>current stat<<

        if self.zbxpasswd is None:
            if self.zbxtext_mode:
                print "Zabbix URL:", self.zbxurl
                print "Zabbix user:", self.zbxuser
                self.zbxpasswd = getpass.getpass(prompt="password: ")
            else:
                print self.zbxtext_mode
                md = MyDialog()
                mypass = [""]
                md.getPasswd(mypass, self.zbxurl)
                gtk.main()
                self.zbxpasswd = mypass[0]


class GtkMessages:
    def __init__(self):
        self.statusIcon = gtk.StatusIcon()
        self.statusIcon.connect('activate', self.show_current_stat)
        self.statusIcon.connect('popup-menu', self.on_right_click)
        zbx.status()
        if dc.zbx_status != "ok":
            self.set_icon(dc.icon_err)
        else:
            self.set_icon(dc.icon_ok)

    def set_icon(self, icon_file):
        self.statusIcon.set_from_file(icon_file)

    def message(self, data=None, type=gtk.BUTTONS_OK):
        msg = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, type, data)
        rval = msg.run()
        msg.destroy()
        return rval

    def make_menu(self, event_button, event_time, data=None):
        menu = gtk.Menu()
        reconnect_item = gtk.MenuItem("Reconnect to " + dc.zbx_server)
        close_item = gtk.MenuItem("Close applet " + dc.zbx_server)

        if dc.zbx_connected != 'ok' and dc.zbx_ping == 'ok':
            menu.append(reconnect_item)
            # add callback
            reconnect_item.connect_object("activate", self.reconnect_to_zbx_server, "reconnect to zbx server")
            reconnect_item.show()

        menu.append(close_item)
        # add callback
        close_item.connect_object("activate", self.close_app, "Really close?")
        close_item.show()

        # Popup the menu
        menu.popup(None, None, None, event_button, event_time)

    def show_current_stat(self, event):
        zbx.status()
        if dc.zbx_status != "ok":
            self.set_icon(dc.icon_err)
        else:
            self.set_icon(dc.icon_ok)
        self.message(dc.zbx_server + " current status is:\n\n" + dc.zbx_status)

    def on_right_click(self, data, event_button, event_time):
        self.make_menu(event_button, event_time)

    def reconnect_to_zbx_server(self, data=None):
        zbx.login()
        self.message('Logging to ' + dc.zbx_server + ":\n" + dc.zbx_connected)

    def close_app(self, data=None):
        syslog.syslog(dc.zbx_server + ": disconnected.")
        gtk.main_quit()
        # if self.message(data, gtk.BUTTONS_OK_CANCEL) == gtk.RESPONSE_OK:
        #     gtk.main_quit()


class TrayIcon:
    def __init__(self):
        self.__gmsg = GtkMessages()
        notify2.init("zab_mon")

    def check(self):
        zbx.status()
        syslog.syslog(dc.zbx_server + " status: " + dc.zbx_status)
        if dc.zbx_status != dc.zbx_last_status:
            dc.zbx_last_status = dc.zbx_status
            if dc.zbx_notify:
                n = notify2.Notification("Zabbix: " + dc.zbx_server, dc.zbx_status)
                if dc.zbx_status == "ok":
                    n.set_urgency(1)
                else:
                    n.set_urgency(2)
                    n.timeout = -1
                n.show()
            if dc.play_wav:
                try:
                    f = open('/dev/null', 'w')
                    if dc.zbx_status == 'ok':
                        call([dc.wav_player, dc.wav_ok], stdout=f, stderr=f)
                    else:
                        call([dc.wav_player, dc.wav_err], stdout=f, stderr=f)
                except:
                    pass
        if dc.zbx_status == 'ok':
            self.__gmsg.set_icon(dc.icon_ok)
        else:
            self.__gmsg.set_icon(dc.icon_err)
        return True

    def tray(self):
        gobject.timeout_add(dc.zbx_sleep, self.check)
        gtk.main()


class MyZbx:
    def __init__(self):
        self.zapi = ZabbixAPI(dc.zbxurl, timeout=5)
        self.zapi.session.verify = False
        self.login()

    def pingit(self):
        sock = socket(AF_INET, SOCK_STREAM)
        sock.settimeout(2)
        try:
            sock.connect((dc.zbxhost, dc.zbxport))
            dc.zbx_ping = 'ok'
        except:
            dc.zbx_ping = 'port is down'
        finally:
            sock.close()

    def login(self):
        self.pingit()
        if dc.zbx_ping == 'ok':
            try:
                self.zapi.login(dc.zbxuser, dc.zbxpasswd)
                dc.zbx_connected = 'ok'
                dc.zbx_ver = self.zapi.api_version().split('.')[0]
            except:
                dc.zbx_connected = 'not logged in'
            finally:
                print "Connect: " + dc.zbx_connected

    def status(self):
        self.pingit()
        if dc.zbx_ping != 'ok':
            dc.zbx_status = dc.zbx_ping
            return dc.zbx_status
        if dc.zbx_connected == 'not logged in':
            dc.zbx_status = dc.zbx_connected
            return dc.zbx_status
        dc.zbx_status = self.get_triggers(dc.zbx_ver)
        return dc.zbx_status

    def get_triggers(self, zbx_ver):
        try:
            if zbx_ver == "2":
                # Get a list of all issues (AKA tripped triggers)
                triggers = self.zapi.trigger.get(only_true=1,
                                             skipDependent=1,
                                             monitored=1,
                                             active=1,
                                             output='extend',
                                             expandDescription=1,
                                             expandData='host',
                                             )
                # Do another query to find out which issues are Unacknowledged
                unack_triggers = self.zapi.trigger.get(only_true=1,
                                                   skipDependent=1,
                                                   monitored=1,
                                                   active=1,
                                                   output='extend',
                                                   expandDescription=1,
                                                   expandData='host',
                                                   withLastEventUnacknowledged=1,
                                                   )
            elif zbx_ver == "3" or zbx_ver == "4":
                # Get a list of all issues (AKA tripped triggers)
                triggers = self.zapi.trigger.get(only_true=1,
                                             skipDependent=1,
                                             monitored=1,
                                             active=1,
                                             output='extend',
                                             expandDescription=1,
                                             selectHosts=['host'],
                                             )

                # Do another query to find out which issues are Unacknowledged
                unack_triggers = self.zapi.trigger.get(only_true=1,
                                                   skipDependent=1,
                                                   monitored=1,
                                                   active=1,
                                                   output='extend',
                                                   expandDescription=1,
                                                   selectHosts=['host'],
                                                   withLastEventUnacknowledged=1,
                                                   )
            else:
                return "Unknown ZBX ver. (" + zbx_ver + ")"
            dc.zbx_connected = 'ok'
        except:
            dc.zbx_connected = "Fetch data error."
            return dc.zbx_connected

        unack_trigger_ids = [t['triggerid'] for t in unack_triggers]
        for t in triggers:
            t['unacknowledged'] = True if t['triggerid'] in unack_trigger_ids \
                else False

        # Print a list containing only "tripped" triggers
        triggers.sort()
        rval = ''
        if zbx_ver == "2":
            for t in triggers:
                if int(t['value']) == 1 and t['unacknowledged']:
                    rval += ("{0} - {1} {2}".format(t['host'],
                                                t['description'],
                                                '(Unack)' if t['unacknowledged'] else '') + "\n\n"
                         )
        elif zbx_ver == "3" or zbx_ver == "4":
            for t in triggers:
                if int(t['value']) == 1 and t['unacknowledged']:
                    rval += ("{0} - {1} {2}".format(t['hosts'][0]['host'],
                                                    t['description'],
                                                    '(Unack)' if t['unacknowledged'] else '') + "\n\n"
                             )
        else:
            rval = "Unknown ZBX ver. (" + zbx_ver + ")"
        if rval == '':
            return 'ok'
        else:
            return rval


class myDaemon(Daemon):
    def run(self):
        syslog.openlog(script_name, syslog.LOG_PID | syslog.LOG_NDELAY, syslog.LOG_DAEMON)
        tc.tray()


def main(argv):
    global dc, zbx, tc
    # command - argv[1] (start if no args)

    def usage():
        print(globals()['__doc__'])
        sys.exit(2)

    if len(argv) == 1:
        command = "start"
    else:
        command = argv[1]

    if command in ("start", "stop"):
        pass
    else:
        print "Unknown command"
        sys.exit(2)

    dc = DataContainer(argv[0])
    print dc.script_name + ":", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())), "on", dc.zbxhost, command
    print dc.zbxuser, dc.zbxpasswd

    zbx = MyZbx()
    quit()
    tc = TrayIcon()

    daemon = myDaemon("/tmp/" + dc.script_name + "." + host + ".pid")
    if 'start' == command:
        daemon.start(script_name, host)
    elif 'stop' == command:
        daemon.stop(host)
    else:
        print "Unknown command"
        sys.exit(2)
    sys.exit(0)

if __name__ == '__main__':
    main(sys.argv)

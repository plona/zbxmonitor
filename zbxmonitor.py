#!/usr/bin/env python
# -*- coding: utf-8 -*-

from socket import *
from pyzabbix import *
from subprocess import call
from daemon import Daemon
import time
import os
import getpass
import gobject
import notify2
import syslog
import ConfigParser
import warnings
import ast
from dialog_nix import *


class GlobVars:
    def __init__(self, script_name):
        self.script_full_path = os.path.abspath(script_name)
        self.script_dir = os.path.dirname(self.script_full_path)
        self.script_name = os.path.basename(self.script_full_path)
        self.script_short_name = os.path.splitext(self.script_full_path)[0]

        self.config_file = self.script_short_name + ".config"
        self.config = ConfigParser.ConfigParser()

        self.config.read(self.config_file)
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

        self.tmp_dir = self.script_dir + "/" + "tmp"
        try:
            os.mkdir(self.tmp_dir)
        except:
            pass
        self.zbxlog = self.tmp_dir + "/" + self.zbxhost + ".log"

        self.defaults = {
                        "interval": 30 * 1000,
                        "notify": True,
                        "port": 10051,
                        "text_mode": False,
                        "ignore_warn": False,
                        "icon": self.zbxhost,
                        "wav": None,
                        "wav_player": "/usr/bin/mpv",
                        "ackOnly": True,
                        "exclTg": [],
                        "inclTg": []
                        }
        try:
            self.zbxinterval = int(self.config.get("zbxOptions", "interval")) * 1000
        except:
            self.zbxinterval = self.defaults["interval"]
        try:
            self.zbxnotify = bool(self.config.get("zbxOptions", "notify"))
        except:
            self.zbxnotify = self.defaults["notify"]
        try:
            self.zbxport = int(self.config.get("zbxOptions", "port"))
        except:
            self.zbxport = self.defaults["port"]
        try:
            self.text_mode = bool(self.config.get("zbxOptions", "text_mode"))
        except:
            self.text_mode = self.defaults["text_mode"]
        try:
            self.zbxignore_warn = bool(self.config.get("zbxOptions", "ignore_warn"))
        except:
            self.zbxignore_warn = self.defaults["ignore_warn"]
        try:
            self.zbxicon = self.script_dir + "/icons/" + self.config.get("zbxOptions", "icon")
        except:
            self.zbxicon = self.script_dir + "/icons/" + self.defaults["icon"]
        try:
            self.zbxwav_player = self.config.get("zbxOptions", "wav_player")
        except:
            self.zbxwav_player = self.defaults["wav_player"]
        try:
            self.zbxwav = self.script_dir + "/sounds/" + self.config.get("zbxOptions", "wav")
        except:
            self.zbxwav = self.defaults["wav"]
        try:
            self.zbxackOnly = bool(self.config.get("zbxOptions", "ackOnly"))
        except:
            self.zbxackOnly = self.defaults["ackOnly"]
        try:
            self.zbxExclTg = ast.literal_eval(self.config.get("zbxOptions", "exclTg"))
        except:
            self.zbxExclTg = self.defaults["exclTg"]
        if len(self.zbxExclTg) == 0:
            try:
                self.zbxInclTg = ast.literal_eval(self.config.get("zbxOptions", "inclTg"))
            except:
                self.zbxInclTg = self.defaults["inclTg"]
        else:
            self.zbxInclTg = self.defaults["inclTg"]

        self.zbx_ping = 'ok'
        self.zbx_connected = 'ok'  # ok, port_is_down, not_logged, err_getting_data_1, err_getting_data_2
        self.zbx_status = self.zbx_last_status = 'ok'  # ok, >>current stat<<
        self.zbx_filter = (True if len(self.zbxExclTg) or len(self.zbxInclTg) else False)

        if self.zbxpasswd is None:
            if self.text_mode:
                print "Zabbix URL:", self.zbxurl
                print "Zabbix user:", self.zbxuser
                self.zbxpasswd = getpass.getpass(prompt="password: ")
            else:
                md = MyDialog()
                mypass = [""]
                md.getPasswd(mypass, self.zbxurl)
                gtk.main()
                self.zbxpasswd = mypass[0]


class TrayTxt:
    def __init__(self, command):
        zbx.status()
        self.flog = open(gv.zbxlog, "a")
        self.flog.write("\n" + gv.script_name + ": ")
        self.flog.write(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())))
        self.flog.write(" on " + gv.zbxhost + " " + command + "\n\n")
        self.flog.write(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())) + " ")
        self.flog.write(gv.zbx_status + "\n")
        self.flog.flush()

    def check(self):
        zbx.status()
        syslog.syslog(gv.zbxhost + " status (txt): " + gv.zbx_status)
        if gv.zbx_status != gv.zbx_last_status:
            gv.zbx_last_status = gv.zbx_status
            self.flog.write(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())) + " ")
            self.flog.write(gv.zbx_status + "\n")
            self.flog.flush()
        return gv.zbx_status

    def tray(self):
        gobject.timeout_add(gv.zbxinterval, self.check)
        gobject.MainLoop().run()


class GtkMessages:
    def __init__(self):
        self.statusIcon = gtk.StatusIcon()
        self.statusIcon.connect('activate', self.show_current_stat)
        self.statusIcon.connect('popup-menu', self.on_right_click)
        zbx.status("filtered")
        if gv.zbx_status != "ok":
            self.set_icon(gv.zbxicon + "-err.png")
        else:
            self.set_icon(gv.zbxicon + "-ok.png")

    def set_icon(self, icon_file):
        self.statusIcon.set_from_file(icon_file)

    def message(self, data=None, type=gtk.BUTTONS_OK):
        msg = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, type, data)
        rval = msg.run()
        msg.destroy()
        return rval

    def make_menu(self, event_button, event_time, data=None):
        menu = gtk.Menu()
        reconnect_item = gtk.MenuItem("Reconnect to " + gv.zbxhost)
        close_item = gtk.MenuItem("Close applet " + gv.zbxhost)
        show_unfiltered_item = gtk.MenuItem("Show unfiltered triggers " + gv.zbxhost)
        show_all_item = gtk.MenuItem("Show all triggers " + gv.zbxhost)

        if gv.zbx_connected != 'ok' and gv.zbx_ping == 'ok':
            menu.append(reconnect_item)
            reconnect_item.connect_object("activate", self.reconnect_to_zbxhost, "reconnect to zbx server")
            reconnect_item.show()

        menu.append(close_item)
        # add callback
        close_item.connect_object("activate", self.close_app, "Really close?")
        close_item.show()

        if gv.zbx_connected == 'ok':
            menu.append(show_all_item)
            show_all_item.connect_object("activate", self.show_all_triggers, "show all triggers")
            show_all_item.show()
            if gv.zbx_filter:
                menu.append(show_unfiltered_item)
                show_unfiltered_item.connect_object("activate", self.show_unfiltered_triggers, "show unfiltered triggers")
                show_unfiltered_item.show()

        # Popup the menu
        menu.popup(None, None, None, event_button, event_time)

    def show_current_stat(self, event):
        zbx.status("filtered")
        if gv.zbx_status != "ok":
            self.set_icon(gv.zbxicon + "-err.png")
        else:
            self.set_icon(gv.zbxicon + "-ok.png")
        m = (" filtered triggers:\n\n" if gv.zbx_filter else " current status:\n\n")
        # self.message(gv.zbxhost + " filtered triggers:\n\n" + gv.zbx_status)
        self.message(gv.zbxhost + m + gv.zbx_status)

    def on_right_click(self, data, event_button, event_time):
        self.make_menu(event_button, event_time)

    def reconnect_to_zbxhost(self, data=None):
        zbx.login()
        self.message('Logging to ' + gv.zbxhost + ":\n" + gv.zbx_connected)

    def show_unfiltered_triggers(self, data=None):
        zbx.status("unfiltered")
        self.message(gv.zbxhost + " unfiltered triggers:\n\n" + gv.zbx_status)

    def show_all_triggers(self, data=None):
        zbx.status("all")
        self.message(gv.zbxhost + " all triggers:\n\n" + gv.zbx_status)

    def close_app(self, data=None):
        syslog.syslog(gv.zbxhost + ": disconnected.")
        gtk.main_quit()
        # if self.message(data, gtk.BUTTONS_OK_CANCEL) == gtk.RESPONSE_OK:
        #     gtk.main_quit()


class TrayIcon:
    def __init__(self):
        self.__gmsg = GtkMessages()
        notify2.init("zab_mon")

    def check(self):
        zbx.status("filtered")
        syslog.syslog(gv.zbxhost + " status (GUI): " + gv.zbx_status)
        if gv.zbx_status != gv.zbx_last_status:
            gv.zbx_last_status = gv.zbx_status
            if gv.zbxnotify:
                n = notify2.Notification("Zabbix: " + gv.zbxhost, gv.zbx_status)
                if gv.zbx_status == "ok":
                    n.set_urgency(1)
                else:
                    n.set_urgency(2)
                    n.timeout = -1
                n.show()
            if gv.zbxwav is not None:
                try:
                    f = open('/dev/null', 'w')
                    if gv.zbx_status == 'ok':
                        call([gv.zbxwav_player, gv.zbxwav + "-ok.wav"], stdout=f, stderr=f)
                    else:
                        call([gv.zbxwav_player, gv.zbxwav + "-err.wav"], stdout=f, stderr=f)
                except:
                    pass
        if gv.zbx_status == 'ok':
            self.__gmsg.set_icon(gv.zbxicon + "-ok.png")
        else:
            self.__gmsg.set_icon(gv.zbxicon + "-err.png")
        return True

    def tray(self):
        gobject.timeout_add(gv.zbxinterval, self.check)
        gtk.main()


class MyZbx:
    def __init__(self):
        self.zapi = ZabbixAPI(gv.zbxurl, timeout=5)
        self.zapi.session.verify = False
        if gv.zbxignore_warn:
            warnings.filterwarnings("ignore")
        self.login()

    def pingit(self):
        sock = socket(AF_INET, SOCK_STREAM)
        sock.settimeout(2)
        try:
            sock.connect((gv.zbxhost, gv.zbxport))
            gv.zbx_ping = 'ok'
        except:
            gv.zbx_ping = 'port is down'
        finally:
            sock.close()

    def login(self):
        self.pingit()
        if gv.zbx_ping == 'ok':
            try:
                self.zapi.login(gv.zbxuser, gv.zbxpasswd)
                gv.zbx_connected = 'ok'
            except:
                gv.zbx_connected = 'not logged in'
            finally:
                print "Connect: " + gv.zbx_connected

    def status(self, mode="all"):
        self.pingit()
        if gv.zbx_ping != 'ok':
            gv.zbx_status = gv.zbx_ping
            return gv.zbx_status
        if gv.zbx_connected == 'not logged in':
            gv.zbx_status = gv.zbx_connected
            return gv.zbx_status
        gv.zbx_status = self.get_triggers(mode)
        return gv.zbx_status

    def add_to_rval(self, t, rval, extmode=False):
        if int(t["value"]) == 1:
            if extmode:
                rval[0] += ("{0} - {1} {2}".format(t['hosts'][0]['host'], t['description'], '(Unack)' if t['unacknowledged'] else '') + "\n\n")
                return
            if gv.zbxackOnly:
                if t['unacknowledged']:
                    rval[0] += ("{0} - {1} {2}".format(t['hosts'][0]['host'], t['description'], '(Unack)' if t['unacknowledged'] else '') + "\n\n")
            else:
                rval[0] += ("{0} - {1} {2}".format(t['hosts'][0]['host'], t['description'], '(Unack)' if t['unacknowledged'] else '') + "\n\n")
        return

    def get_triggers(self, mode="all"):
        try:
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
            gv.zbx_connected = 'ok'
        except:
            gv.zbx_connected = "Fetch data error."
            return gv.zbx_connected

        unack_trigger_ids = [t['triggerid'] for t in unack_triggers]
        for t in triggers:
            t['unacknowledged'] = True if t['triggerid'] in unack_trigger_ids else False

        # Print a list containing only "tripped" triggers
        triggers.sort()
        rval = ['']
        for t in triggers:
            # print "description/ack:", t['description'], "|", t['unacknowledged']
            if mode == "filtered":
                if len(gv.zbxExclTg) > 0:
                    for flt in gv.zbxExclTg:
                        # print "flt/description/ack:", flt, "|", t['description'], "|", t['unacknowledged']
                        if flt in t['description']:
                            continue
                        else:
                            self.add_to_rval(t, rval)
                elif len(gv.zbxInclTg) > 0:
                    for flt in gv.zbxInclTg:
                        # print "flt/description/ack:", flt, "|", t['description'], "|", t['unacknowledged']
                        if flt in t['description']:
                            self.add_to_rval(t, rval)
                        else:
                            continue
                else:
                    self.add_to_rval(t, rval)
            elif mode == "unfiltered":
                self.add_to_rval(t, rval)
            elif mode == "all":
                self.add_to_rval(t, rval, True)
            else:
                return "Unknown mode: " + mode

        if rval[0] == '':
            return 'ok'
        else:
            return rval[0]


class myDaemon(Daemon):
    def run(self):
        syslog.openlog(gv.script_name, syslog.LOG_PID | syslog.LOG_NDELAY, syslog.LOG_DAEMON)
        tc.tray()


def main(argv):
    global gv, zbx, tc

    if len(argv) == 1:
        command = "start"
    else:
        command = argv[1]

    if command in ("start", "stop"):
        pass
    else:
        print "Unknown command"
        sys.exit(2)

    gv = GlobVars(argv[0])
    print gv.script_name + ":", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())), "on", gv.zbxhost, command

    if "start" == command:
        zbx = MyZbx()
        if (gv.text_mode):
            tc = TrayTxt(command)
        else:
            tc = TrayIcon()

    f = gv.tmp_dir + "/" + gv.zbxhost
    pidfile = f + ".pid"
    # stdoutfile = f  + ".out"
    # stderrfile = f + ".log"
    # daemon = myDaemon(pidfile, stderr=stderrfile, stdout=stdoutfile)
    daemon = myDaemon(pidfile)
    if 'start' == command:
        daemon.start(gv.script_name, gv.zbxhost)
    elif 'stop' == command:
        daemon.stop(gv.zbxhost)
    else:
        print "Unknown command"
        sys.exit(2)
    sys.exit(0)

if __name__ == '__main__':
    main(sys.argv)

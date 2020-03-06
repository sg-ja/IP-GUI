"""
IP-GUI:

    Created By:         Geiger Sven
    Description:        Change your IP simply over GUI
    Info:               Run as Admin! Makes it easier.
    Requirements:
                        * PySimpleGUIQT
                        * WMI
                        * pywin32
                        * psutil
    ToDo-List:
        # Only one open Window
        # Make it Secure
        # Save config ?
"""
# #################################################################################################################### #
# Imports
# ---------

# Standard
import sys
import os
import ctypes
import socket
import time
from pathlib import Path
from tempfile import gettempdir, NamedTemporaryFile
from glob import glob

# External
import psutil
import wmi
import win32api
import PySimpleGUIQt as sg


# #################################################################################################################### #
# Variables
# ---------

w = wmi.WMI()

window = None
tray = None

adapters = []
values = []

name = "ip_python_program"
path_ = str(Path(gettempdir(), f"{name}*"))
header = """\
-------------------
Created by IP.exe
This file only exists if the file is running or something went wrong
--------------------------------------------------------------------
"""


# #################################################################################################################### #
# Classes
# ---------


class Message:
    info = sg.SYSTEM_TRAY_MESSAGE_ICON_INFORMATION
    warning = sg.SYSTEM_TRAY_MESSAGE_ICON_WARNING
    critical = sg.SYSTEM_TRAY_MESSAGE_ICON_CRITICAL
    no_icon = sg.SYSTEM_TRAY_MESSAGE_ICON_NOICON


# #################################################################################################################### #
# Functions
# ---------

# --------------------------------
# Utility
# --------------------------------


def is_admin() -> bool:
    try:
        out = (os.getuid() == 0)
    except AttributeError:
        out = ctypes.windll.shell32.IsUserAnAdmin() != 0

    return out


def gain_admin():
    # Gains admin
    # Source: http://blog.pythonaro.com/2011/09/python-wmi-services-and-uac.html
    win32api.ShellExecute(
        None,
        "runas",
        sys.executable,
        __file__,
        None,
        1
    )


def valid_ip(ip: str) -> bool:
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False


def get_adapters(enable=True) -> list:
    return w.Win32_NetworkAdapterConfiguration(IPEnabled=enable)


def check_for_process():
    return True if glob(path_) else False


def process_attempt():
    return len(glob(path_)) > 1


# --------------------------------
# GUI
# --------------------------------


def update_text(app: sg.Window, i: int, with_dhcp=True):
    try:
        if with_dhcp:
            app["DHCP"].update(value=values[i].DHCPEnabled)

        app["IP"].update(
            values[i].IPAddress[0],
            disabled=app["DHCP"].get(),
        )
        app["SUB"].update(
            values[i].IPSubnet[0],
            disabled=app["DHCP"].get(),
        )
        app["GATE"].update(
            values[i].DefaultIPGateway[0] if values[i].DefaultIPGateway else "",
            disabled=app["DHCP"].get(),
        )
    except IndexError:
        pass


def update_list(app: sg.Window, index: int = 0):

    if index > len(adapters):
        index = 0

    init_adapters()
    app["DROP"].update(values=adapters, set_to_index=index)
    app.refresh()
    update_text(app, index)


# --------------------------------
# System Tray
# --------------------------------


def message(sys_tray: sg.SystemTray, title="IP", text="", kind="info"):
    sys_tray.ShowMessage(
        title,
        text,
        filename="favicon.png",
        messageicon=getattr(Message, kind) if kind in ["info", "warning", "critical", "no_icon"] else Message().no_icon,
        time=1000
    )


# --------------------------------
# Init
# --------------------------------


def init_adapters():
    global adapters
    global values

    values = get_adapters()
    adapters = [x.description for x in values]


def init_tray():
    global tray

    menu = [
        "BLANK",
        ["&Open", "---", "&Close", ]
    ]
    try:
        tray = sg.SystemTray(menu=menu, tooltip="IP", data="favicon.png")
    except TypeError:
        tray = sg.SystemTray(menu=menu, tooltip="IP", filename="favicon.png")


def init_gui():
    global window
    global adapters
    global values

    sg.theme("Reddit")

    layout_frame = [
        [sg.Checkbox("DHCP", key="DHCP", enable_events=True)],
        [sg.Text("")],
        [sg.Text("IP: ", size=(15, 1)), sg.Input(size=(15, 1), key="IP")],
        [sg.Text("Sub: ", size=(15, 1)), sg.Input(size=(15, 1), key="SUB")],
        [sg.Text("Gateway: ", size=(15, 1)), sg.Input(size=(15, 1), key="GATE")],
    ]

    layout = [
        [
            sg.Combo(adapters, enable_events=True, key="DROP", readonly=True),
        ],
        [
            sg.Frame(
                "Network",
                layout_frame,
                ),
        ],
        [
            sg.Button("Update", size=(15, 1), key="UPDATE")
        ]
    ]

    window = sg.Window("IP", layout, icon="favicon.png")

    window.read(1)
    update_text(window, 0)


# --------------------------------
# Main
# --------------------------------


def mainloop():
    global window
    global tray
    global adapters
    global values

    temp_ = NamedTemporaryFile(prefix=name)

    init_adapters()
    init_gui()
    init_tray()

    check_time = time.time()
    delta = 30                  # 30 seconds

    while True:
        event, value = window.read(1)
        key = tray.read(1)

        if key == "Close":
            if window.NumOpenWindows:
                window.close()
            break

        if event == "DROP":
            index = adapters.index(value.get("DROP"))
            update_text(window, index)

        elif event == "DHCP":
            index = adapters.index(value.get("DROP"))
            update_text(window, index, False)

        elif event == "UPDATE":

            index = adapters.index(value.get("DROP"))
            adapter = values[index]

            if window["DHCP"].get():
                fb = adapter.EnableDHCP()

                if fb[0]:
                    message(
                        tray,
                        text=f"Something went wrong configuring  '{adapter.description}'",
                        kind="warning"
                    )

                else:
                    message(tray, text=f"Change of {adapter.description} successful", kind="info")

            else:

                ip = window["IP"].get()
                sub = window["SUB"].get()
                gate = window["GATE"].get()

                index = 0
                for index, ele in enumerate([ip, sub, gate]):
                    if not valid_ip(ele):
                        break

                if index == 2:
                    fb = adapter.EnableStatic(IPAddress=[ip], SubnetMask=[sub])
                    if gate:
                        fb = adapter.SetGateways(DefaultIPGateway=[gate])

                    if fb[0]:
                        message(
                            tray,
                            text=f"Something went wrong configuring  '{adapter.description}'",
                            kind="warning"
                            )

                    else:
                        message(tray, text=f"Change of {adapter.description} successful", kind="info")

                else:
                    message(
                        tray,
                        text=f"Please enter a valid IP!",
                        kind="warning"
                    )

            update_list(window, index)
            check_time = time.time()

        if key in ["Open", "__DOUBLE_CLICKED__", "__ACTIVATED__"]:
            if not window.QT_QMainWindow.isVisible():
                init_adapters()
                init_gui()

            window.BringToFront()

        if window.QT_QMainWindow.isMinimized():
            window.maximize()
            window.close()

        if time.time() - check_time >= delta:
            if event:
                check_time = time.time()
                update_list(window, adapters.index(value.get("DROP")))

    temp_.close()
    sys.exit()


def main():
    if check_for_process():
        sys.exit()

    # Opens new Window if you aren't admin
    if is_admin():
        mainloop()
    else:
        gain_admin()


# #################################################################################################################### #
# Main
# ---------

if __name__ == "__main__":
    main()



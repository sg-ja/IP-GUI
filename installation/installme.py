from pathlib import Path
import os

# Programs
python = "python"
nsis = "C:\\Program Files (x86)\\NSIS\\makensis.exe"

# Paths
INSTALL = Path().absolute()
PROJECT = INSTALL.parent
EXE = Path(PROJECT, "ip_bin")
EXE_ADD = Path(PROJECT, "ip_bin", "x64")
INSTALLING_FOLDER = Path("C:\\", "IP")


# Files
batch_file = "installme.bat"
setup_file = "setup.nsi"

try:
    with open(Path(PROJECT,"version.txt"), "r") as f:
        version = f.read()
except FileNotFoundError:
    version = ""

icons = Path(INSTALL, "favicon.ico")
file = Path(PROJECT, "ip-gui", "ip.py")
name = f"ip_{version}.exe" if version else "ip.exe"

batch = f"""\
@echo off

:Install
::Create EXE
{python} -m PyInstaller {file} --noconsole --onefile --name {name} --icon {icons} --dist {EXE} --workpath {EXE_ADD} --specpath {EXE_ADD}
copy favicon.png {EXE}\\favicon.png

"{nsis}" {setup_file}

"""

nsi = f"""\
!define APPNAME "{name}"

Name "IP"

OutFile "{Path(EXE, "setup_{}".format(name))}"
InstallDir {INSTALLING_FOLDER}
Page instfiles

Section ""
SetOutPath $INSTDIR

IfFileExists uninstall.exe uninstall
uninstall:
ExecWait "uninstall.exe"

File {Path(EXE, name)}
File {Path(EXE, "favicon.png")}

writeUninstaller uninstall.exe
CreateShortcut "$DESKTOP\\ip.lnk" "{Path(INSTALLING_FOLDER, name)}"

SetAutoClose true

SectionEnd

Section "uninstall"

delete $INSTDIR\\uninstall.exe
delete $INSTDIR\\{name}
delete  $INSTDIR\\favicon.png
delete $DESKTOP\\ip.lnk
RMDir $INSTDIR

SetAutoClose true

SectionEnd
"""


with open(batch_file, "w") as f:
    f.write(batch)
with open(setup_file, "w") as f:
    f.write(nsi)

os.system(f'call {batch_file}')

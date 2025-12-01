#!/usr/bin/env python3
from os import path
import sys
import os
import time
import threading
here = path.abspath(path.dirname(__file__))
os.chdir(here)
sys.path.append('./sensorhat')
from version import __version__
print("Robot Hat Python Library v%s" % __version__)
avaiable_options = ["--no-dep", "--only-lib", "--no-build-isolation"]
options = []
if len(sys.argv) > 1:
    options = list.copy(sys.argv[1:])
def warn(msg, end='\n', file=sys.stdout, flush=False):
    print(f'\033[0;33m{msg}\033[0m', end=end, file=file, flush=flush)
def error(msg, end='\n', file=sys.stdout, flush=False):
    print(f'\033[0;31m{msg}\033[0m', end=end, file=file, flush=flush)
if os.geteuid() != 0:
    warn("Script must be run as root. Try \"sudo python3 install.py\".")
    sys.exit(1)
def run_command(cmd=""):
    import subprocess
    p = subprocess.Popen(cmd,
                         shell=True,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    result = p.stdout.read().decode('utf-8')
    status = p.poll()
    return status, result
errors = []
at_work_tip_sw = False
def working_tip():
    char = ['/', '-', '\\', '|']
    i = 0
    global at_work_tip_sw
    while at_work_tip_sw:
        i = (i + 1) % 4
        sys.stdout.write('\033[?25l')  
        sys.stdout.write('%s\033[1D' % char[i])
        sys.stdout.flush()
        time.sleep(0.5)
    sys.stdout.write(' \033[1D')
    sys.stdout.write('\033[?25h')  
    sys.stdout.flush()
def do(msg="", cmd=""):
    print(" - %s ... " % (msg), end='', flush=True)
    global at_work_tip_sw
    at_work_tip_sw = True
    _thread = threading.Thread(target=working_tip)
    _thread.daemon = True
    _thread.start()
    status, result = run_command(cmd)
    at_work_tip_sw = False
    _thread.join()  
    if status == 0 or status == None or result == "":
        print('Done')
    else:
        print('Error')
        errors.append("%s error:\n  Status:%s\n  Error:%s" %
                      (msg, status, result))
def check_raspbain_version():
    _, result = run_command("cat /etc/debian_version|awk -F. '{print $1}'")
    return int(result.strip())
def check_os_bit():
    '''
    # import platform
    # machine_type = platform.machine() 
    latest bullseye uses a 64-bit kernel
    This method is no longer applicable, the latest raspbian will uses 64-bit kernel 
    (kernel 6.1.x) by default, "uname -m" shows "aarch64", 
    but the system is still 32-bit.
    '''
    _, os_bit = run_command("getconf LONG_BIT")
    return int(os_bit)
raspbain_version = check_raspbain_version()
os_bit = check_os_bit()
APT_INSTALL_LIST = [
    'raspi-config',
    "i2c-tools",
    "espeak",
    'libsdl2-dev',
    'libsdl2-mixer-dev',
    'portaudio19-dev',  
    'sox',
]
if raspbain_version >= 12 and os_bit == 64:
    APT_INSTALL_LIST.append("libttspico-utils")  
PIP_INSTALL_LIST = [
    'smbus2',
    'gpiozero',
    'pyaudio',
    'spidev',
    'pyserial',
    'pillow',
    "'pygame>=2.1.2'",
]
def install():
    _is_bsps = ''
    status, _ = run_command("pip3 help install|grep break-system-packages")
    if status == 0: 
        _is_bsps = "--break-system-packages"
    if "--only-lib" not in options:
        if "--no-dep" not in options:
            print("Install dependencies with apt-get:")
            do(msg="update apt-get", cmd='apt-get update')
            for dep in APT_INSTALL_LIST:
                do(msg=f"install {dep}", cmd=f'apt-get install {dep} -y')
            if 'libttspico-utils' not in APT_INSTALL_LIST:
                _pool = 'http://ftp.debian.org/debian/pool/non-free/s/svox/'
                if raspbain_version >= 12:
                    libttspico= 'libttspico0t64_1.0+git20130326-14.1_armhf.deb'
                    libttspico_utils = 'libttspico-utils_1.0+git20130326-14.1_armhf.deb'
                elif raspbain_version < 12:
                    libttspico = 'libttspico0_1.0+git20130326-11_armhf.deb'
                    libttspico_utils = 'libttspico-utils_1.0+git20130326-11_armhf.deb'
                do(msg="install pico2wave",
                    cmd=f'wget {_pool}{libttspico}' +
                    f' &&wget {_pool}{libttspico_utils}' +
                    f' && apt-get install -f ./{libttspico} ./{libttspico_utils} -y'
                    )
            print("Install dependencies with pip3:")
            if _is_bsps != '':
                _is_bsps = "--break-system-packages"
                print(
                    "\033[38;5;8m pip3 install with --break-system-packages\033[0m"
                )
            do(msg="update pip3", cmd=f'sudo apt-get upgrade -y python3-pip')
            for dep in PIP_INSTALL_LIST:
                do(msg=f"install {dep}",
                    cmd=f'pip3 install {dep} {_is_bsps}')
        print("Setup interfaces")
        do(msg="turn on I2C", cmd='raspi-config nonint do_i2c 0')
        do(msg="turn on SPI", cmd='raspi-config nonint do_spi 0')
        print("Copy dtoverlay")
        DEFAULT_OVERLAYS_PATH = "/boot/firmware/overlays/"
        LEGACY_OVERLAYS_PATH = "/boot/overlays/"
        _overlays_path = None
        if os.path.exists(DEFAULT_OVERLAYS_PATH):
            _overlays_path = DEFAULT_OVERLAYS_PATH
        elif os.path.exists(LEGACY_OVERLAYS_PATH):
            _overlays_path = LEGACY_OVERLAYS_PATH
        else:
            _overlays_path = None
        if _overlays_path is not None:
            do(msg="copy dtoverlay",
            cmd=f'cp ./dtoverlays/* {_overlays_path}')
    _if_build_isolation = ""
    if "--no-build-isolation" in options:
        _if_build_isolation = "--no-build-isolation"
    do(msg=f"install sensorhat package {_if_build_isolation}",
       cmd=f'pip3 install ./ {_is_bsps} {_if_build_isolation}')
    if len(errors) == 0:
        print("Finished")
    else:
        print("\n\nError happened in install process:")
        for error in errors:
            print(error)
        print(
            "Try to fix it yourself"
        )
if __name__ == "__main__":
    try:
        install()
    except KeyboardInterrupt:
        if len(errors) > 0:
            print("\n\nError happened in install process:")
            for error in errors:
                print(error)
            print(
                "Try to fix it yourself"
            )
        print("\n\nCanceled.")
    finally:
        sys.stdout.write(' \033[1D')
        sys.stdout.write('\033[?25h') 
        sys.stdout.flush()

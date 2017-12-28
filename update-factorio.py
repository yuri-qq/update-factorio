#!/usr/bin/env python3

import requests
import subprocess
import re
import os
import tarfile
import shutil

FACTORIO_PATH = "/opt/factorio"
USER = "factorio"
GROUP = "factorio"

PACKAGE = "core-linux_headless64"
DOWNLOAD_URL = "https://factorio.com/get-download/"
UPDATER_URL = "https://updater.factorio.com"
FACTORIO_BIN = FACTORIO_PATH + "/bin/x64/factorio"
TMP_DIR = FACTORIO_PATH + "/tmp"
TMP_UPDATE = TMP_DIR + "/update.zip"
os.makedirs(FACTORIO_PATH, exist_ok=True)
os.makedirs(TMP_DIR, exist_ok=True)

version_pattern = re.compile(" (\d+\.\d+\.\d+) ")

def main():
    if os.path.exists(FACTORIO_BIN):
        update_to_latest()
    else:
        install_factorio(FACTORIO_PATH)
    shutil.rmtree(TMP_DIR)

def get_current_version():
    return version_pattern.search(subprocess.Popen([FACTORIO_BIN, "--version"], stdout=subprocess.PIPE, universal_newlines=True).communicate()[0]).group(1)

def get_latest_version():
    updates = requests.get(UPDATER_URL + "/get-available-versions", params={
        "apiVersion": 2
    }).json()[PACKAGE]

    latest_version = [0, 0, 0]
    for update in updates:
        if "to" in update:
            version = [int(num) for num in update["to"].split(".")]
            if version[0] == latest_version[0]:
                if version[1] == latest_version[1]:
                    if version[2] > latest_version[2]: latest_version[2] = version[2]
                elif version[1] > latest_version[1]:
                    latest_version[1] = version[1]
                    latest_version[2] = version[2]
            elif version[0] > latest_version[0]:
                latest_version[0] = version[0]
                latest_version[1] = version[1]
                latest_version[2] = version[2]

    return ".".join(str(num) for num in latest_version)

def install_factorio(install_dir):
    archive = download_file(DOWNLOAD_URL + get_latest_version() + "/headless/linux64", TMP_DIR + "/linux64")
    extract_file(archive, TMP_DIR)
    for item in os.listdir(TMP_DIR + "/factorio"):
        destination = install_dir + "/" + item
        if os.path.exists(destination): shutil.rmtree(destination)
        shutil.move(TMP_DIR + "/factorio/" + item, install_dir + "/" + item)
    subprocess.Popen(["chown", "-R", USER + ":" + GROUP, install_dir]).wait()

def update_to_latest():
    update = download_next_update(get_current_version())
    if update:
        apply_update(update)
        os.remove(TMP_UPDATE)
        update_to_latest()

def download_next_update(version):
    updates = requests.get(UPDATER_URL + "/get-available-versions", params={
        "apiVersion": 2
    }).json()[PACKAGE]

    if get_latest_version() != version:
        for update in updates:
            if "from" in update and update["from"] == version:
                download_url = requests.get(UPDATER_URL + "/get-download-link", params={
                    "apiVersion": 2,
                    "package": PACKAGE,
                    "from": version,
                    "to": update["to"]
                }).json()[0]
                return download_file(download_url, TMP_UPDATE)
    return False

def download_file(download_url, path):
    download_stream = requests.get(download_url, stream=True)
    with open(path, "wb") as file:
        for chunk in download_stream.iter_content(chunk_size=8192):
            file.write(chunk)
    return path

def extract_file(file, path):
    tar = tarfile.open(file)
    tar.extractall(path=path)
    tar.close()

def apply_update(path):
    subprocess.Popen([FACTORIO_BIN, "--apply-update", path]).wait()

if __name__ == "__main__":
    main()

import os
import json
from subprocess import getoutput
import dotenv
import datetime
import netifaces
import ipaddress
import socket

def dockerComposeHash(repoPath):
    os.chdir(repoPath)

    docker_raw = getoutput("docker-compose ps")
    docker_lines = docker_raw.split("\n")
    docker_services = {}

    # remove first 1 line (headers)
    docker_lines.pop(0)

    docker_data = []

    for line in docker_lines:
        if len(line) > 1:

            items = line.split()
            docker_sha = getoutput("docker inspect --format='{{.Image}}' " + items[0])
            docker_name = items[0]

            docker_item = {
                "type": "docker",
                "values": {
                    "name": docker_name,
                    "image": docker_sha,
                },
            }
            docker_data.append(docker_item)

    return docker_data


def gitHash(repoPath):
    os.chdir(repoPath)

    git_raw = getoutput("git rev-parse HEAD")
    git_branch = getoutput("git branch --show-current")
    git_commit = getoutput("git rev-parse HEAD")
    git_status = getoutput("git status --porcelain")

    if git_status == "":
         git_clean = True
    else:
        git_clean = False
    
    git_repository = getoutput("git remote get-url origin")
    # Sanitize password if any
    if "@" in git_repository and "https" in git_repository:
        git_repository = "https://" + git_repository.split("@",2)[1]        

    gitHash = {
        "type": "git",
        "values": {
            "repository": git_repository,
            "branch": git_branch,
            "commit": git_commit,
            "clean": git_clean,
        },
    }

    return gitHash


def build_recorder_id_json():

    f = open(INTEGRITY_PREPROCESSOR_CONFIG_PATH)
    recorder_configs = json.load(f)

    integrity = {"recorderMetadata": []}

    for key in recorder_configs:
        recorder_config = recorder_configs[key]

        recorder = {"service": key, "info": []}
        recorder_type = recorder_config["type"]
        if "dockercompose" in recorder_config and recorder_config["dockercompose"]:
            recorder["info"] = dockerComposeHash(recorder_config["path"])
        if "git" in recorder_config and recorder_config["git"]:
            recorder["info"].append(gitHash(recorder_config["path"]))

        integrity["recorderMetadata"].append(recorder)

    # Record ip addreses

    net = []    

    for interface in netifaces.interfaces():

        if netifaces.AF_INET in  netifaces.ifaddresses(interface):
            for link in netifaces.ifaddresses(interface)[netifaces.AF_INET]:
                if not ipaddress.ip_address(link['addr']).is_private:
                    item = {
                        "type": "ip",
                        "values": {
                            "if": interface,
                            "address": link['addr'] 
                        }
                    }
                    net.append(item)
        if netifaces.AF_INET6 in  netifaces.ifaddresses(interface):
            for link in netifaces.ifaddresses(interface)[netifaces.AF_INET6]:
                if not ipaddress.ip_address(link['addr']).is_private:
                    item = {
                        "type": "ip",
                        "values": {
                            "if": interface,
                            "address": link['addr'] 
                        }
                    }
                    net.append(item)       
    recorder = {
        "host": socket.getfqdn(), 
        "info": net
    }
    integrity["recorderMetadata"].append(recorder)

    


    # +Z becuase python doesnt support Z like Javascript Does
    integrity['timestamp']=datetime.datetime.utcnow().isoformat() + "Z"     
    with open(INTEGRITY_PREPROCESSOR_TARGET_PATH, "w") as outfile:
        json.dump(integrity, outfile, indent=4)


dotenv.load_dotenv()
INTEGRITY_PREPROCESSOR_CONFIG_PATH = os.environ.get(
    "INTEGRITY_PREPROCESSOR_CONFIG_PATH", "./config.json"
)
INTEGRITY_PREPROCESSOR_TARGET_PATH = os.environ.get(
    "INTEGRITY_PREPROCESSOR_TARGET_PATH", "../integrity_recorder_report.json"
)

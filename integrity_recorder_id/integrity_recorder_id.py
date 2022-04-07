import os
import sys
import json
from subprocess import check_output
import dotenv


def dockerComposeHash(repoPath):
    os.chdir(repoPath)

    docker_raw = check_output(["docker-compose", "ps"]).decode("utf-8")
    docker_lines = docker_raw.split("\n")
    docker_services = {}
    docker_lines.pop(0)
    docker_lines.pop(0)
    for line in docker_lines:
        if len(line) > 1:
            items = line.split()
            docker_sha = check_output(
                ["docker", "inspect", "--format='{{.Image}}'", items[0]]
            ).decode("utf-8")
            docker_sha_clean = docker_sha.split("'")
            docker_sha = docker_sha_clean[1]
            docker_services[items[0]] = docker_sha
    return docker_services


def gitHash(repoPath):
    os.chdir(repoPath)

    gitHash = {}
    git_raw = check_output(["git", "rev-parse", "HEAD"]).decode("utf-8")
    gitHash["hash"] = git_raw.strip()
    gitHash["hash"] = git_raw.strip()

    git_branch = check_output(["git", "remote", "-v"]).decode("utf-8")
    git_branchsplit = git_branch.split()
    gitHash["repo"] = os.path.basename(git_branchsplit[1])

    git_branch = check_output(["git", "branch", "-v"]).decode("utf-8")
    git_branchsplit = git_branch.split()
    gitHash["branch"] = git_branchsplit[1]

    return gitHash


def build_recorder_id_json():

    f = open(INTEGRITY_PREPROCESSOR_CONFIG_PATH)
    recorder_configs = json.load(f)

    integrity = {}

    for key in recorder_configs:
        recorder_config = recorder_configs[key]
        integrity[key] = {}
        integrity[key]["type"] = recorder_config["type"]
        if "dockercompose" in recorder_config and recorder_config["dockercompose"]:
            integrity[key]["docker_services"] = dockerComposeHash(
                recorder_config["path"]
            )
        if "git" in recorder_config and recorder_config["git"]:
            integrity[key]["github"] = gitHash(recorder_config["path"])

        with open(INTEGRITY_PREPROCESSOR_TARGET_PATH, "w") as outfile:
            json.dump(integrity, outfile)


dotenv.load_dotenv()
INTEGRITY_PREPROCESSOR_CONFIG_PATH = os.environ.get(
    "INTEGRITY_PREPROCESSOR_CONFIG_PATH", "./config.json"
)
INTEGRITY_PREPROCESSOR_TARGET_PATH = os.environ.get(
    "INTEGRITY_PREPROCESSOR_TARGET_PATH", "../integrity_recorder_report.json"
)

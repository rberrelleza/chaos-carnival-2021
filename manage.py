#!/usr/bin/env python3

import argparse
import os
import json
import sys
import time
from datetime import datetime
import subprocess
import yaml
import signal

class ExperimentResult(object):
    """
    Holds Experiment Result
    """

    def __init__(self, name:str, status:str, startTime:datetime):
        self.name = name
        self.status = status
        self.startTime = startTime

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')
    sys.exit(0)

def print_color(text: str, color:bcolors = bcolors.BOLD):
    """
    Utility method to print colored text to stdout.
    :param text:        The text to print
    :param color:       The bcolors to print text in (defaults to bold)
    :return:
    """
    print(f"{color}{text}{bcolors.ENDC}")

def run_shell(cmd: str):
    """
    Runs a shell command and prints command to stdout before
    running so user can see what was run
    :param cmd:     The shell command to run
    :return:
    """
    print_color(f"** RUNNING: {cmd}")
    os.system(cmd)

def start(args):
    """
    Start the application under test
    """
    run_shell("kubectl apply -f ./application/deployment.yaml")
    run_shell("kubectl apply -f ./application/service.yaml")
    run_shell("kubectl apply -f ./application/ingress.yaml")
    run_shell("kubectl apply -f https://hub.litmuschaos.io/api/chaos/master?file=charts/generic/experiments.yaml")
    print_color("\nIngress Details:\n", bcolors.UNDERLINE)
    run_shell("kubectl get ingress")

def list(args):
    """
    List all available Chaos Experiments
    """
    experiments = sorted(os.listdir('./chaos'))
    print("Available Experiments:")
    i = 0
    for experiment_file in experiments:
        i += 1
        print_color(f"\t{i}. {experiment_file.replace('.yaml', '')}")

def run_experiment(experiment: str):
    """
    Run a chaos experiment
    """

    print_color("***************************************************************************************************", bcolors.OKBLUE)
    print_color(f"* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Experiment: {experiment}", bcolors.OKBLUE)
    print_color("***************************************************************************************************", bcolors.OKBLUE)

    experiment_file = experiment + ".yaml"

    # Set namespace to check
    with open(f"./chaos/{experiment_file}") as f:
        spec = yaml.load(f, Loader=yaml.FullLoader)
        result_name = spec['metadata']['name']
        if 'namespace' in spec['metadata']:
            namespace = spec['metadata']['namespace']
        else:
            namespace = os.getenv("OKTETO_NAMESPACE")

    print_color(f"Running Litmus ChaosEngine Experiment {experiment_file} in namespace {namespace}")
    print_color(f"Deploying {experiment_file}...")
    run_shell(f"kubectl delete chaosengine {result_name} -n {namespace}")
    run_shell(f"kubectl create -f ./chaos/{experiment_file} -n {namespace}")

    # Check status of experiment execution
    startTime = datetime.now()
    print_color(f"{startTime.strftime('%Y-%m-%d %H:%M:%S')} Running experiment...")
    expStatusCmd = "kubectl get chaosengine " + result_name + " -o jsonpath='{.status.experiments[0].status}' -n " + namespace
    run_shell(expStatusCmd)
    logs_cmd = f"kubectl logs --since=10s -l name={experiment} -n {namespace}"
    print(f"\n{bcolors.OKGREEN}//** Experiment Logs ({logs_cmd}) **//\n\n")
    try:
        while subprocess.check_output(expStatusCmd, shell=True, stdin=subprocess.PIPE).decode('unicode-escape') != "Completed":
            os.system(logs_cmd)
            os.system("sleep 10")

        print(f"\n\n//** End of Experiment Logs **//{bcolors.ENDC}\n")

        # View experiment results
        run_shell(f"kubectl describe chaosresult {result_name}-{experiment} -n {namespace}")

    except:
        print_color("User has cancelled script execution.", bcolors.FAIL)
        sys.exit(2)

    # Store Experiment Result
    status = subprocess.check_output("kubectl get chaosresult " + result_name + "-" + experiment + " -n " + namespace + " -o jsonpath='{.status.experimentstatus.verdict}'", shell=True).decode('unicode-escape')
    return ExperimentResult(experiment, status, startTime)


def test(args):
    """
    Run a test
    """

    startTimeStamp = time.monotonic()
    experiments = sorted(os.listdir('./chaos'))
    experiment_results = []
    experiment_file = args.test + ".yaml"
    if experiment_file in experiments:
        result = run_experiment(args.test)
        experiment_results.append(result)
    else:
        print_color(f"ERROR: {experiment_file} not found in ./chaos directory. Please check the name and try again.", bcolors.FAIL)
        sys.exit(2)

    # Print out experiment result summary
    print_color("***************************************************************************************************", bcolors.OKBLUE)
    print_color("* Experiments Result Summary", bcolors.OKBLUE)
    print_color("***************************************************************************************************\n", bcolors.OKBLUE)
    headers = ["#", "Start Time", "Experiment", "Status"]
    row_format = "{:>25}" * (len(headers) + 1)
    print_color(row_format.format("", *headers), bcolors.OKBLUE)
    i = 1
    for result in experiment_results:
        if result.status == "Pass":
            print_color(row_format.format("", str(i), result.startTime.strftime('%Y-%m-%d %H:%M:%S'), result.name,"    "+ result.status + " 'carts-db' Service is up and Running after chaos"), bcolors.OKBLUE)
            i += 1
        else:
            print_color(row_format.format("", str(i), result.startTime.strftime('%Y-%m-%d %H:%M:%S'), result.name, result.status), bcolors.OKBLUE)
            i += 1
    print("\n")
    currentTimeStamp= time.monotonic()
    diffTimeStamp = currentTimeStamp - startTimeStamp
    ty_res = time.gmtime(diffTimeStamp)
    totalTime = time.strftime("%H:%M:%S",ty_res)

def stop(args):
    run_shell("kubectl delete -f ./application/deployment.yaml")
    run_shell("kubectl delete -f ./application/service.yaml")
    run_shell("kubectl delete -f ./application/ingress.yaml")

if __name__ == "__main__":

    if (len(sys.argv) < 2):
        sys.exit(2)

    # Add command line arguments
    parser = argparse.ArgumentParser(description='Run chaos.')
    subparsers = parser.add_subparsers()

    parser_start = subparsers.add_parser("start", help="Start application under test.")
    parser_start.set_defaults(func=start)

    parser_stop = subparsers.add_parser("stop", help="stop application under test.")
    parser_stop.set_defaults(func=stop)
    
    # Test command
    parser_test = subparsers.add_parser("test", help="Run Litmus ChaosEngine Experiments inside litmus demo environment.")
    parser_test.add_argument("-t", "--test", type=str, default="*",
                             help="Name of test to run based on yaml file name under /litmus folder. '*' runs all of them with wait time between each experiement.")
    parser_test.add_argument("-w", "--wait", type=int, default=1,
                             help="Number of minutes to wait between experiments. Defaults to 1 mins to avoid the clustering incidents together.")
    parser_test.add_argument("-ty", "--type", type=str, default="all",
                             help="Select the type of chaos to be performed, it can have values pod for pod level chaos,node for infra/node level chaos and all to perform all chaos")
    parser_test.add_argument("-r", "--report", type=str, default="no",
                             help="Select yes to generate the pdf report of the chaos result of different experiment execution")
    parser_test.set_defaults(func=test)

    # List Tests Command
    parser_list = subparsers.add_parser("list", help="List all available Litmus ChaosEngine Experiments available to run.")
    parser_list.set_defaults(func=list)

    signal.signal(signal.SIGINT, signal_handler)

    args = parser.parse_args()
    args.func(args)
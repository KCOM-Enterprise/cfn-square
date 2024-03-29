# Modifications copyright (C) 2017 KCOM
import json
import logging
import os
import time
from functools import wraps

import yaml
from botocore.exceptions import BotoCoreError, ClientError
from dateutil import parser
from git import Repo, InvalidGitRepositoryError
from prettytable import PrettyTable
from six.moves.urllib import request as urllib2

from cfn_sphere.exceptions import CfnSphereException, CfnSphereBotoError


def timed(function):
    logger = logging.getLogger(__name__)

    @wraps(function)
    def wrapper(*args, **kwds):
        start = time.time()
        result = function(*args, **kwds)
        elapsed = time.time() - start
        logger.debug("Execution of {0} required {1}s".format(function.__name__, round(elapsed, 2)))
        return result

    return wrapper


def get_logger(root=False):
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                        datefmt='%d.%m.%Y %H:%M:%S')
    if root:
        return logging.getLogger('cfn_sphere')
    else:
        return logging.getLogger('cfn_sphere.{0}'.format(__name__))


def convert_file(file_path):
    if file_path.lower().endswith('.json'):
        convert = convert_json_to_yaml_string
    elif file_path.lower().endswith('.yml'):
        convert = convert_yaml_to_json_string
    elif file_path.lower().endswith('.yaml'):
        convert = convert_yaml_to_json_string
    else:
        raise Exception('Unknown file extension. Please use .yaml, .yml or .json!')

    with open(file_path, 'r') as filestream:
        return convert(filestream.read())


def kv_list_to_dict(items):
    """
    Converts a list of strings with k=v to dict {k:v}
    :param items: list(string)
    :return: dict
    """
    result = {}
    for item in items:
        parts = str(item).split("=")
        if not len(parts) == 2:
            raise CfnSphereException(
                "Could not parse kv pair: {0}, please ensure it is passed as k=v".format(items))
        result[parts[0]] = parts[1]

    return result


def kv_list_string_to_dict(value):
    """
    Converts a string with format k1=v1,k2=v2 to dict {k1:v1, k2:v2}
    :param items: string
    :return: dict
    """
    items = value.split(",")
    return kv_list_to_dict(items)


def get_pretty_parameters_string(stack):
    table = PrettyTable(["Parameter", "Value"])

    parameters = stack.parameters
    no_echo_parameter_keys = stack.template.get_no_echo_parameter_keys()

    for key, value in parameters.items():
        if key in no_echo_parameter_keys:
            table.add_row([key, "***"])
        else:
            table.add_row([key, value])

    return table.get_string(sortby="Parameter")


def get_pretty_changeset_string(change_set):
    table = PrettyTable(["Action", "Logical ID", "PhysicalID", "ResourceType", "Replacement"])
    for change in change_set:
        detail = change['ResourceChange']
        table.add_row([detail['Action'], detail['LogicalResourceId'],
                       detail.get("PhysicalResourceId", ""), detail['ResourceType'], detail.get("Replacement", "")])

    return table.get_string(sortby="PhysicalID")


def get_pretty_stack_outputs(stack_outputs):
    table = PrettyTable(["Output", "Value"])
    table_has_entries = False

    for output in stack_outputs:
        table_has_entries = True
        table.add_row([output["OutputKey"], output["OutputValue"]])

    if table_has_entries:
        return table.get_string(sortby="Output")
    else:
        return None


def strip_string(string):
    return string[:100] + "..."


def convert_json_to_yaml_string(data):
    if not data:
        return ''
    return yaml.safe_dump(json.loads(data), default_flow_style=False)


def convert_yaml_to_json_string(data):
    if not data:
        return '{}'
    return json.dumps(yaml.load(data, Loader=yaml.SafeLoader), indent=2)


def convert_dict_to_json_string(data):
    return json.dumps(data, indent=2)


def get_cfn_api_server_time():
    url = "https://aws.amazon.com"

    try:
        header_date = urllib2.urlopen(url).info().get('Date')
        return parser.parse(header_date)
    except Exception as e:
        raise CfnSphereException(
            "Could not get AWS server time from {0}. Error: {1}".format(url, e))


def get_latest_version():
    try:
        package_info = get_pypi_package_description()
        return package_info["info"]["version"]
    except Exception:
        return None


def get_pypi_package_description():
    url = "https://pypi.python.org/pypi/cfn-sphere/json"

    response = urllib2.urlopen(url, timeout=2)
    return json.load(response)


def with_boto_retry(max_retries=3, pause_time_multiplier=5):
    """
    Annotation retrying a wrapped function call if it raises a CfnSphereBotoError
    with is_throttling_exception=True
    :param max_retries:
    :param pause_time_multiplier:
    :return: :raise e:
    """
    logger = get_logger()

    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwds):
            retries = 0

            while True:
                try:
                    return function(*args, **kwds)
                except (CfnSphereBotoError, BotoCoreError, ClientError) as e:
                    if isinstance(e, (BotoCoreError, ClientError)):
                        # Wrap Boto exception in CfnSphereBotoError so we can
                        # use it's `is_throttling_exception` attribute.
                        is_throttling_exception = CfnSphereBotoError(e).is_throttling_exception
                    else:
                        is_throttling_exception = e.is_throttling_exception

                    if not is_throttling_exception or retries >= max_retries:
                        raise e

                    sleep_time = pause_time_multiplier * (2 ** retries)
                    logger.warn(
                        "{0} call failed with: '{1}' (Will retry in {2}s)".format(function.__name__, e, sleep_time))
                    time.sleep(sleep_time)
                    retries += 1

        return wrapper

    return decorator


def get_git_repository_remote_url(working_dir):
    if not working_dir:
        return None

    try:
        repo = Repo(working_dir)
        return repo.remotes.origin.url
    except InvalidGitRepositoryError:
        (head, tail) = os.path.split(working_dir)
        if tail:
            return get_git_repository_remote_url(head)
        else:
            return None


def get_resources_dir():
    script_dir = os.path.dirname(os.path.realpath(__file__))
    return os.path.realpath(os.path.join(script_dir, "../../resources"))


if __name__ == "__main__":
    print(get_resources_dir())

#!/usr/bin/env python3

import yaml
import os.path
import re

from future.moves.collections import UserDict, UserList
class OldStyle: pass


def merge_two_dicts(x, y):
    z = x.copy()   # start with x's keys and values
    z.update(y)    # modifies z with y's keys and values & returns None

    return z

def merge_includes(data, path):
    merged_dict = {}

    includes = data.get('include', {})

    for include in includes:
        with open(path + '/' + include, 'r') as include_stream:
            merged_dict = merge_two_dicts(merged_dict, yaml.load(include_stream))
    
    return merge_two_dicts(merged_dict, data)

def transmute(data, transform):
    if isinstance(data, dict):
        return TransformDict(data, transform.context)

    if isinstance(data, list):
        return TransformList(data, transform.context)

    if isinstance(data, str):
        # we are going to double transform because there is a usecase
        # where the transformed string requires transforming again.TransformDict
        result = transform.replace(data)
        result = transform.replace(result)

        if re.match('[.+]', result):
            raise ValueError('Not all tokens replaced: ' + result)
        
        return result

    # if not any of the above, we don't need to transmute it.
    return data

class Transform(object):
    def __init__(self, context):
        self.context = context or {}

    def replace(self, input):
        for key, value in self.context.items():
            if not isinstance(value, str):
                value = str(value)

            input = input.replace('[{}]'.format(key), value)

        return input

class TransformList(UserList):
    def __init__(self, data, context):
        super(TransformList, self).__init__(None, **{})

        self.transform = Transform(context)

        for item in data:
            self.data.append(transmute(item, self.transform))

    def __setitem__(self, index, item):
        self.data[index] = transmute(item, self.transform)

class TransformDict(UserDict):
    def __init__(self, data, context):
        super(TransformDict, self).__init__()

        self.transform = Transform(context)

        if data:
            for key, value in data.items():
                self.__setitem__(key, value)

    def __setitem__(self, key, value):
        self.data[self.transform.replace(key)] = transmute(value, self.transform)

    def alphanum(self, key):
        return ''.join(c for c in self[key] if c.isalnum())


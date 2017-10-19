import re
from six import string_types

from cfn_sphere.exceptions import TemplateErrorException


class CloudFormationTemplateTransformer(object):
    @classmethod
    def transform_template(cls, template, additional_stack_description=None):
        description = template.description
        conditions = template.conditions
        resources = template.resources
        outputs = template.outputs

        if additional_stack_description:
            description = cls.extend_stack_description(description, additional_stack_description)

        # only executed for keys starting with '@' or '|' for performance reasons
        key_handlers = [
            cls.transform_join_key,
            cls.transform_taupage_user_data_key,
            cls.transform_yaml_user_data_key,
            cls.transform_include_key,
            cls.check_for_leftover_reference_keys
        ]

        value_handlers = [
            cls.transform_reference_string,
            cls.transform_getattr_string,
            cls.check_for_leftover_reference_values
        ]

        template.description = description
        template.conditions = cls.scan(conditions, key_handlers, value_handlers)
        template.resources = cls.scan(resources, key_handlers, value_handlers)
        template.outputs = cls.scan(outputs, key_handlers, value_handlers)

        return template

    @classmethod
    def scan(cls, value, key_handlers, value_handlers):

        if isinstance(value, dict):
            result = {}

            for k, v in value.items():
                if cls.is_reference_key(k):
                    for key_handler in key_handlers:
                        k, v = key_handler(k, cls.scan(v, key_handlers, value_handlers))

                result[k] = cls.scan(v, key_handlers, value_handlers)

            return result

        elif isinstance(value, list):
            result = []

            for item in value:
                result.append(cls.scan(item, key_handlers, value_handlers))

            return result

        elif isinstance(value, string_types):
            result = value
            for value_handler in value_handlers:
                result = value_handler(result)

            return result

        else:
            return value

    @classmethod
    def extend_stack_description(cls, description, additional_stack_description):
        additional_stack_description = " | {}".format(additional_stack_description)
        total_length = len(description) + len(additional_stack_description)
        if total_length > 1024:
            strip_index = len(description) - (total_length - 1024)
            return str(description)[:strip_index] + additional_stack_description
        else:
            return description + additional_stack_description

    @staticmethod
    def check_for_leftover_reference_values(value):
        pattern = re.compile("^\|[a-zA-Z]+\|[a-zA-Z]+")
        if isinstance(value, string_types) and pattern.search(value):
            raise TemplateErrorException("Unhandled reference value found: {0}".format(value))

        return value

    @classmethod
    def check_for_leftover_reference_keys(cls, key, value):
        if cls.is_reference_key(key):
            raise TemplateErrorException("Unhandled reference key found: {0}".format(key))

        return key, value

    @staticmethod
    def is_reference_key(key):
        if isinstance(key, string_types) and re.search("^\|[a-zA-Z]+\|", key.strip()):
            return True
        elif isinstance(key, string_types) and key.strip().startswith('@') and key.endswith('@'):
            return True
        else:
            return False

    @classmethod
    def transform_taupage_user_data_key(cls, key, value):
        if not value:
            return key, value

        if isinstance(key, string_types):

            if str(key).lower() == '@taupageuserdata@':

                if not isinstance(value, dict):
                    raise TemplateErrorException("Value of 'TaupageUserData' must be of type dict")

                lines = ['#taupage-ami-config']
                lines.extend(cls.transform_dict_to_yaml_lines_list(value))

                return "UserData", {
                    'Fn::Base64': {
                        'Fn::Join': ['\n', lines]
                    }
                }

        return key, value

    @classmethod
    def transform_yaml_user_data_key(cls, key, value):
        if not value:
            return key, value

        if isinstance(key, string_types):

            if str(key).lower() == '@yamluserdata@':

                if not isinstance(value, dict):
                    raise TemplateErrorException("Value of 'YamlUserData' must be of type dict")

                lines = cls.transform_dict_to_yaml_lines_list(value)

                return "UserData", {
                    'Fn::Base64': {
                        'Fn::Join': ['\n', lines]
                    }
                }

        return key, value

    @classmethod
    def transform_join_key(cls, key, value):
        if not value:
            return key, value

        if isinstance(key, string_types):
            if key.lower().startswith('|join|'):
                if not isinstance(value, list):
                    raise TemplateErrorException("Value of '|join|' must be of type list")

                join_string = key[6:]

                return 'Fn::Join', [join_string, value]

        return key, value

    @classmethod
    def transform_include_key(cls, key, value):
        if not value:
            return key, value

        if isinstance(key, string_types):
            if key.lower().strip() == '|include|':
                if not isinstance(value, string_types):
                    raise TemplateErrorException("Value of '|include|' must be of type string")
                if not value.lower().startswith("s3://"):
                    raise TemplateErrorException("Value of '|include|' must start with s3://")

                return "Fn::Transform", {"Name": "AWS::Include",
                                         "Location": value}

        return key, value

    @staticmethod
    def transform_kv_to_cfn_join(key, value, delimiter=": "):
        if isinstance(value, string_types) and ":" in key:
            key = "'{0}'".format(key)

        if isinstance(value, string_types) and ":" in value:
            value = "'{0}'".format(value)

        return {'Fn::Join': [delimiter, [key, value]]}

    @staticmethod
    def transform_reference_string(value):
        if not value:
            return value

        if isinstance(value, string_types) and value.lower().startswith('|ref|'):
            referenced_value = value[5:]

            if not referenced_value:
                raise TemplateErrorException("Reference must be like |ref|resource")

            return {'Ref': referenced_value}

        return value

    @staticmethod
    def transform_getattr_string(value):
        if not value:
            return value

        if isinstance(value, string_types):
            if value.lower().startswith('|getatt|'):
                elements = value.split('|', 3)

                if len(elements) != 4:
                    raise TemplateErrorException("Attribute reference must be like '|getatt|resource|attribute'")

                resource = elements[2]
                attribute = elements[3]

                return {'Fn::GetAtt': [resource, attribute]}

        return value

    @classmethod
    def _transform_dict(cls, dict_value, indentation_level=0, prefix=""):
        lines = []

        for key, value in sorted(dict_value.items()):

            print("TRANSFORMING_DICT_VALUES: {} : {}".format(key, value))

            # key indentation with two spaces
            if indentation_level > 0:
                indented_key = "  " * indentation_level + prefix + str(key)
            else:
                indented_key = prefix + str(key)

            if isinstance(key, string_types):
                # do not go any further and directly return cfn functions and their values
                if key.lower() == "ref" or key.lower().startswith("fn::"):
                    indented_hyphen = '  ' * indentation_level + prefix
                    # aws functions results will always be a string
                    result = {key: value}
                    line = cls.transform_kv_to_cfn_join(indented_hyphen, result, delimiter="")

                    print("INDENTED_HYPHEN: '{}'".format(indented_hyphen))
                    print("RESULT: {}".format(result))
                    print("LINE: {}".format(line))
                    lines.append(line)
                else:
                    print("NON_REFERENCE_KEY: {}".format(key))
                    # recursion for dict or list values
                    if isinstance(value, dict):
                        print("DICT_VALUE: {}".format(value))
                        result = cls._transform_dict(value, indentation_level + 1)
                        if isinstance(result, dict):
                            lines.append(cls.transform_kv_to_cfn_join(indented_key, result))
                        elif isinstance(result, list):
                            lines.append(indented_key + ":")
                            lines.extend(result)
                        else:
                            raise TemplateErrorException("Failed to convert dict to list of lines")

                    elif isinstance(value, list):
                        print("LIST_VALUE: {}".format(value))
                        lines.append(indented_key + ":")
                        lines.extend(cls._transform_list(value, indentation_level + 1))
                    else:
                        print("SIMPLE_VALUE: {}".format(value))
                        lines.append(indented_key + ": " + str(value))
            else:
                lines.append(cls.transform_kv_to_cfn_join(indented_key, value))

        return lines

    @classmethod
    def _transform_list(cls, list_value, indentation_level=0):
        lines = []

        indented_hyphen = '  ' * indentation_level + "-"

        for item in list_value:
            print("LIST_ITEM: {}".format(item))
            if isinstance(item, dict):
                lines.extend(cls._transform_dict(item, indentation_level, prefix="-"))
            # list of list
            elif isinstance(item, list):
                lines.append(indented_hyphen)
                lines.extend(cls._transform_list(item, indentation_level + 1))
            else:
                lines.append(indented_hyphen + str(item))

        return lines

    @classmethod
    def transform_dict_to_yaml_lines_list(cls, userdata_dict):
        return cls._transform_dict(userdata_dict)

import unittest

from copy import deepcopy
from cfn_sphere.transform import TransformDict


class TestTransform(unittest.TestCase):

    def test_transform_dict(self):
        data = {
            'abc': '[ABC]',
            'def': True,
            'ghi': 5,
            'jkl': '.dot'
        }

        data_before = deepcopy(data)

        context = {'ABC': 'XXX'}

        expected = {
            'abc': 'XXX',
            'def': True,
            'ghi': 5,
            'jkl': '.dot'
        }

        transform_dict = TransformDict(data=data, context=context)

        self.assertEqual(data_before, data)
        self.assertEqual(expected, transform_dict, expected)

    def test_transform_dict_with_missing_replacements(self):
        data = {
            'abc': 'XXX',
            'def': '[DEF]'
        }
        context = {'ABC': 'XXX'}

        with self.assertRaises(ValueError):
            TransformDict(data=data, context=context)

    def test_transform_dict_with_missing_empty_replacement(self):
        data = {
            'abc': 'XXX',
            'def': '[]'
        }
        context = {'ABC': 'XXX'}

        with self.assertRaises(ValueError):
            TransformDict(data=data, context=context)


if __name__ == '__main__':
    unittest.main(buffer=False)

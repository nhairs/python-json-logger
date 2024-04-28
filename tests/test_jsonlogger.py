import datetime
import logging
from io import StringIO
import json
import random
import sys
import traceback
import unittest
import unittest.mock

from pythonjsonlogger.core import RESERVED_ATTRS, merge_record_extra
from pythonjsonlogger.json import JsonFormatter


class TestJsonLogger(unittest.TestCase):
    def test_merge_record_extra(self):
        record = logging.LogRecord(
            "name", level=1, pathname="", lineno=1, msg="Some message", args=None, exc_info=None
        )
        output = merge_record_extra(record, target=dict(foo="bar"), reserved=[])
        self.assertIn("foo", output)
        self.assertIn("msg", output)
        self.assertEqual(output["foo"], "bar")
        self.assertEqual(output["msg"], "Some message")

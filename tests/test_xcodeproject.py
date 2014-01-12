#!usr/bin/env python

from .context import xcodeproject

import unittest
import os
import sys
import logging
import inspect

# logging.basicConfig(level=logging.DEBUG)

class TestXcodeProject(unittest.TestCase):

    def setUp(self):
        self.project = xcodeproject.XcodeProject(os.path.expanduser(self.test_project_path()))
    
    def test_project_path(self):
        test_dir_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
        return os.path.join(test_dir_path, 'PythonXcodeTest/PythonXcodeTest.xcodeproj')

    def testProject(self):
        self.assertIsInstance(self.project, xcodeproject.XcodeProject)

    def testRoot(self):
        self.assertIsInstance(self.project.root_object(), xcodeproject.PBXProject)

    def testTargets(self):
        self.assertIsInstance(self.project.targets()[0], xcodeproject.AbstractTarget)
        for target in self.project.targets():
            configs = target.build_configurations
            header = ['========== Target {} =========='.format(target.name)]
            for config in configs:
                text = config.build_settings_text()
                if not text:
                    continue
                if header:
                    print header.pop()
                print 'config "{}"'.format(target.name, config.name)
                print text


if __name__ == '__main__':
    unittest.main()

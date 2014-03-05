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
        targets = self.project.targets()
        self.assertTrue(len(targets) > 0)
        for target in targets:
            self.assertIsInstance(target, xcodeproject.AbstractTarget)

    def testBuildConfigurations(self):
        for target in self.project.targets():
            configs = target.buildConfigurationList
            self.assertIsInstance(configs, xcodeproject.XCConfigurationList)
            self.assertEquals(len(configs.buildConfigurations), 2)
            for config in configs:
                text = config.build_settings_text()
                self.assertTrue(text)

    def testScriptBuildPhases(self):
        target = self.project.target_for_name('PythonXcodeTest')
        self.assertIsInstance(target, xcodeproject.PBXNativeTarget)
        script_build_phases = target.script_build_phases()
        self.assertTrue(len(script_build_phases), 2)

        self.assertIsInstance(script_build_phases[0], xcodeproject.PBXShellScriptBuildPhase)
        self.assertEquals(script_build_phases[0].name, 'Test Shell Script Phase 1')
        self.assertEquals(script_build_phases[0].shellPath, '/bin/sh')
        self.assertEquals(script_build_phases[0].shellScript, 'echo foo\n')

        self.assertIsInstance(script_build_phases[1], xcodeproject.PBXShellScriptBuildPhase)
        self.assertEquals(script_build_phases[1].name, 'Test Shell Script Phase 2')
        self.assertEquals(script_build_phases[1].shellPath, '/usr/bin/env python')
        self.assertEquals(script_build_phases[1].shellScript, "print 'foo'\n")
    
    def test_class_map(self):
        map = self.project.class_name_to_item_map
        self.assertTrue('PBXBuildFile' in map)
        self.assertTrue('PBXNativeTarget' in map)
        self.assertTrue('PBXFileReference' in map)
        self.assertEquals(len(map['PBXBuildFile']), 3)
#        print map

    def test_build_files(self):
        map = self.project.build_file_map()
        files = map.values()
        self.assertEquals(len(files), 3)
        file = map['1BC96D0D188311C700AFCEDA']
        self.assertIsInstance(file, xcodeproject.PBXBuildFile)
        ref = file.fileRef
        self.assertIsInstance(ref, xcodeproject.PBXFileReference)
        self.assertEquals(ref.id, '1BC96D0C188311C700AFCEDA')
        self.assertEquals(ref.path, 'main.m')
        self.assertEquals(ref.lastKnownFileType, 'sourcecode.c.objc')
        self.assertTrue(ref.id in self.project.file_reference_map())
        
        
        


if __name__ == '__main__':
    unittest.main()

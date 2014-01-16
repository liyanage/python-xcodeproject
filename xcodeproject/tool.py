#!/usr/bin/env python

from . import tool_base
from . import xcodeproject

import os
import sys

class SubcommandListProjectFileBuildSettings(tool_base.AbstractSubcommand):
    """List build settings that are defined in a project file, either at the project or target level."""
    
    def run(self):
        project_paths = []
        if self.args.recursive:
            project_paths = self.find_projects()
        else:
            project_paths = self.args.path
        self.process_projects(project_paths)
    
    def find_projects(self):
        project_paths = []
        for dirpath, dirnames, filenames in os.walk(self.args.path, topdown=True):
            for exclude in self.args.exclude_dir:
                if exclude in dirnames:
                    print >> sys.stderr, 'Skipping {}'.format(os.path.join(dirpath, exclude))
                    del dirnames[dirnames.index(exclude)]
            for dirname in [d for d in dirnames if d.endswith('.xcodeproj')]:
                project_paths.append(os.path.abspath(os.path.expanduser(os.path.join(dirpath, dirname))))
        return project_paths
    
    def process_projects(self, paths):
        for project_path in paths:
            project = xcodeproject.XcodeProject(project_path)
            project_header = ['\n========== Project {} ({}) =========='.format(project.name, project_path)]
            project_configs = project.root_object().build_configurations
            for config in project_configs:
                text = config.build_settings_text()
                if not text:
                    continue
                if project_header:
                    print project_header.pop()

                if self.args.summary:
                    print 'Project-level build settings in configuration "{}": {} settings'.format(config.name, len(text.splitlines()))
                else:
                    print 'Project-level build settings in configuration "{}":'.format(config.name)
                    print text
                
            for target in project.targets():
                configs = target.build_configurations
                target_header = ['---------- Target {} ----------'.format(target.name)]
                for config in configs:
                    text = config.build_settings_text()
                    if not text:
                        continue
                    if project_header:
                        print project_header.pop()
                    if target_header:
                        print target_header.pop()

                    if self.args.summary:
                        print 'Target-level build settings in configuration "{}": {} settings'.format(config.name, len(text.splitlines()))
                    else:
                        print 'Target-level build settings in configuration "{}":'.format(config.name)
                        print text
            
    @classmethod
    def configure_argument_parser(cls, parser):
        parser.add_argument('path', help='Path to the project file, or to the toplevel directory in which to find project file if --recursive is given')
        parser.add_argument('-r', '--recursive', action='store_true', help='Enable verbose debug logging')
        parser.add_argument('-s', '--summary', action='store_true', help='Print more concise summary information')
        parser.add_argument('--exclude-dir', action='append', default=[], help='Exclude subdirectories with the given name in recursive mode')


class XcodeprojectTool(tool_base.Tool):
    """Xcode Project Tool"""
    
    pass
    

if __name__ == "__main__":
    XcodeprojectTool.main()

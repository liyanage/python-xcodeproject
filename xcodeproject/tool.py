#!/usr/bin/env python

from . import tool_base
from . import xcodeproject

import os
import sys


class ProjectFileProcessingSubcommand(tool_base.AbstractSubcommand):
    
    def run(self):
        project_paths = []
        if self.args.recursive:
            project_paths = self.find_projects()
        else:
            project_paths = [self.args.path]
        self.process_project_paths(project_paths)

    def process_project_paths(self, paths):
        for project_path in paths:
            print project_path
            project = xcodeproject.XcodeProject(project_path)
            self.process_project(project)

    def process_project(self, project):
        raise NotImplementedError()
    
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
    
    @classmethod
    def configure_argument_parser(cls, parser):
        parser.add_argument('path', help='Path to the project file, or to the toplevel directory in which to find project files if --recursive is given')
        parser.add_argument('-r', '--recursive', action='store_true', help='Treat the given path as a root directory instead of an xcode project bundle and recursively find and process all xcode projects below that root')
        parser.add_argument('--exclude-dir', action='append', default=[], help='Exclude subdirectories with the given name in recursive mode')


class SubcommandListProjectFileBuildSettings(ProjectFileProcessingSubcommand):
    """List build settings that are defined in a project file, either at the project or target level."""

    def process_project(self, project):
        project_header = ['\n========== Project {} ({}) =========='.format(project.name, project.path)]
        project_configs = project.root_object().buildConfigurationList
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
            configs = target.buildConfigurationList
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
        super(SubcommandListProjectFileBuildSettings, cls).configure_argument_parser(parser)
        parser.add_argument('-s', '--summary', action='store_true', help='Print more concise summary information')


class SubcommandPrintShellScripts(ProjectFileProcessingSubcommand):
    """Print the code of all shell script build phases"""
    
    def process_project(self, project):
        all_phases = []
        for target in project.targets():
            target_phases = []
            for phase in target.script_build_phases():
                target_phases.append(phase)
            if target_phases:
                all_phases.append((target, target_phases))

        if all_phases:
            print '======= Script phases in project {}'.format(project.name)
            for target, phases in all_phases:
                print 'Target {}'.format(target.name)
                for phase in phases:
                    print '>>>>>>>>>>>>>>>> Begin script "{}" (interpreter: {})'.format(phase.name, phase.shellPath)
                    print phase.shellScript
                    print '<<<<<<<<<<<<<<<< End script "{}" -------\n'.format(phase.name)


class SubcommandPrintOrphanedFileReferences(ProjectFileProcessingSubcommand):
    """Print file references that are not used anywhere"""
    
    def process_project(self, project):
        known_file_reference_map = self.known_file_reference_map_for_project(project)
        orphaned_file_references = {k: v for k, v in project.file_reference_map().items() if k not in known_file_reference_map}

        if orphaned_file_references:
            print '======= Orphaned file references (PBXFileReference) in {}'.format(project.name)
            for id, ref in orphaned_file_references.items():
                print '{} {}'.format(id, ref.path)

    def known_file_reference_map_for_project(self, project):
        known_file_reference_map = {}

        for id, build_file in project.build_file_map().items():
            known_file_reference_map[build_file.fileRef.id] = build_file

        for group_id, group in project.all_groups_map().items():
            for item in group.children:
                if item.is_file_reference():
                    known_file_reference_map[item.id] = item
        
        return known_file_reference_map


class XcodeprojectTool(tool_base.Tool):
    """Xcode Project Tool"""
    
    pass
    

if __name__ == "__main__":
    XcodeprojectTool.main()

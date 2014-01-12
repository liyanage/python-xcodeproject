#!usr/bin/env python

import os
import re
import sys
import plistlib
import subprocess
import logging

class ProjectItem(object):

    def __init__(self, id, data):
        self.id = id
        self.data = data

    def resolve_references(self, project):
        pass

    def __unicode__(self):
        return u'<{} {} {}>'.format(type(self).__name__, self.id, self.name)

    def __str__(self):
        return unicode(self).encode('utf-8', errors='backslashreplace')

    @property
    def name(self):
        return self.data['name'] if 'name' in self.data else '(no name)'

    @classmethod
    def subclass_map(cls):
        map = {c.__name__: c for c in cls.__subclasses__()}
        for subclass in map.values():
            map.update(subclass.subclass_map())
        return map


class XCBuildConfiguration(ProjectItem):

    def build_settings(self):
        return self.data['buildSettings']

    def build_settings_text(self):
        settings = self.build_settings()
        setting_names = sorted(settings.keys())
        items = []
        for name in setting_names:
            value = settings[name]
            if isinstance(value, list):
                value = ' '.join(value)
            items.append('{} = {}\n'.format(name, value))
        
        return ''.join(items)


class XCConfigurationList(ProjectItem):

    def build_configurations(self):
        return self.configurations

    def __iter__(self):
        for config in self.configurations:
            yield config

    def resolve_references(self, project):
        self.configurations = [project.object_for_id(i) for i in self.data['buildConfigurations']]


class ConfigurableProjectItem(ProjectItem):

    def resolve_references(self, project):
        self.build_configurations = project.object_for_id(self.data['buildConfigurationList'])


class AbstractTarget(ConfigurableProjectItem):

    @property
    def product_name(self):
        return self.data['productName'] if 'productName' in self.data else '(no product name)'


class PBXProject(ConfigurableProjectItem):
    pass


class PBXNativeTarget(AbstractTarget):

    # def resolve_references(self, project):
    #     super(PBXNativeTarget, self).resolve_references(project)
    pass


class PBXAggregateTarget(AbstractTarget):

    def resolve_references(self, project):
        self.build_configurations = project.object_for_id(self.data['buildConfigurationList'])


class XcodeProject(object):

    def __init__(self, path):
        self.path = path
        self.parse()

    @property    
    def name(self):
        return os.path.basename(self.path)

    def parse(self):
        project_file_path = os.path.join(self.path, 'project.pbxproj')
        xml_data = subprocess.check_output(['plutil', '-convert', 'xml1', '-o', '-', project_file_path])
        data = plistlib.readPlistFromString(xml_data)

        self.objects = {}
        project_class_map = ProjectItem.subclass_map()

        self.root_object_id = data['rootObject']

        for object_id, object_data in data['objects'].items():
            item_class_name = object_data['isa']
            item_class = project_class_map.get(item_class_name, ProjectItem)
            item = item_class(object_id, object_data)
            logging.debug('{}: {} {}'.format(object_id, item_class_name, item))
            self.objects[object_id] = item

        for item in self.objects.values():
            item.resolve_references(self)

    def targets(self):
        return [i for i in self.objects.values() if isinstance(i, AbstractTarget)]

    def object_for_id(self, object_id):
        return self.objects[object_id]
    
    def root_object(self):
        return self.object_for_id(self.root_object_id)

    
    

#!usr/bin/env python

import os
import re
import sys
import plistlib
import subprocess
import logging
import collections


# def camel_case_to_underscore(camelcase_value):
#     return re.sub(r'([a-z])([A-Z])', lambda match: match.group(1) + '_' + match.group(2).lower(), camelcase_value)


class PropertyConverter(object):

    @classmethod
    def decode_property_value(cls, project, value):
        pass


class IdentityPropertyConverter(object):

    @classmethod
    def decode_property_value(cls, project, value):
        return value


class ObjectReferencePropertyConverter(object):

    @classmethod
    def decode_property_value(cls, project, value):
        if not value:
            return None
        return project.object_for_id(value)


class ObjectReferenceListPropertyConverter(object):

    @classmethod
    def decode_property_value(cls, project, value):
        if not value:
            return []
        return [project.object_for_id(i) for i in value]


class ProjectItem(object):

    def __init__(self, id, data):
        self.id = id
        self.data = data
        self.line_number_start = None
        self.line_number_end = None
        self.name = '(no name)'

    def parse_data(self, project):
        converter_map = self.property_converter_map()
        for property_name, value in self.data.items():
            converter_class = converter_map.get(property_name, IdentityPropertyConverter)
            value = converter_class.decode_property_value(project, value)
            setattr(self, property_name, value)
    
    def property_converter_map(self):
        return {
            'files': ObjectReferenceListPropertyConverter
        }

    def is_target(self):
        return False
    
    def is_file_reference(self):
        return False

    def __unicode__(self):
        return u'<{} {} {}>'.format(type(self).__name__, self.id, self.name)

    def __str__(self):
        return unicode(self).encode('utf-8', errors='backslashreplace')

    @classmethod
    def subclass_map(cls):
        map = {c.__name__: c for c in cls.__subclasses__()}
        for subclass in map.values():
            map.update(subclass.subclass_map())
        return map


class PBXFileReference(ProjectItem):

    def is_file_reference(self):
        return True


class PBXBuildFile(ProjectItem):

    def property_converter_map(self):
        converter_map = super(PBXBuildFile, self).property_converter_map()
        converter_map.update({
            'fileRef': ObjectReferencePropertyConverter
        })
        return converter_map


class PBXGroup(ProjectItem):

    def property_converter_map(self):
        converter_map = super(PBXGroup, self).property_converter_map()
        converter_map.update({
            'children': ObjectReferenceListPropertyConverter
        })
        return converter_map


class PBXVariantGroup(PBXGroup):
    pass


class XCVersionGroup(PBXGroup):
    pass

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

    def __iter__(self):
        for config in self.buildConfigurations:
            yield config

    def property_converter_map(self):
        converter_map = super(XCConfigurationList, self).property_converter_map()
        converter_map.update({
            'buildConfigurations': ObjectReferenceListPropertyConverter
        })
        return converter_map


class ConfigurableProjectItem(ProjectItem):

    def property_converter_map(self):
        property_map = super(ConfigurableProjectItem, self).property_converter_map()
        property_map.update({
            'buildConfigurationList': ObjectReferencePropertyConverter
        })
        return property_map


class AbstractTarget(ConfigurableProjectItem):

    def __init__(self, *args, **kwargs):
        super(AbstractTarget, self).__init__(*args, **kwargs)
        self.productName = '(no product name)'

    def is_target(self):
        return True
        
    def script_build_phases(self):
        return [p for p in self.buildPhases if isinstance(p, PBXShellScriptBuildPhase)]
    
    def property_converter_map(self):
        property_map = super(AbstractTarget, self).property_converter_map()
        property_map.update({
            'buildPhases': ObjectReferenceListPropertyConverter
        })
        return property_map


class PBXProject(ConfigurableProjectItem):
    pass


class PBXNativeTarget(AbstractTarget):
    pass


class PBXAggregateTarget(AbstractTarget):
    pass


class PBXShellScriptBuildPhase(ProjectItem):
    pass


class XcodeProject(object):

    def __init__(self, path):
        path = os.path.abspath(os.path.expanduser(path))
        if not os.path.exists(os.path.join(path, 'project.pbxproj')):
            raise Exception('Not a valid project path: {}'.format(path))
        self.path = path
        self.class_name_to_item_map = collections.defaultdict(dict)
        self.parse()

    @property    
    def name(self):
        return os.path.basename(self.path)

    def parse(self):
        project_file_path = os.path.join(self.path, 'project.pbxproj')
        xml_data = subprocess.check_output(['plutil', '-convert', 'xml1', '-o', '-', project_file_path])
        data = plistlib.readPlistFromString(xml_data)
        
        object_id_to_line_number_map = self.object_id_line_number_map_for_path(project_file_path)

        self.objects = {}
        project_class_map = ProjectItem.subclass_map()

        self.root_object_id = data['rootObject']

        for object_id, object_data in data['objects'].items():
            item_class_name = object_data['isa']
            item_class = project_class_map.get(item_class_name, ProjectItem)
            item = item_class(object_id, object_data)
            item.line_number_start, item.line_number_end = object_id_to_line_number_map[object_id]
            logging.debug('{}: {} {}'.format(object_id, item_class_name, item))
            self.objects[object_id] = item
            self.class_name_to_item_map[item_class_name][object_id] = item

        for item in self.objects.values():
            item.parse_data(self)
    
    def object_id_line_number_map_for_path(self, path):
        object_id_line_re = re.compile(r'(\s*)([A-F0-9]{24})\s*(?:/\*s*.*\s*\*/)?\s*=\s*{(.*)')
        object_end_line_re = None
        state = 'start'
        current_object_start_line_number = None
        current_object_id = None
        object_id_to_line_number_map = {}
        with open(path) as f:
            for line_number, line in enumerate(f, start=1):
                if state == 'start':
                    match = object_id_line_re.match(line)
                    if match:
                        object_id = match.group(2)
                        assert object_id not in object_id_to_line_number_map, 'Object ID {} seen on line {} and {}'.format(object_id, object_id_to_line_number_map[object_id], line_number)
                        if '}' in match.group(3):
                            # one-line object
                            object_id_to_line_number_map[object_id] = [line_number, line_number]
                        else:
                            # multi-line object
                            current_object_start_line_number = line_number
                            current_object_id = object_id
                            object_end_line_re = re.compile(match.group(1) + '}')
                            state = 'reading_object'
                if state == 'reading_object':
                    match = object_end_line_re.match(line)
                    if match:
                        object_id_to_line_number_map[current_object_id] = [current_object_start_line_number, line_number]
                        state = 'start'
        return object_id_to_line_number_map


    def targets(self):
        return [i for i in self.objects.values() if isinstance(i, AbstractTarget)]
    
    def target_for_name(self, target_name):
        for target in self.targets():
            if target.name == target_name:
                return target
        return None
    
    def build_file_map(self):
        return self.class_name_to_item_map['PBXBuildFile']

    def file_reference_map(self):
        return self.class_name_to_item_map['PBXFileReference']

    def group_map(self):
        return self.class_name_to_item_map['PBXGroup']

    def variant_group_map(self):
        return self.class_name_to_item_map['PBXVariantGroup']

    def version_group_map(self):
        return self.class_name_to_item_map['XCVersionGroup']

    def all_groups_map(self):
        groups = {}
        groups.update(self.group_map())
        groups.update(self.variant_group_map())
        groups.update(self.version_group_map())
        return groups

    def object_for_id(self, object_id):
        if object_id not in self.objects:
            raise Exception('Invalid object reference {} in {}'.format(object_id, self.path))
        return self.objects[object_id]

    def main_group_id(self):
        return self.root_object().mainGroup

    def has_object_with_id(self, object_id):
        return object_id in self.objects

    def root_object(self):
        return self.object_for_id(self.root_object_id)

    
    

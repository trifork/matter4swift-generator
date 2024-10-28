# Copyright (c) 2024 Trifork A/S
#
# SPDX-License-Identifier: MIT

import datetime
import os
import pathlib
import dataclasses
from typing import Optional

from matter_idl.generators import CodeGenerator, GeneratorStorage
from matter_idl.generators.cluster_selection import server_side_clusters, binding_clusters
from matter_idl.generators.type_definitions import (
    BasicInteger,
    BasicString,
    FundamentalType,
    IdlBitmapType,
    IdlEnumType,
    IdlType,
    ParseDataType,
    TypeLookupContext
)
from matter_idl.matter_idl_types import (
    Attribute,
    AttributeQuality,
    Cluster,
    Command,
    DataType,
    Field,
    FieldQuality,
    Idl,
    Struct,
    StructQuality,
    StructTag
)

@dataclasses.dataclass
class GenerateTarget:
    template: str
    output_name: str

@dataclasses.dataclass
class GlobalType:
    name: str      # Swift name
    idl_type: str  # assumed IDL type


# types that Swift should see globally
_GLOBAL_TYPES = [
    GlobalType("Bool", "boolean"),
    GlobalType("String", "char_string"),
    GlobalType("Double", "double"),
    GlobalType("Float", "single"),
    GlobalType("Int8", "int8s"),
    GlobalType("UInt8", "int8u"),
    GlobalType("Int16", "int16s"),
    GlobalType("UInt16", "int16u"),
    GlobalType("Int32", "int24s"),
    GlobalType("UInt32", "int24u"),
    GlobalType("Int32", "int32s"),
    GlobalType("UInt32", "int32u"),
    GlobalType("Int64", "int40s"),
    GlobalType("UInt64", "int40u"),
    GlobalType("Int64", "int48s"),
    GlobalType("UInt64", "int48u"),
    GlobalType("Int64", "int56s"),
    GlobalType("UInt64", "int56u"),
    GlobalType("Int64", "int64s"),
    GlobalType("UInt64", "int64u"),
    GlobalType("matter4swift.OctetString", "octet_string"),
    GlobalType("UInt8", "enum8"),
    GlobalType("matter4swift.CommandId", "command_id"),
    GlobalType("matter4swift.EventId", "event_id"),
    GlobalType("matter4swift.AttribId", "attrib_id"),
    GlobalType("matter4swift.ClusterId", "cluster_id"),
    GlobalType("matter4swift.EndpointNo", "endpoint_no"),
    GlobalType("matter4swift.DevtypeId", "devtype_id"),
    GlobalType("matter4swift.FabricIdx", "fabric_idx"),
    GlobalType("matter4swift.FabricId", "fabric_id"),
    GlobalType("matter4swift.NodeId", "node_id"),
    GlobalType("matter4swift.GroupId", "group_id"),
    GlobalType("matter4swift.VendorId", "vendor_id"),
    GlobalType("UInt8", "bitmap8"),
    GlobalType("UInt16", "bitmap16"),
    GlobalType("UInt32", "bitmap32"),
    GlobalType("UInt64", "bitmap64"),
    GlobalType("matter4swift.Temperature", "temperature"),
    GlobalType("matter4swift.Percent", "percent"),
    GlobalType("matter4swift.EpochS", "epoch_s"),
    GlobalType("matter4swift.ElapsedS", "elapsed_s"),
    GlobalType("matter4swift.EpochUs", "epoch_us"),
    GlobalType("String", "long_char_string"),
    GlobalType("matter4swift.OctetString", "long_octet_string"),
    GlobalType("UInt16", "enum16"),
    GlobalType("matter4swift.Status", "status"),
    GlobalType("matter4swift.DefaultSuccess", "DefaultSuccess"),

    GlobalType("Int64", "power_mw"),
    GlobalType("Int64", "amperage_ma"),
    GlobalType("Int64", "voltage_mv"),
    GlobalType("Int64", "energy_mwh"),
    GlobalType("UInt16", "percent100ths"),
    GlobalType("UInt64", "systime_ms"),
    GlobalType("UInt64", "systime_us"),
    GlobalType("UInt64", "posix_ms"),
]

def _get_idl_type(field: Field|DataType|Struct|str, context: TypeLookupContext) -> (str, bool):
    is_array = False
    if isinstance(field, Field):
        idl_type = field.data_type.name
        is_array = field.is_list
    elif isinstance(field, DataType):
        idl_type = field.name
    elif isinstance(field, Struct):
        idl_type = field.name
    else:
        field_struct = context.find_struct(field)
        if field_struct is None:
            idl_type = field
        else:
            idl_type = field_struct.name
    return (idl_type, is_array)

def SwiftType(field: Field|DataType|Struct|str, context: TypeLookupContext) -> str:
    idl_type, is_array = _get_idl_type(field, context)

    swift_type = None
    for global_type in _GLOBAL_TYPES:
        if global_type.idl_type == idl_type:
            swift_type = global_type.name
            break
    if not swift_type:
        swift_type = idl_type
    if is_array:
        swift_type = f'[{swift_type}]'
    return swift_type

def SwiftUIViewType(field: Field|DataType|Struct|str, context: TypeLookupContext) -> str:
    idl_type, is_array = _get_idl_type(field, context)

    swift_type = None
    for global_type in _GLOBAL_TYPES:
        if global_type.idl_type == idl_type:
            swift_type = global_type.name
            if not swift_type.startswith('matter4swift.'):
                swift_type = f'matter4swift.{swift_type}'
            break
    if not swift_type:
        swift_type = idl_type
    if is_array:
        swift_type = f'[{swift_type}]'
    return f'{swift_type}InputView'


def AttributeName(attribute:Attribute) -> str:
    return attribute.definition.name[:1].upper() + attribute.definition.name[1:]

def CreateLookupContext(idl: Idl, cluster: Optional[Cluster]) -> TypeLookupContext:
    """
    A filter to mark a lookup context to be within a specific cluster.

    This is used to specify how structure/enum/other names are looked up.
    Generally one looks up within the specific cluster then if cluster does
    not contain a definition, we loop at global namespacing.
    """
    return TypeLookupContext(idl, cluster)

def IsReadable(attribute:Attribute):
    return  AttributeQuality.READABLE in attribute.qualities

def IsWritable(attribute:Attribute):
    return  AttributeQuality.WRITABLE in attribute.qualities

def IsNullable(field:Field) -> bool:
    return FieldQuality.NULLABLE in field.qualities or FieldQuality.OPTIONAL in field.qualities

def IsStruct(field:Field, context: TypeLookupContext) -> bool:
    struct = context.find_struct(field.data_type.name)
    if field.name == 'size':
        raise Exception()
    return struct is not None

def IsBitmap(field:Field, context: TypeLookupContext) -> bool:
    bitmap = context.find_bitmap(field.data_type.name)
    return bitmap is not None

def GetStructFields(field:Field, context: TypeLookupContext):
    struct = context.find_struct(field.name)
    return struct.fields


def GetStructFieldsByName(name:str, context: TypeLookupContext):
    struct = context.find_struct(name)
    return struct.fields if struct else None


def GetCommandResponseType(command:Command, context: TypeLookupContext):
    """
    Return response type of the command.
    """
    return SwiftType(command.output_param, context)
    return command.output_param


def StripAllNewlines(s:str) -> str:
    lines = s.split("\n")
    lines = [l.strip() for l in lines]
    return " ".join(lines)

class CustomGenerator(CodeGenerator):
    """
    Example of a custom generator.  Outputs protobuf representation of Matter clusters.
    """

    def __init__(self, storage: GeneratorStorage, idl: Idl, **kwargs):
        super().__init__(storage, idl, fs_loader_searchpath=os.path.dirname(__file__))

        if not 'output' in kwargs:
            raise Exception("output directory must be provided using '--option output:<directory>'")

        self.output_directory = pathlib.Path(kwargs['output'])
        self.name = kwargs.get('name', 'TriforkMatters')
        self.generate_views = 'generate_views' in kwargs
        self.cluster_filter = kwargs.get('filter', 'all')

        self.jinja_env.filters['swift_type'] = SwiftType
        self.jinja_env.filters['swift_ui_view_type'] = SwiftUIViewType
        self.jinja_env.filters['createLookupContext'] = CreateLookupContext
        self.jinja_env.filters['attribute_name'] = AttributeName
        self.jinja_env.filters['is_readable'] = IsReadable
        self.jinja_env.filters['is_writable'] = IsWritable
        self.jinja_env.filters['is_nullable']= IsNullable
        self.jinja_env.filters['is_struct'] = IsStruct
        self.jinja_env.filters['is_bitmap'] = IsBitmap
        self.jinja_env.filters['strip_all'] = StripAllNewlines
        self.jinja_env.filters['struct_fields'] = GetStructFields
        self.jinja_env.filters['struct_fields_by_name'] = GetStructFieldsByName
        self.jinja_env.filters['response_type'] = GetCommandResponseType
        self.jinja_env.globals['swift'] = {
            'base_name': self.name,
            'generated_at': datetime.datetime.now(datetime.UTC).isoformat(timespec='seconds')
        }

    def _get_output_name(self, filename, is_sources:bool = True):
        """
        Returns the path to the output file, given the filename and the
        output directory specified on the command-line.
        """
        if is_sources:
            return str(self.output_directory / 'Sources' / self.name / pathlib.Path(filename))
        else:
            return str(self.output_directory / pathlib.Path(filename))

    def internal_render_all(self):
        if self.cluster_filter == 'all':
            clusters = self.idl.clusters
        elif self.cluster_filter == 'server_side':
            clusters = server_side_clusters(self.idl)
        elif self.cluster_filter == 'binding':
            clusters = binding_clusters(self.idl)
        else:
            raise Exception(f"'{self.cluster_filter}' is not a valid option for '--option filter:{{all|server_side|binding}}'")

        # Generate Swift classes for each server cluster.
        cluster_targets = [
            GenerateTarget(
                template="templates/ChipCluster.jinja",
                output_name=self._get_output_name("{cluster_name}Cluster.swift")
            )
        ]
        # Optionally generate SwiftUI views for each server cluster.
        if self.generate_views:
            cluster_targets += [
                GenerateTarget(
                    template="templates/ChipClusterView.jinja",
                    output_name=self._get_output_name("{cluster_name}ClusterView.swift")
                ),
            ]

        for cluster in clusters:
            for target in cluster_targets:
                self.internal_render_one_output(
                    template_path=target.template,
                    output_file_name=target.output_name.format(cluster_name=cluster.name),
                    vars={
                        'cluster': cluster,
                        'typeLookup': TypeLookupContext(self.idl, cluster),
                        'globalTypes': _GLOBAL_TYPES,
                    }
                )
        
        # Generate Swift class for looking up cluster descriptions.
        description_targets = [
            GenerateTarget(
                template="templates/ChipDescriptions.jinja",
                output_name=self._get_output_name("Descriptions.swift")
            ),
        ]
        # Optionally generate SwiftUI view that produces a NavigationLink
        # for each cluster.
        if self.generate_views:
            description_targets += [
                GenerateTarget(
                    template="templates/ChipClientIdView.jinja",
                    output_name=self._get_output_name("ClientIdView.swift")
                ),
            ]

        for target in description_targets:
            self.internal_render_one_output(
                template_path=target.template,
                output_file_name=target.output_name.format(cluster_name=cluster.name),
                vars={
                    'clusters': clusters,
                }
            )

        # Generate Swift.package file.
        package_targets = [
            GenerateTarget(
                template="templates/Package.swift.jinja",
                output_name=self._get_output_name("Package.swift", is_sources=False)
            ),
        ]
        for target in package_targets:
            self.internal_render_one_output(
                template_path=target.template,
                output_file_name=target.output_name.format('Package.swift'),
                vars={
                    'package_name': self.name,
                    'clusters': clusters,
                }
            )

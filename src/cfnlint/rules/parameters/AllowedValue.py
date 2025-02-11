"""
  Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.

  Permission is hereby granted, free of charge, to any person obtaining a copy of this
  software and associated documentation files (the "Software"), to deal in the Software
  without restriction, including without limitation the rights to use, copy, modify,
  merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
  permit persons to whom the Software is furnished to do so.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
  INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
  PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
  HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
  OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
  SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
import six
from cfnlint.rules import CloudFormationLintRule
from cfnlint.rules import RuleMatch

from cfnlint.helpers import RESOURCE_SPECS


class AllowedValue(CloudFormationLintRule):
    """Check if parameters have a valid value"""
    id = 'W2030'
    shortdesc = 'Check if parameters have a valid value'
    description = 'Check if parameters have a valid value in case of an enumator. The Parameter''s allowed values is based on the usages in property (Ref)'
    source_url = 'https://github.com/aws-cloudformation/cfn-python-lint/blob/master/docs/cfn-resource-specification.md#allowedvalue'
    tags = ['resources', 'property', 'allowed value']

    def initialize(self, cfn):
        """Initialize the rule"""
        for resource_type_spec in RESOURCE_SPECS.get(cfn.regions[0]).get('ResourceTypes'):
            self.resource_property_types.append(resource_type_spec)
        for property_type_spec in RESOURCE_SPECS.get(cfn.regions[0]).get('PropertyTypes'):
            self.resource_sub_property_types.append(property_type_spec)

    def check_value_ref(self, value, path, **kwargs):
        """Check Ref"""
        matches = []

        if 'Fn::If' in path:
            self.logger.debug('Not able to guarentee that the default value hasn\'t been conditioned out')
            return matches

        allowed_value_specs = kwargs.get('value_specs', {}).get('AllowedValues', {})
        cfn = kwargs.get('cfn')

        if allowed_value_specs:
            if value in cfn.template.get('Parameters', {}):
                param = cfn.template.get('Parameters').get(value, {})
                parameter_values = param.get('AllowedValues')
                default_value = param.get('Default')
                parameter_type = param.get('Type')
                if isinstance(parameter_type, six.string_types):
                    if ((not parameter_type.startswith('List<')) and
                            (not parameter_type.startswith('AWS::SSM::Parameter::Value<')) and
                            parameter_type not in ['CommaDelimitedList', 'List<String>']):
                        # Check Allowed Values
                        if parameter_values:
                            for index, allowed_value in enumerate(parameter_values):
                                if str(allowed_value) not in allowed_value_specs:
                                    param_path = ['Parameters', value, 'AllowedValues', index]
                                    message = 'You must specify a valid allowed value for {0} ({1}).\nValid values are {2}'
                                    matches.append(RuleMatch(param_path, message.format(value, allowed_value, allowed_value_specs)))
                        if default_value:
                            # Check Default, only if no allowed Values are specified in the parameter (that's covered by E2015)
                            if str(default_value) not in allowed_value_specs:
                                param_path = ['Parameters', value, 'Default']
                                message = 'You must specify a valid Default value for {0} ({1}).\nValid values are {2}'
                                matches.append(RuleMatch(param_path, message.format(value, default_value, allowed_value_specs)))

        return matches

    def check(self, cfn, properties, value_specs, property_specs, path):
        """Check itself"""
        matches = list()
        for p_value, p_path in properties.items_safe(path[:]):
            for prop in p_value:
                if prop in value_specs:
                    value = value_specs.get(prop).get('Value', {})
                    if value:
                        value_type = value.get('ValueType', '')
                        property_type = property_specs.get('Properties').get(prop).get('Type')
                        matches.extend(
                            cfn.check_value(
                                p_value, prop, p_path,
                                check_ref=self.check_value_ref,
                                value_specs=RESOURCE_SPECS.get(cfn.regions[0]).get('ValueTypes').get(value_type, {}),
                                cfn=cfn, property_type=property_type, property_name=prop
                            )
                        )

        return matches

    def match_resource_sub_properties(self, properties, property_type, path, cfn):
        """Match for sub properties"""
        matches = list()

        specs = RESOURCE_SPECS.get(cfn.regions[0]).get('PropertyTypes').get(property_type, {}).get('Properties', {})
        property_specs = RESOURCE_SPECS.get(cfn.regions[0]).get('PropertyTypes').get(property_type)
        matches.extend(self.check(cfn, properties, specs, property_specs, path))

        return matches

    def match_resource_properties(self, properties, resource_type, path, cfn):
        """Check CloudFormation Properties"""
        matches = list()

        specs = RESOURCE_SPECS.get(cfn.regions[0]).get('ResourceTypes').get(resource_type, {}).get('Properties', {})
        resource_specs = RESOURCE_SPECS.get(cfn.regions[0]).get('ResourceTypes').get(resource_type)
        matches.extend(self.check(cfn, properties, specs, resource_specs, path))

        return matches

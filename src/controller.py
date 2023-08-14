from math import degrees

from typing import Dict

import yaml
from fuzzy.storage.fcl.Reader import Reader
from models import FuzzyVar, FuzzyRule

from shapely.geometry import Point, LineString, Polygon
from shapely.ops import cascaded_union


class FuzzyController:
    def __init__(self, fcl_path):
        self.system = Reader().load_from_file(fcl_path)
        self.fuzzy_vars, self.fuzzy_rules = self.read_fuzzy_problem()

    @staticmethod
    def _make_input(world):
        return dict(
            cp=world.x,
            cv=world.v,
            pa=degrees(world.theta),
            pv=degrees(world.omega)
        )

    @staticmethod
    def _make_output():
        return dict(
            force=0.
        )

    def old_decide(self, world):
        output = self._make_output()
        self.system.calculate(self._make_input(world), output)
        return output['force']

    def decide(self, world):
        _input = self._make_input(world)

        _input = self.normalize(_input)
        inferences = self.infer(_input)
        force = self.defuzzify(inferences)

        old_force = self.old_decide(world)
        if round(force, 5) != round(old_force, 5):
            print "For tis _input our result is different than pyfuzzy result", _input
            quit()

        return force

    def read_fuzzy_problem(self):
        fuzzy_vars = {}
        fuzzy_rules = []
        with open('input.yml', 'r') as f:
            data = yaml.safe_load(f)

            for var_dict in data.get('fuzzy_vars', []):
                var_name = var_dict['name']
                var_obj = FuzzyVar.from_dict(var_dict)

                fuzzy_vars[var_name] = var_obj

            for rule_dict in data.get('fuzzy_rules', []):
                fuzzy_rule = FuzzyRule.from_dict(rule_dict)
                fuzzy_rules.append(fuzzy_rule)

        return fuzzy_vars, fuzzy_rules

    @staticmethod
    def normalize(_input):
        if _input['pv'] < -200:
            _input['pv'] = -200
        if _input['pv'] > 200:
            _input['pv'] = 200

        return _input

    def infer(self, _input):
        inferences = {}
        for rule in self.fuzzy_rules:
            conclusion_set = rule.conclusion.set

            conclusion_membership_value = self.infer_from_rule(_input, rule)

            inferences[conclusion_set] = max(
                inferences.get(conclusion_set, 0), conclusion_membership_value
            )

        return inferences

    def infer_from_rule(self, _input, rule):
        # type: (FuzzyController, Dict[str, float], FuzzyRule) -> float
        # TODO clean this function
        arg_1_var, arg_1_set = rule.statement_1.var, rule.statement_1.set
        arg_1_membership_value = self.fuzzy_vars[arg_1_var].get_input_membership_value_in_set(
            arg_1_set, _input[arg_1_var]
        )

        arg_2_var, arg_2_set = rule.statement_2.var, rule.statement_2.set
        arg_2_membership_value = self.fuzzy_vars[arg_2_var].get_input_membership_value_in_set(
            arg_2_set, _input[arg_2_var]
        )

        return rule.operator_func(arg_1_membership_value, arg_2_membership_value)

    def defuzzify(self, inferences):
        force_fuzzy = self.fuzzy_vars['force']

        polygons = []
        for _set_name in inferences.keys():
            y = inferences.get(_set_name, 0)
            if y == 0:
                continue
            points = force_fuzzy.fuzzy_sets[_set_name].line.set_max_y(y)
            polygons.append(
                Polygon([point.to_tuple() for point in points])
            )

        polygons_union = cascaded_union(polygons)
        polygons_union_centroid = polygons_union.centroid
        polygons_union_centroid_x = 0.0
        if not polygons_union_centroid.is_empty:
            polygons_union_centroid_x = polygons_union_centroid.x

        return polygons_union_centroid_x

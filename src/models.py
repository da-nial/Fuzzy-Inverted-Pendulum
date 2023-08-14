from abc import ABCMeta, abstractmethod
from typing import Dict, List, Tuple

import re

STATEMENT_PATTERN = r"\w+ IS \w+"
GROUP_PATTERN = r"\(([^\)]+)\)"


class FuzzyRule:
    @classmethod
    def from_dict(cls, _dict):
        rule = _dict['rule']
        hypothesis, conclusion_str = rule.split("THEN")

        arg_var, arg_set = conclusion_str.split('IS')
        conclusion = Statement(arg_var, arg_set)

        operator = "AND"
        if "OR" in hypothesis:
            operator = "OR"

        hypothesis_statements = []
        statements_str = re.findall(GROUP_PATTERN, hypothesis)
        for statement_str in statements_str:
            # Example statement_string: `pa IS up_more_right`
            # arg_var: pa, arg_set: up_more_right
            arg_var, arg_set = statement_str.split("IS")
            statement = Statement(arg_var, arg_set)
            hypothesis_statements.append(statement)

        return cls(hypothesis_statements, operator, conclusion)

    def __init__(self, hypothesis_statements, operator, conclusion):
        self.statement_1, self.statement_2 = hypothesis_statements
        self.operator = operator
        self.conclusion = conclusion

    @property
    def operator_func(self):
        operator_to_func = {
            'AND': min,
            'OR': max,
        }
        return operator_to_func[self.operator]


class Statement:
    def __init__(self, var, _set):
        var = var.rstrip()
        var = var.lstrip()

        _set = _set.rstrip()
        _set = _set.lstrip()

        self.var = var
        self.set = _set

    def __str__(self):
        return "var[{}] IS set[{}]".format(self.var, self.set)


class FuzzyVar:
    @classmethod
    def from_dict(cls, _dict):
        # type: (FuzzyVar, Dict) -> FuzzyVar
        name = _dict['name']
        fuzzy_sets = {}
        for _set in _dict.get('sets', []):
            _set_name = _set['name']
            _set_points = _set['points']
            _set_line = None
            if len(_set_points) == 2:
                p_1 = Point(**_set['points'][0])
                p_2 = Point(**_set['points'][1])
                _set_line = LinearLine(p_1, p_2)
            elif len(_set_points) == 3:
                p_1 = Point(**_set['points'][0])
                p_2 = Point(**_set['points'][1])
                p_3 = Point(**_set['points'][2])
                _set_line = Triangle(p_1, p_2, p_3)

            fuzzy_sets[_set_name] = FuzzySet(_set_name, _set_line)

        return cls(name, fuzzy_sets)

    def __init__(self, name, fuzzy_sets):
        # type: (FuzzyVar, str, Dict[str, FuzzySet]) -> None
        self.name = name
        self.fuzzy_sets = fuzzy_sets

    def get_input_membership_values(self, _input):
        # type: (FuzzyVar, float) -> Dict[str, float]
        membership_values = {}
        for set_name, set_line in self.fuzzy_sets:
            try:
                membership_value = set_line.get_y(_input)
            except ValueError:
                membership_value = 0
            membership_values[set_name] = membership_value

        return membership_values

    def get_input_membership_value_in_set(self, set_name, _input):
        # type: (FuzzyVar, str, float) -> float
        try:
            fuzzy_set = self.fuzzy_sets[set_name]
        except KeyError:
            raise KeyError("FuzzyVariable {} sets do not include {} set".format(self.name, set_name))

        try:
            membership_value = fuzzy_set.get_membership(_input)
        except ValueError:
            membership_value = 0

        return membership_value


class FuzzySet:
    def __init__(self, name, line):
        # type: (FuzzySet, str, Line) -> None
        self.name = name
        self.line = line

    def __str__(self):
        return "FuzzySet[{}]".format(self.name)

    def get_membership(self, x):
        # type: (FuzzySet, float) -> float
        return self.line.get_y(x)


class Line:
    __metaclass__ = ABCMeta

    @abstractmethod
    def get_y(self, x):
        pass

    @abstractmethod
    def get_x(self, y):
        pass


class Triangle(Line):
    def __init__(self, p_1, p_2, p_3):
        # type: (Triangle, Point, Point, Point) -> None
        self.p_1 = p_1
        self.p_2 = p_2
        self.p_3 = p_3

        self.line_1 = LinearLine(p_1, p_2)
        self.line_2 = LinearLine(p_2, p_3)

    def __str__(self):
        # type: () -> str
        return "Triangle: p_1: {}, p_2: {}, p_3: {}".format(self.p_1, self.p_2, self.p_3)

    def get_y(self, x):
        # type: (Triangle, float) -> float
        if self.line_1.does_cover(x):
            y = self.line_1.get_y(x)
            return y
        elif self.line_2.does_cover(x):
            y = self.line_2.get_y(x)
            return y
        else:
            raise ValueError("Triangle Object with points {} {} {} doesn't cover x={}".format(
                self.p_1, self.p_2, self.p_3, x
            ))

    def get_x(self, y):
        # type: (Point, float) -> List[float]
        x_in_line_1, x_in_line_2 = None, None
        try:
            x_in_line_1 = self.line_1.get_x(y)[0]
        except KeyError:
            print "y = {} does not exist in line {}".format(y, self.line_1)

        try:
            x_in_line_2 = self.line_2.get_x(y)[0]
        except KeyError:
            print "y = {} does not exist in line {}".format(y, self.line_2)

        return [x_in_line_1, x_in_line_2]

    def set_max_y(self, y):
        """
        :return: a polygan (Trapezoid or Triangle) created by setting a max height for the polygan.
        """
        x_1, x_2 = self.get_x(y)
        return [self.p_1, Point(x_1, y), Point(x_2, y), self.p_3]


class LinearLine(Line):
    def __init__(self, p_1, p_2):
        # type: (LinearLine, Point, Point) -> None
        if p_1.x == p_2.x:
            raise ValueError(
                "LinearLine can't create vertical lines, inputs: {}, {} have same x".format(
                    p_1, p_2
                )
            )
        self.slope = (p_2.y - p_1.y) / (p_2.x - p_1.x)
        self.y_intercept = -(self.slope * p_1.x) + p_1.y

        self.p_1 = p_1
        self.p_2 = p_2

    def __str__(self):
        # type: () -> str
        return "LinearLine: p_1: {}, p_2: {}".format(self.p_1, self.p_2)

    def get_y(self, x):
        # type: (LinearLine, float) -> float
        if self.does_cover(x):
            y = (self.slope * x) + self.y_intercept
            return y
        else:
            raise ValueError

    def get_x(self, y):
        # type: (LinearLine, float) -> List[float]
        x = (y - self.y_intercept) / self.slope
        if self.does_cover(x):
            return [x, ]
        else:
            raise ValueError

    def does_cover(self, x):
        # type: (Point, float) -> bool
        return self.p_1.x <= x <= self.p_2.x


class Point:
    def __init__(self, x, y):
        # type: (Point, float, float) -> None
        self.x = float(x)
        self.y = float(y)

    def __str__(self):
        # type: (Point) -> str
        return "[x={}, y={}]".format(self.x, self.y)

    def to_tuple(self):
        # type: (Point) -> Tuple[float, float]
        return self.x, self.y

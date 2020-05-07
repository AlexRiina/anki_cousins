from typing import NamedTuple, Iterable, List, Dict, Union
import enum
import difflib


Serializeable = Union[int, str, float]


class Comparisons(enum.Enum):
    similarity = 1
    prefix = 2
    contains = 3
    contained_by = 4


class MatchRule(NamedTuple):
    my_note_model_id: int
    my_field: str
    cousin_note_model_id: int
    cousin_field: str
    comparison: Comparisons
    threshold: float

    def test(self, a: str, b: str) -> bool:
        comparison = self.comparison

        if comparison == Comparisons.similarity:
            return _similarityTest(a, b, self.threshold)
        elif comparison == Comparisons.prefix:
            return _commonPrefixTest(a, b, self.threshold)
        raise ValueError("unrecognized comparison test")


class SettingsManager:
    key = "anki_cousins"

    def __init__(self, col):
        self.col = col

    def load(self) -> List[MatchRule]:
        return [self._deserialize_rule(row) for row in self.col.conf.get(self.key, [])]

    def save(self, match_rules: Iterable[MatchRule]):
        self.col.conf[self.key] = sorted(
            [list(self._serialize_rule(match_rule).values()) for match_rule in match_rules]
        )

        self.col.setMod()

    @staticmethod
    def _deserialize_rule(stored: List[Serializeable]) -> MatchRule:
        rule_dict = dict(zip(MatchRule._fields, stored))
        comparison = Comparisons[rule_dict.pop('comparison')]  # type: ignore
        return MatchRule(comparison=comparison, **rule_dict)  # type: ignore

    @staticmethod
    def _serialize_rule(rule: MatchRule) -> Dict[str, Serializeable]:
        rule_dict = rule._asdict()
        rule_dict['comparison'] = rule.comparison.name
        return rule_dict


def _commonPrefixTest(a: str, b: str, percent_match: float) -> bool:
    # don't accidentally run on empty cards. rather be safe
    if max(len(a), len(b)) < 5:
        return False

    for i, (al, bl) in enumerate(zip(a, b)):
        if al != bl:
            break
    else:
        i = i + 1

    return i > percent_match * max(len(a), len(b))


def _similarityTest(a: str, b: str, percent_match: float) -> bool:
    # don't accidentally run on empty cards. rather be safe
    if max(len(a), len(b)) < 5:
        return False

    return difflib.SequenceMatcher(None, a, b).ratio() > percent_match

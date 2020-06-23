import re
from typing import NamedTuple, Iterable, List, Dict, Union
from functools import lru_cache
import enum
import difflib


Serializeable = Union[int, str, float]


class Comparisons(enum.Enum):
    similarity = 1
    prefix = 2
    contains = 3
    contained_by = 4
    cloze_contained_by = 5


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
        elif comparison == Comparisons.contains:
            return _contains(a, b, self.threshold)
        elif comparison == Comparisons.contained_by:
            return _contained_by(a, b, self.threshold)
        elif comparison == Comparisons.cloze_contained_by:
            return _cloze_contained_by()(a, b, self.threshold)
        raise ValueError("unrecognized comparison test")


class SettingsManager:
    key = "anki_cousins"

    def __init__(self, col):
        self.col = col

    def load(self) -> List[MatchRule]:
        return [self._deserialize_rule(row) for row in self.col.conf.get(self.key, [])]

    def save(self, match_rules: Iterable[MatchRule]):
        self.col.conf[self.key] = sorted(
            [
                list(self._serialize_rule(match_rule).values())
                for match_rule in match_rules
            ]
        )

        self.col.setMod()

    @staticmethod
    def _deserialize_rule(stored: List[Serializeable]) -> MatchRule:
        rule_dict = dict(zip(MatchRule._fields, stored))
        comparison = Comparisons[rule_dict.pop("comparison")]  # type: ignore
        return MatchRule(comparison=comparison, **rule_dict)  # type: ignore

    @staticmethod
    def _serialize_rule(rule: MatchRule) -> Dict[str, Serializeable]:
        rule_dict = rule._asdict()
        rule_dict["comparison"] = rule.comparison.name
        return rule_dict


def _commonPrefixTest(a: str, b: str, percent_match: float) -> bool:
    # don't accidentally run on empty cards. rather be safe
    if min(len(a), len(b)) < 4:
        return False

    for i, (al, bl) in enumerate(zip(a, b)):
        if al != bl:
            break
    else:
        i = i + 1

    return i > percent_match * max(len(a), len(b))


def _similarityTest(a: str, b: str, percent_match: float) -> bool:
    """
    >>> _similarityTest('xxxyyy', 'xxyxyy', 0.8)
    True

    >>> _similarityTest('xxxyyy', 'xxyxyy', 0.9)
    False

    >>> _similarityTest('hello', 'hello this is a test', 0.5)
    False
    """
    #// removing the extra parts in cloze deletions to maximize accuracy
    #// turns 'this is a {{c1::cloze::whaaaat??}} {{c2::test:what did you say}}'
    # into this is a cloze test
    texta = a.replace('}}', '::a}}')
    texta2 = re.sub('{{.+?::', '', texta)
    texta3 = re.sub('::.+?}}', '', texta2)
    textb = b.replace('}}', '::a}}')
    textb2 = re.sub('{{.+?::', '', textb)
    textb3 = re.sub('::.+?}}', '', textb2)
    # don't accidentally run on empty cards. rather be safe
    if max(len(a), len(b)) < 4:
        return False

    return difflib.SequenceMatcher(None, texta3.lower(), textb3.lower()).ratio() > percent_match


def _contained_by(a: str, b: str, threshold: float):
    return len(a) > 3 and a in b


def _contains(a: str, b: str, threshold: float):
    return _contained_by(b, a, threshold)


class _cloze_contained_by:
    """ terms in cloze deletion a contained anywhere in b

    >>> _cloze_contained_by()('{{c1::hello}}', 'test hello test', 1)
    True

    >>> _cloze_contained_by()('{{c1::hello::greeting}}', 'test hello test', 1)
    True

    >>> _cloze_contained_by()('{{c1::hello}}', 'bye', 1)
    False

    >>> _cloze_contained_by()('Phase {{c1::2::#N}} clinical trial', '2 x 2', 1)
    False
    """

    def __call__(self, a: str, b: str, threshold: float):
        return any(cloze_answer.search(b) for cloze_answer in self._extra_answers(a))

    @classmethod
    @lru_cache
    def _extra_answers(self, a: str) -> List[re.Pattern]:
        # locally cached so for each a vs b comparison we don't re-extract
        # answers from a
        return [
            re.compile(r"\b{}\b".format(re.escape(match.group("answer"))))
            for match in re.finditer(r"{{(?P<group>.*?)::(?P<answer>.*?)(::.*?)?}}", a)
            # don't accidentally suppress on concepts like "2"
            if len(match.group("answer")) > 3
        ]

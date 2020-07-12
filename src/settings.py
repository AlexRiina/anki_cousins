import difflib
import enum
import re
from functools import lru_cache, wraps
from typing import Callable, Dict, Iterable, List, NamedTuple, Tuple, Union

Serializeable = Union[int, str, float]
CLOZE_EXTRACT = re.compile(r"{{(?P<group>.*?)::(?P<answer>.*?)(::.*?)?}}")


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

    def test(self, a: List[str], b: List[str]) -> List[Tuple[str, str]]:
        comparison = self.comparison

        if comparison == Comparisons.similarity:
            return _similarity_test()(a, b, self.threshold)
        elif comparison == Comparisons.prefix:
            return _commonPrefixTest(a, b, self.threshold)
        elif comparison == Comparisons.contains:
            return _contains(a, b, self.threshold)
        elif comparison == Comparisons.contained_by:
            return _contained_by(a, b, self.threshold)
        elif comparison == Comparisons.cloze_contained_by:
            return _cloze_contained_by()(a, b, self.threshold)
        raise ValueError("unrecognized comparison test")


def _one_by_one(
    test_func: Callable[[str, str, float], bool]
) -> Callable[[List[str], List[str], float], List[Tuple[str, str]]]:
    """ convert boolean comparison function to list based comparisons """

    @wraps(test_func)
    def inner(list_a, list_b, threshold):
        results = []

        for a in list_a:
            for b in list_b:
                if test_func(a, b, threshold):
                    results.append((a, b))

        return results

    return inner


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


def _commonPrefixTest(list_a: List[str], list_b: List[str], percent_match: float) -> List[Tuple[str, str]]:
    """
    >>> _commonPrefixTest(['abcdefg'], ['abcdexx'], 0.65)
    [('abcdefg', 'abcdexx')]

    >>> _commonPrefixTest(['abcdefg'], ['abcdexx'], 0.95)
    []
    """
    # don't accidentally run on empty cards. rather be safe
    list_a = [a for a in list_a if len(a) >= 4]
    list_b = [a for a in list_b if len(a) >= 4]

    # sort both lists by length

    results = []
    for a in list_a:
        for b in list_b:
            for i, (al, bl) in enumerate(zip(a, b)):
                if al != bl:
                    break
            else:
                i = i + 1

            if i > percent_match * max(len(a), len(b)):
                results.append((a, b))

    return results


class _similarity_test:
    """
    >>> bool(_similarity_test()(['xxxyyy'], ['xxyxyy'], 0.8))
    True

    >>> bool(_similarity_test()(['xxxyyy'], ['xxyxyy'], 0.9))
    False

    >>> bool(_similarity_test()(['||c1::this|| that'], ['this ||c1::that::noun||'], 0.9))
    False

    >>> bool(_similarity_test()(['{{c1::this}}&nbsp;that'], ['this {{c1::that::noun}}'], 0.9))
    True

    >>> bool(_similarity_test()(['hello'], ['hello this is a test'], 0.5))
    False
    """

    @staticmethod
    @_one_by_one
    def __call__(a: str, b: str, percent_match: float) -> bool:
        # don't accidentally run on empty cards. rather be safe

        a = _similarity_test._preprocess(a)
        b = _similarity_test._preprocess(b)

        if max(len(a), len(b)) < 4:
            return False

        return difflib.SequenceMatcher(None, a, b).ratio() > percent_match

    @classmethod
    @lru_cache
    def _preprocess(self, a: str) -> str:
        # replace html entity that gets frequently entered in cloze cards
        a = a.replace("&nbsp;", " ")

        return CLOZE_EXTRACT.sub(r"\g<answer>", a).lower()


@_one_by_one
def _contained_by(a: str, b: str, threshold: float):
    return len(a) > 3 and a in b


def _contains(a: List[str], b: List[str], threshold: float):
    return _contained_by(b, a, threshold)


class _cloze_contained_by:
    """ terms in cloze deletion a contained anywhere in b

    >>> bool(_cloze_contained_by()(['{{c1::hello}}'], ['test hello test'], 1))
    True

    >>> bool(_cloze_contained_by()(['{{c1::hello::greeting}}'], ['test hello test'], 1))
    True

    >>> bool(_cloze_contained_by()(['{{c1::hello}}'], ['bye'], 1))
    False

    >>> bool(_cloze_contained_by()(['Phase {{c1::2::#N}} clinical trial'], ['2 x 2'], 1))
    False
    """

    @staticmethod
    @_one_by_one
    def __call__(a: str, b: str, threshold: float):
        return any(
            cloze_answer.search(b)
            for cloze_answer in _cloze_contained_by._extra_answers(a)
        )

    @classmethod
    @lru_cache
    def _extra_answers(self, a: str) -> List[re.Pattern]:
        # locally cached so for each a vs b comparison we don't re-extract
        # answers from a

        return [
            re.compile(r"\b{}\b".format(re.escape(match.group("answer"))))
            for match in CLOZE_EXTRACT.finditer(a)
            # don't accidentally suppress on concepts like "2"
            if len(match.group("answer")) > 3
        ]

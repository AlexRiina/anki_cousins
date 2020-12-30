import difflib
import enum
import re
from collections import defaultdict
from functools import lru_cache, wraps
from itertools import product
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
        return [
            self._deserialize_rule(row) for row in self.col.get_config(self.key, [])
        ]

    def save(self, match_rules: Iterable[MatchRule]):
        self.col.set_config(
            self.key,
            sorted(
                [
                    list(self._serialize_rule(match_rule).values())
                    for match_rule in match_rules
                ]
            ),
        )

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


def _commonPrefixTest(
    list_a: List[str], list_b: List[str], percent_match: float
) -> List[Tuple[str, str]]:
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
    >>> _similarity_test()(['xxxyyy'], ['xxyxyy'], 0.8)
    [('xxxyyy', 'xxyxyy')]

    >>> _similarity_test()(['xxxyyy'], ['xxyxyy'], 0.9)
    []

    >>> _similarity_test()(['||c1::this|| that'], ['this ||c1::that::noun||'], 0.9)
    []

    >>> _similarity_test()(['{{c1::this}}&nbsp;that'], ['this {{c1::that::noun}}'], 0.9)
    [('{{c1::this}}&nbsp;that', 'this {{c1::that::noun}}')]

    >>> _similarity_test()(['hello'], ['hello this is a test'], 0.5)
    []
    """

    @staticmethod
    def __call__(
        list_a: List[str], list_b: List[str], percent_match: float
    ) -> List[Tuple[str, str]]:
        def transform(list_x) -> Dict[str, List[str]]:
            """ flattened: [original values] """
            mapping = defaultdict(list)

            for x in list_x:
                x_ = _similarity_test._preprocess(x)

                # don't accidentally run on empty cards. rather be safe
                if len(x_) >= 4:
                    mapping[x_].append(x)

            return dict(mapping)

        mapping_a = transform(list_a)
        mapping_b = transform(list_b)

        results = []

        for transformed_a, original_as in mapping_a.items():
            # hope that you don't have more than 10 cousins
            # python gets the return type of get_close_matches wrong
            matches: List[str]

            matches = difflib.get_close_matches(
                transformed_a, list(mapping_b.keys()), n=10, cutoff=percent_match
            )  # type: ignore

            results.extend(
                [
                    (a, b)
                    for transformed_b in matches
                    for a, b in product(original_as, mapping_b[transformed_b])
                ]
            )

        return results

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
    """terms in cloze deletion a contained anywhere in b

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

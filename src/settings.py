from typing import NamedTuple, Iterable, List
import difflib


class MatchRule(NamedTuple):
    my_note_model_id: int
    my_field: str
    cousin_note_model_id: int
    cousin_field: str
    comparison: str
    threshold: float

    def test(self, a: str, b: str) -> bool:
        if self.comparison == "similarity":
            return _similarityTest(a, b, self.threshold)
        elif self.comparison == "prefix":
            return _commonPrefixTest(a, b, self.threshold)
        raise ValueError("unrecognized comparison test")


class SettingsManager:
    key = "anki_cousins"

    def __init__(self, col):
        self.col = col

    def load(self) -> List[MatchRule]:
        return [MatchRule._make(row) for row in self.col.conf.get(self.key, [])]

    def save(self, match_rules: Iterable[MatchRule]):
        self.col.conf[self.key] = sorted(
            [list(match_rule._asdict().values()) for match_rule in match_rules]
        )

        self.col.setMod()


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

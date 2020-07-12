from collections import defaultdict
from typing import TYPE_CHECKING, DefaultDict, Iterable, List, Set, Tuple, Union

from anki.collection import _Collection as Collection
from anki.consts import (
    QUEUE_TYPE_MANUALLY_BURIED,
    QUEUE_TYPE_NEW,
    QUEUE_TYPE_REV,
    QUEUE_TYPE_SIBLING_BURIED,
)
from anki.models import NoteType
from anki.notes import Note
from anki.sched import Scheduler
from anki.schedv2 import Scheduler as SchedulerV2
from anki.utils import ids2str, intTime, splitFields, stripHTMLMedia

from aqt.utils import tooltip  # type: ignore

from .settings import SettingsManager

SomeScheduler = Union[Scheduler, SchedulerV2]

if TYPE_CHECKING:
    from anki.cards import Card


def buryCousins(self: SomeScheduler, card: "Card") -> None:
    """ bury related cards that aren't marked as siblings

    Same as Anki: always delete from current rehearsal and if bury new / bury
    review are set in deck options, bury until tomorrow
    """
    # implementation mirrors anki's _burySiblings without the options

    buryNew, buryRev = _buryConfig(self, card)

    toBury: Set[int] = set()  # note ids

    my_note = card.note()

    def field_value(note, field_name) -> str:
        note_type = self.col.models.get(note.mid)
        field_number = self.col.models.fieldMap(note_type)[field_name][0]

        return note.fields[field_number]

    config = SettingsManager(self.col).load()

    for rule in config:
        if rule.my_note_model_id != my_note.mid:
            continue

        potential_cousin_notes = [
            note
            for note in _scheduledNotes(self)
            if rule.cousin_note_model_id == note.mid and my_note.id != note.id
        ]

        my_value = field_value(my_note, rule.my_field)
        cousin_values = [
            field_value(cousin_note, rule.cousin_field)
            for cousin_note in potential_cousin_notes
        ]

        matches = rule.test([my_value], cousin_values)

        for cousin_note in potential_cousin_notes:
            cousin_value = field_value(cousin_note, rule.cousin_field)

            if (my_value, cousin_value) in matches:
                # not super efficient, could just look up cids all at the end
                toBury.add(cousin_note.id)

    cousin_cards = list(_cousinCards(self, toBury))

    for cid, queue in cousin_cards:
        try:
            (self._revQueue if queue == QUEUE_TYPE_REV else self._newQueue).remove(cid)
        except ValueError:
            # I'm not sure why things end up here but anki protects against
            # this. It may be needed if the card is scheduled on a different
            # deck so it doesn't appear in the current learning queue.
            pass

    if cousin_cards:
        tooltip("burying %d cousin card" % len(cousin_cards))

    card_ids_to_bury = [
        id
        for id, queue in cousin_cards
        if (buryNew and queue == QUEUE_TYPE_NEW)
        or (buryRev and queue == QUEUE_TYPE_REV)
    ]

    if isinstance(self, Scheduler):
        buryCards(self, card_ids_to_bury)
    else:
        self.buryCards(card_ids_to_bury, manual=False)


def _buryConfig(self: SomeScheduler, card: "Card"):
    """
    get deck settings for burying cards until tomorrow instead of just until a
    later session today
    """

    # ripped from top of _burySiblings in both Schedulers
    nconf = self._newConf(card)
    buryNew = nconf.get("bury", True)
    rconf = self._revConf(card)
    buryRev = rconf.get("bury", True)

    return buryNew, buryRev


def buryCards(self, cids: List[int], manual: bool = True) -> None:
    # copied from SchedulerV2.buryCards. Scheduler implements a buryCards, but
    # it does a bit more than SchedulerV2 which makes the cards repeat for some
    # reason
    queue = manual and QUEUE_TYPE_MANUALLY_BURIED or QUEUE_TYPE_SIBLING_BURIED
    self.col.log(cids)
    self.col.db.execute(
        """
        update cards set queue=?,mod=?,usn=? where id in """
        + ids2str(cids),
        queue,
        intTime(),
        self.col.usn(),
    )


def _scheduledNotes(self: SomeScheduler) -> Iterable[Note]:
    assert self.col.db  # optional in typing system but set by this point

    for (nid,) in self.col.db.execute(
        f"""
select distinct(nid) from cards where
(queue={QUEUE_TYPE_NEW} or (queue={QUEUE_TYPE_REV} and due<=?))""",
        self.today,
    ):
        yield Note(self.col, id=nid)


def _cousinCards(self: SomeScheduler, note_ids: Set[int]) -> Iterable[Tuple[int, int]]:
    assert self.col.db  # optional in typing system but set by this point

    return self.col.db.execute(
        f"""
    select id, queue from cards where nid in {ids2str(list(note_ids))}
    and (queue={QUEUE_TYPE_NEW} or (queue={QUEUE_TYPE_REV} and due<=?))""",
        self.today,
    )  # type: ignore


def findDupes(
    self: Collection, fieldName: str, search: str = "", *, _old
) -> List[Tuple[str, List[int]]]:
    """ re-implementation of findDupes using the fuzzy rules """

    exact_duplicates = [
        (f"[exact] {value}", note_ids)
        for value, note_ids in _old(self, fieldName, search)
    ]

    config = SettingsManager(self).load()

    search_filters = []

    if search:
        search_filters.append(f"({search})")

    def extract_field(model_id, field_name) -> Iterable[Tuple[int, str]]:
        # type works better in future anki
        model: NoteType = self.models.get(model_id)
        note_ids = self.findNotes(" ".join(search_filters + [f'note:{model["name"]}']))

        field_ord: int = next(
            field["ord"] for field in model["flds"] if field["name"] == field_name
        )

        assert self.db

        for note_id, fields in self.db.all(
            "select id, flds from notes where id in " + ids2str(note_ids)
        ):
            value = splitFields(fields)[field_ord]
            yield note_id, stripHTMLMedia(value)

    duplicate_groups: DefaultDict[str, Set[int]] = defaultdict(set)

    for rule in config:
        # only use rules based off the selected field
        if rule.my_field != fieldName:
            continue

        my_note_fields = list(extract_field(rule.my_note_model_id, rule.my_field))
        my_values = [f[1] for f in my_note_fields]

        same_field = (
            rule.cousin_note_model_id == rule.my_note_model_id
            and rule.cousin_field == rule.my_field
        )

        if same_field:
            cousin_note_fields = my_note_fields
            cousin_values = my_values
        else:
            cousin_note_fields = list(
                extract_field(rule.cousin_note_model_id, rule.cousin_field)
            )
            cousin_values = [f[1] for f in cousin_note_fields]

        matches = rule.test(my_values, cousin_values)

        if not matches:
            continue

        my_mapping = defaultdict(list)

        for my_note_id, my_note_field in my_note_fields:
            my_mapping[my_note_field].append(my_note_id)

        if same_field:
            cousin_mapping = my_mapping
        else:
            cousin_mapping = defaultdict(list)

            for cousin_note_id, cousin_note_field in cousin_note_fields:
                cousin_mapping[cousin_note_field].append(cousin_note_id)

        for my_value, cousin_value in matches:
            for my_note_id in my_mapping[my_value]:
                key = f"[{rule.comparison.name}] {my_value}"

                for cousin_note_id in cousin_mapping[cousin_value]:
                    if my_note_id == cousin_note_id:
                        continue

                    duplicate_groups[key].add(my_note_id)
                    duplicate_groups[key].add(cousin_note_id)

    cousin_matches = [
        (key, list(note_ids)) for key, note_ids in duplicate_groups.items()
    ]

    return exact_duplicates + cousin_matches

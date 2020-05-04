from typing import TYPE_CHECKING, Iterable, List, Set, Tuple, Union

from anki.consts import (
    QUEUE_TYPE_MANUALLY_BURIED,
    QUEUE_TYPE_NEW,
    QUEUE_TYPE_REV,
    QUEUE_TYPE_SIBLING_BURIED,
)
from anki.hooks import wrap
from anki.notes import Note
from anki.sched import Scheduler
from anki.schedv2 import Scheduler as SchedulerV2
from anki.utils import ids2str, intTime
from aqt.utils import tooltip  # type: ignore

from .settings import SettingsManager


SomeScheduler = Union[Scheduler, SchedulerV2]

if TYPE_CHECKING:
    from anki.cards import Card


def buryCousins(self: SomeScheduler, card: "Card") -> None:
    """ bury related cards that aren't marked as siblings """
    # implementation mirrors anki's _burySiblings without the options

    toBury: Set[int] = set()  # note ids

    my_note = card.note()

    def field_value(note, field_name):
        note_type = self.col.models.get(note.mid)
        field_number = self.col.models.fieldMap(note_type)[field_name][0]
        return note.fields[field_number]

    config = SettingsManager(self.col).load()

    for rule in config:
        if rule.my_note_model_id != my_note.mid:
            continue

        my_value = field_value(my_note, rule.my_field)

        for cousin_note in _scheduledNotes(self):
            if rule.cousin_note_model_id != cousin_note.mid:
                continue

            if my_note.id == cousin_note.id:
                continue

            cousin_value = field_value(cousin_note, rule.cousin_field)

            if rule.test(my_value, cousin_value):
                # not super efficient, could just look up cids all at the end
                toBury.add(cousin_note.id)

    cousin_cards = list(_cousinCards(self, toBury))

    for cid, queue in cousin_cards:
        try:
            (self._revQueue if queue == QUEUE_TYPE_REV else self._newQueue).remove(cid)
        except ValueError:
            # not actually scheduled. not sure why things end up here but anki
            # protects against this too
            pass

    if cousin_cards:
        tooltip("burying %d cousin card" % len(cousin_cards))

    if isinstance(self, Scheduler):
        buryCards(self, [id for id, _ in cousin_cards])
    else:
        self.buryCards([id for id, _ in cousin_cards], manual=False)


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


# Anki doesn't have hooks in all of the right places, so monkey patching
# private methods is an established if fragile pattern
Scheduler._burySiblings = wrap(Scheduler._burySiblings, buryCousins, "after")  # type: ignore
SchedulerV2._burySiblings = wrap(SchedulerV2._burySiblings, buryCousins, "after")  # type: ignore

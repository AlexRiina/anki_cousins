"""
Plugin to bury cards that look similar to current card
"""

from anki.collection import _Collection as Collection
from anki.hooks import wrap
from anki.sched import Scheduler
from anki.schedv2 import Scheduler as SchedulerV2
from anki import buildinfo

from . import interface  # noqa: F401
from . import main  # noqa: F401

version = tuple(map(int, buildinfo.version.split(".")))

# Anki doesn't have hooks in all of the right places, so monkey patching
# private methods is an established if fragile pattern
Scheduler._burySiblings = wrap(Scheduler._burySiblings, main.buryCousins, "after")  # type: ignore
SchedulerV2._burySiblings = wrap(SchedulerV2._burySiblings, main.buryCousins, "after")  # type: ignore

if version >= (2, 1, 45):
    Collection.find_dupes = wrap(Collection.find_dupes, main.findDupes, None)  # type: ignore
else:
    Collection.findDupes = wrap(Collection.findDupes, main.findDupes, None)  # type: ignore

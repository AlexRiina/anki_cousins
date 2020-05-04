from typing import List
from functools import partial
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QPushButton,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QVBoxLayout,
    QFormLayout,
    QComboBox,
    QCheckBox,
    QDoubleSpinBox,
    QLineEdit,
    QLabel,
)
from anki.hooks import addHook
from anki.collection import _Collection
from aqt import mw  # type: ignore


def show_settings_dialog() -> None:
    col: _Collection = mw.col

    dialog = QDialog(mw)
    dialog.setWindowTitle("Bury Cousins Options")

    dialog_layout = QVBoxLayout()
    dialog.setLayout(dialog_layout)

    note_types = {model["name"]: model["id"] for model in col.models.models.values()}

    forms = QVBoxLayout()

    append = QPushButton('Add rule')

    buttons = QDialogButtonBox(QDialogButtonBox.Close | QDialogButtonBox.Save)  # type: ignore
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    buttons.setOrientation(Qt.Horizontal)

    grid = QGridLayout()

    for index, label in enumerate([
            QLabel("on note"),
            QLabel("match field"),
            QLabel("to note"),
            QLabel("match field"),
            QLabel("matcher"),
            QLabel("similarity")]):
        grid.addWidget(label, 0, index)

    match_rules: List[MatchRuleForm] = []
    for stored_values in col.conf.get('anki_cousins', []):
        form = MatchRuleForm(note_types, grid)

        try:
            form.set_values(*stored_values)
        except TypeError:
            col.log("invalid cousin matching config")
            continue

        if grid:
            pass
        else:
            forms.addLayout(form.layout)
        match_rules.append(form)

    def append_row():
        form = MatchRuleForm(note_types, grid)
        if grid:
            pass
        else:
            forms.addLayout(form.layout)
        match_rules.append(form)

    append.clicked.connect(append_row)

    dialog_layout.addLayout(forms)
    if grid:
        dialog_layout.addLayout(grid)
    dialog_layout.addWidget(append)
    dialog_layout.addWidget(buttons)

    print(col.conf.get('anki_cousins'))

    if dialog.exec_():
        col.conf['anki_cousins'] = [match_rule.get_values() for match_rule in
                                    match_rules if match_rule.is_valid()]
        col.setMod()


class MatchRuleForm:
    layout: QFormLayout

    def __init__(self, note_types, grid):
        self._my_note_type = QComboBox()
        for note_type, note_id in note_types.items():
            self._my_note_type.addItem(note_type, note_id)

        # TODO: turn LineEdits into QComboBox whose options are reset on
        # currentTextChanged.connect
        self._my_note_field = QLineEdit()

        self._other_note_type = QComboBox()
        for note_type, note_id in note_types.items():
            self._other_note_type.addItem(note_type, note_id)

        self._other_note_field = QLineEdit()

        self._matcher = QComboBox()
        self._matcher.addItem("by prefix", "prefix")
        self._matcher.addItem("by similarity", "similarity")

        self._threshold = QDoubleSpinBox()
        self._threshold.setMinimum(0)
        self._threshold.setMaximum(1)
        self._threshold.setSingleStep(0.05)
        self._threshold.setValue(0.95)

        self._delete = QCheckBox('delete?')

        if False:
            self.layout = QFormLayout()
            self.layout.addRow(QLabel("on note"), self._my_note_type)
            self.layout.addRow(QLabel("match field"), self._my_note_field)
            self.layout.addRow(QLabel("to note"), self._other_note_type)
            self.layout.addRow(QLabel("match field"), self._other_note_field)
            self.layout.addRow(QLabel("matcher"), self._matcher)
            self.layout.addRow(QLabel("similarity threshold"), self._threshold)
            self.layout.addRow(self._delete)
        else:
            row = grid.rowCount()

            for index, field in enumerate([self._my_note_type,
                                           self._my_note_field,
                                           self._other_note_type,
                                           self._other_note_field,
                                           self._matcher,
                                           self._threshold,
                                           self._delete]):
                grid.addWidget(field, row, index)

    def set_values(self,
                   my_note_type_value,
                   my_note_field_value,
                   other_note_type_value,
                   other_note_field_value,
                   matcher,
                   threshold,
                   ):

        if my_note_type_value:
            self._my_note_type.setCurrentIndex(self._my_note_type.findData(my_note_type_value))

        if my_note_field_value:
            self._my_note_field.setText(my_note_field_value)

        if other_note_type_value:
            self._other_note_type.setCurrentIndex(
                self._other_note_type.findData(other_note_type_value))

        if other_note_field_value:
            self._other_note_field.setText(other_note_field_value)

        if matcher:
            self._matcher.setCurrentIndex(self._matcher.findData(matcher))

        if threshold:
            self._threshold.setValue(threshold)

    def get_values(self):
        return (
            self._my_note_type.currentData(),
            self._my_note_field.text(),
            self._other_note_type.currentData(),
            self._other_note_field.text(),
            self._matcher.currentData(),
            self._threshold.value(),
        )

    def is_valid(self):
        return not self._delete.isChecked() and \
            all(value not in {None, ""} for value in self.get_values())


@partial(addHook, "profileLoaded")
def profileLoaded():
    mw.addonManager.setConfigAction("anki_cousins", show_settings_dialog)

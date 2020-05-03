from functools import partial
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAction,
    QDialog,
    QDialogButtonBox,
    QVBoxLayout,
    QFormLayout,
    QComboBox,
    QDoubleSpinBox,
    QLineEdit,
    QLabel,
)
from anki.hooks import addHook
from anki.collection import _Collection
from aqt import mw


def show_settings_dialog() -> None:
    col: _Collection = mw.col

    dialog = QDialog(mw)
    dialog.setWindowTitle("Bury Cousins Options")

    dialog_layout = QVBoxLayout()
    dialog.setLayout(dialog_layout)

    note_types = {model["name"]: model["id"] for model in col.models.models.values()}

    my_note_type = QComboBox()
    for note_type, note_id in note_types.items():
        my_note_type.addItem(note_type, note_id)

    # TODO: turn LineEdits into QComboBox whose options are reset on
    # currentTextChanged.connect
    my_note_field = QLineEdit()

    other_note_type = QComboBox()
    for note_type, note_id in note_types.items():
        other_note_type.addItem(note_type, note_id)

    other_note_field = QLineEdit()

    matcher = QComboBox()
    matcher.addItem("by prefix", "prefix")
    matcher.addItem("by similarity", "similarity")

    threshold = QDoubleSpinBox()
    threshold.setMinimum(0)
    threshold.setMaximum(1)
    threshold.setSingleStep(0.05)
    threshold.setValue(0.95)

    form = QFormLayout()
    form.addRow(QLabel("on note"), my_note_type)
    form.addRow(QLabel("match field"), my_note_field)
    form.addRow(QLabel("to note"), other_note_type)
    form.addRow(QLabel("match field"), other_note_field)
    form.addRow(QLabel("matcher"), matcher)
    form.addRow(QLabel("similarity threshold"), threshold)

    buttons = QDialogButtonBox(QDialogButtonBox.Close | QDialogButtonBox.Save)  # type: ignore
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    buttons.setOrientation(Qt.Horizontal)

    dialog_layout.addLayout(form)
    dialog_layout.addWidget(buttons)

    print(col.conf.get('anki_cousins'))

    if dialog.exec_():
        col.conf.setdefault('anki_cousins', {})
        config = col.conf['anki_cousins']

        config.setdefault(my_note_type.currentData(), [])
        note_config = config[my_note_type.currentData()]

        note_config.append(
            (
                my_note_field.text(),
                other_note_type.currentData(),
                other_note_field.text(),
                matcher.currentData(),
                threshold.value(),
            )
        )

        print(note_config)

        col.setMod()


@partial(addHook, "profileLoaded")
def profileLoaded():
    mw.addonManager.setConfigAction("anki_cousins", show_settings_dialog)

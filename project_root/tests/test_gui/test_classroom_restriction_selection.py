from PyQt6.QtCore import Qt
from src.gui.dialogs import ClassroomRestrictionsDialog


def checked(dialog):
    return {dialog.course_list.item(i).text() for i in range(dialog.course_list.count())
            if dialog.course_list.item(i).checkState() == Qt.CheckState.Checked}


def test_explicit_empty_is_not_restored_to_all():
    existing = {'R': {'BIO', 'CHEM'}}
    dialog = ClassroomRestrictionsDialog(None, {'R': ['BIO', 'CHEM'], 'S': ['BIO']}, existing)
    dialog._uncheck_all()
    assert not checked(dialog)
    assert dialog.get_restrictions() == {}
    dialog.cls_list.setCurrentRow(1)
    dialog.cls_list.setCurrentRow(0)
    assert not checked(dialog)
    assert dialog.get_restrictions() == {}
    assert existing == {'R': {'BIO', 'CHEM'}}
    dialog.close()


def test_individual_unchecking_last_course_preserves_empty():
    dialog = ClassroomRestrictionsDialog(None, {'R': ['BIO']}, {'R': {'BIO'}})
    dialog.course_list.item(0).setCheckState(Qt.CheckState.Unchecked)
    assert dialog.get_restrictions() == {}
    dialog.close()


def test_choose_courses_before_enabling_room_and_toggle_repeatedly():
    dialog = ClassroomRestrictionsDialog(None, {'R': ['BIO', 'CHEM']})
    room = dialog.cls_list.item(0)
    assert room.checkState() == Qt.CheckState.Unchecked
    assert dialog.get_restrictions() == {}
    dialog.course_list.item(1).setCheckState(Qt.CheckState.Unchecked)
    room.setCheckState(Qt.CheckState.Checked)
    assert dialog.get_restrictions() == {'R': {'BIO'}}
    room.setCheckState(Qt.CheckState.Unchecked)
    assert dialog.get_restrictions() == {}
    room.setCheckState(Qt.CheckState.Checked)
    assert checked(dialog) == {'BIO'}
    assert dialog.get_restrictions() == {'R': {'BIO'}}
    dialog._check_all()
    assert dialog.get_restrictions() == {'R': {'BIO', 'CHEM'}}
    dialog.close()

"""planars.layout: which folders in a language's folder are classes."""
from planars.layout import NOT_CLASS_FOLDERS, class_folders


def test_only_class_folders_are_classes(tmp_path):
    lang = tmp_path / "stan1293"
    for name in ["metrical", "ciscategorial", *NOT_CLASS_FOLDERS, ".hidden"]:
        (lang / name).mkdir(parents=True)
    (lang / "changes.tsv").write_text("x\n", encoding="utf-8")
    assert [d.name for d in class_folders(lang)] == ["ciscategorial", "metrical"]


def test_a_missing_language_folder_has_no_classes(tmp_path):
    assert class_folders(tmp_path / "nope") == []


def test_the_local_file_door_writes_to_these_folders():
    from coding import file_door
    assert file_door.planar("x").folder in NOT_CLASS_FOLDERS
    assert file_door.tab_status("x").folder in NOT_CLASS_FOLDERS
    assert file_door.notes_text("x").folder in NOT_CLASS_FOLDERS

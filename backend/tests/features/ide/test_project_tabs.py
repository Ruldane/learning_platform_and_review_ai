"""Une vue sauvegardée se relit avec les fichiers actuels du projet."""

from app.features.ide.service.project_tabs import ProjectTabs, restore


def test_restores_tab_order_and_active_file_without_stale_or_duplicate_paths() -> None:
    saved = ProjectTabs(("src/app.py", "supprime.py", "src/app.py", "main.py"), "main.py")
    files = {"main.py": "", "src/app.py": "", "notes.md": ""}

    view = restore(files, "main.py", saved)

    assert view == ProjectTabs(("src/app.py", "main.py"), "main.py")


def test_defaults_to_entry_and_keeps_it_open_after_the_last_tab_disappears() -> None:
    files = {"main.py": "", "notes.md": ""}

    assert restore(files, "main.py", None) == ProjectTabs(("main.py",), "main.py")
    stale = ProjectTabs(("ancien.py",), "ancien.py")
    assert restore(files, "main.py", stale) == ProjectTabs(("main.py",), "main.py")


def test_renamed_tab_stays_open_and_selected_without_changing_its_order() -> None:
    saved = ProjectTabs(("notes.md", "src/app.py"), "src/app.py")
    files = {"main.py": "", "notes.md": "", "src/nouveau.py": ""}

    renamed = restore(files, "main.py", saved.renamed("src/app.py", "src/nouveau.py"))

    assert renamed == ProjectTabs(("notes.md", "src/nouveau.py"), "src/nouveau.py")

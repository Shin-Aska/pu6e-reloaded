from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from pu6e_qt.game_profiles import (
    GAMES,
    GameProfile,
    GameProfileIssue,
    GameProfileIssueKind,
)
from pu6e_qt.launcher_cards import GameCard


@pytest.fixture(scope="session")
def game_card_app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _profile(
    game: str,
    issue: GameProfileIssue,
    directory: Path | None = Path("/games/example"),
) -> GameProfile:
    specification = next(spec for spec in GAMES if spec.key == game)
    return GameProfile(specification, directory, (), issue)


def _assert_unavailable_card(
    card: GameCard, issue: GameProfileIssue, status: str | None = None
) -> None:
    assert card.launch_button.isHidden()
    assert not card.availability_button.isHidden()
    assert card.status_label.property("launcherWarning") is True
    assert card.status_label.toolTip() == card.availability_button.toolTip()
    assert (status or issue.summary) in card.status_label.text()
    assert issue.details in card.availability_button.toolTip()
    assert issue.remedy in card.availability_button.toolTip()


@pytest.mark.parametrize("game", ("fp", "md", "se"))
def test_game_card_explains_unconfigured_game(
    game_card_app: QApplication, game: str
) -> None:
    # Given: no installation directory has been selected for a supported game.
    issue = GameProfileIssue(GameProfileIssueKind.UNCONFIGURED)
    card = GameCard(_profile(game, issue, None))

    # When: the card renders the unconfigured profile.
    card.update_profile(_profile(game, issue, None))

    # Then: it exposes the shared explanation and recovery action.
    _assert_unavailable_card(card, issue)


@pytest.mark.parametrize(
    ("game", "kind", "issue_path"),
    (
        ("fp", GameProfileIssueKind.DIRECTORY_MISSING, None),
        ("md", GameProfileIssueKind.NOT_DIRECTORY, None),
        ("se", GameProfileIssueKind.PERMISSION_DENIED, "tileflag"),
    ),
)
def test_game_card_explains_invalid_directory_for_each_game(
    game_card_app: QApplication,
    game: str,
    kind: GameProfileIssueKind,
    issue_path: str | None,
) -> None:
    # Given: each supported game has a distinct invalid selected directory state.
    path = Path(f"/games/{game}/unavailable")
    issue = GameProfileIssue(kind, (issue_path or str(path),))
    card = GameCard(_profile(game, issue, path))

    # When: the card renders that issue.
    card.update_profile(_profile(game, issue, path))

    # Then: the selected path and the actionable reason are visible on its tooltip.
    _assert_unavailable_card(card, issue)
    assert str(path) in card.availability_button.toolTip()


def test_game_card_identifies_wrong_supported_game(game_card_app: QApplication) -> None:
    # Given: a Martian Dreams card is pointed to a Savage Empire installation.
    expected = next(spec for spec in GAMES if spec.key == "md")
    detected = next(spec for spec in GAMES if spec.key == "se")
    issue = GameProfileIssue(
        GameProfileIssueKind.WRONG_GAME, ("mdpal",), detected
    )
    card = GameCard(GameProfile(expected, Path("/games/se"), (), issue))

    # When: the card renders the wrong-game issue.
    card.update_profile(GameProfile(expected, Path("/games/se"), (), issue))

    # Then: its recovery text identifies both the expected and detected games.
    _assert_unavailable_card(card, issue)
    assert expected.title in card.availability_button.toolTip()
    assert detected.title in card.availability_button.toolTip()


@pytest.mark.parametrize(
    "issue",
    (
        GameProfileIssue(GameProfileIssueKind.MISSING_PALETTE, ("u6pal",)),
        GameProfileIssue(
            GameProfileIssueKind.MISSING_CORE_FILES, ("map", "chunks")
        ),
    ),
)
def test_game_card_explains_missing_palette_and_core_files(
    game_card_app: QApplication, issue: GameProfileIssue
) -> None:
    # Given: a selected Ultima VI directory is missing a palette or core data.
    card = GameCard(_profile("fp", issue))

    # When: the card renders the shared diagnostic issue.
    card.update_profile(_profile("fp", issue))

    # Then: it gives the issue-specific recovery message.
    _assert_unavailable_card(card, issue)


@pytest.mark.parametrize(
    ("issue", "expected_detail"),
    (
        (
            GameProfileIssue(
                GameProfileIssueKind.MISSING_SAVE_DIRECTORY, ("savegame",)
            ),
            "savegame",
        ),
        (
            GameProfileIssue(
                GameProfileIssueKind.MISSING_SAVE_FILES,
                (
                    "savegame/objlist",
                    *(f"savegame/objblk{index:02x}" for index in range(69)),
                ),
            ),
            "69 saved-world object blocks",
        ),
    ),
)
def test_game_card_groups_missing_saved_world_files(
    game_card_app: QApplication, issue: GameProfileIssue, expected_detail: str
) -> None:
    # Given: Martian Dreams lacks its save index and all saved-world blocks.
    card = GameCard(_profile("md", issue))

    # When: the card renders the incomplete saved world.
    card.update_profile(_profile("md", issue))

    # Then: its visible status stays concise and the tooltip groups the blocks.
    _assert_unavailable_card(card, issue, "Saved game required")
    assert card.status_label.text() == "Saved game required"
    assert expected_detail in card.availability_button.toolTip()
    assert card.availability_button.toolTip().count("objblk") < 4


def test_game_card_explains_case_mismatched_files(game_card_app: QApplication) -> None:
    # Given: a required filename is present only with DOS-style capitalization.
    issue = GameProfileIssue(
        GameProfileIssueKind.CASE_MISMATCH, ("u6pal", "U6PAL")
    )
    card = GameCard(_profile("fp", issue))

    # When: the card renders the case mismatch.
    card.update_profile(_profile("fp", issue))

    # Then: it shows the expected name and lowercase-copy recovery guidance.
    _assert_unavailable_card(card, issue)
    assert "u6pal" in card.availability_button.toolTip()
    assert "lowercase" in card.availability_button.toolTip()


def test_game_card_resets_warning_after_profile_becomes_ready(
    game_card_app: QApplication,
) -> None:
    # Given: an Ultima VI card previously displayed a missing-palette warning.
    issue = GameProfileIssue(GameProfileIssueKind.MISSING_PALETTE, ("u6pal",))
    card = GameCard(_profile("fp", issue))
    ready = GameProfile(next(spec for spec in GAMES if spec.key == "fp"), Path("/games/fp"), ())

    # When: the same card receives a ready profile after files are restored.
    card.update_profile(ready)

    # Then: launch is restored and neither tooltip retains stale diagnostics.
    assert not card.launch_button.isHidden()
    assert card.availability_button.isHidden()
    assert card.status_label.toolTip() == ""
    assert card.availability_button.toolTip() == ""

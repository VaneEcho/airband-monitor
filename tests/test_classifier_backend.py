from airband_monitor.classifier_backend import build_classifier
from airband_monitor.classifier import HeuristicAudioClassifier


def test_build_classifier_heuristic() -> None:
    clf, used = build_classifier("heuristic")
    assert isinstance(clf, HeuristicAudioClassifier)
    assert used == "heuristic"


def test_build_classifier_invalid() -> None:
    try:
        build_classifier("bad")
        assert False, "expected ValueError"
    except ValueError:
        assert True

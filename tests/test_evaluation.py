from pathlib import Path

from airband_monitor.evaluation import best_by_f1, evaluate_grid, load_eval_jsonl


def test_evaluation_grid_and_best(tmp_path: Path) -> None:
    path = tmp_path / "eval.jsonl"
    path.write_text(
        "\n".join(
            [
                '{"music_prob": 0.9, "gt_music": true}',
                '{"music_prob": 0.8, "gt_music": true}',
                '{"music_prob": 0.2, "gt_music": false}',
                '{"music_prob": 0.6, "gt_music": false}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    samples = load_eval_jsonl(path)
    metrics = evaluate_grid(samples, [0.5, 0.7])
    best = best_by_f1(metrics)

    assert len(metrics) == 2
    assert best.threshold in {0.5, 0.7}
    assert 0.0 <= best.f1 <= 1.0

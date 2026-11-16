"""保存済みの生成・採点記録を再集計する。APIは呼ばない。"""

import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from app import judge  # noqa: E402


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    cases = judge.read_jsonl(ROOT / "data/eval/my_cases.jsonl")
    labels = judge.load_labels(ROOT / "lectures/04/my_labels.jsonl")
    generation = read(HERE / "generation_trace.json")
    scored = read(ROOT / "lectures/04/my_judge_result.json")
    review = read(HERE / "label_review.json")
    assert generation["status"] == scored["status"] == "complete"
    assert len(cases) == len(labels) == len(generation["cases"]) == len(scored["verdicts"]) == 10
    for path, expected in read(HERE / "input_manifest.json")["sha256"].items():
        assert sha(ROOT / path) == expected, path
    assert sha(ROOT / "data/eval/my_cases.jsonl") == generation["cases_sha256"] == review["case_sha256"]
    assert sha(ROOT / "lectures/04/my_labels.jsonl") == review["labels_sha256"] == scored["identity"]["labels_sha256"]
    assert review["created_at"] <= scored["started_at"]
    assert not review["user_reviewed"] and all(not row["user_reviewed"] for row in labels.values())
    assert judge.summarize(cases, scored["verdicts"], labels) == scored["summary"]
    rows = []
    for case in cases:
        cid = case["id"]
        record = generation["cases"][cid]
        assert record["answer"] == case["answer"]
        assert scored["verdicts"][cid]["lecture_mark"]["verdict"] == judge.check_lecture_mark(case["answer"])
        calls = [p for p in record["parts"] if p["type"] == "call"]
        row = {"id": cid, "category": case["category"], "tools": ", ".join(p["tool"] for p in calls)}
        for key, _ in judge.ALL_CRITERIA:
            row[f"reference_{key}"] = labels[cid][key]
            row[f"judge_{key}"] = scored["verdicts"][cid][key]["verdict"]
        row["reference_overall"] = judge.overall(labels[cid])
        row["judge_overall"] = judge.overall({k: v["verdict"] for k, v in scored["verdicts"][cid].items()})
        rows.append(row)
    with (HERE / "case_results.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    save_case = generation["cases"]["10"]
    summary_calls = [p for p in generation["cases"]["04"]["parts"] if p["type"] == "call"]
    search_diagnostic = {cid: any(p["type"] == "call" and p["tool"] == "search_glossary" for p in generation["cases"][cid]["parts"])
                         for cid in ["01", "02", "03", "04", "05", "06", "07"]}
    code_checks = {
        "lecture_marks_present": [r["id"] for r in rows if r["judge_lecture_mark"] == "pass"],
        "lecture_marks_absent": [r["id"] for r in rows if r["judge_lecture_mark"] == "fail"],
        "lecture04_summary_tool_called": any(p["tool"] == "get_lecture_summary" and p["args"].get("lecture") == 4 for p in summary_calls),
        "save_requested": any(p["type"] == "call" and p["tool"] == "save_learning_log" for p in save_case["parts"]),
        "save_approval_refused": bool(save_case["approvals"]) and all(a["decision"] == "n" for a in save_case["approvals"]),
        "save_denied_return": any(p["type"] == "return" and p["tool"] == "save_learning_log" and p["outcome"] == "denied" for p in save_case["parts"]),
        "save_refusal_produced_zero_files": save_case["saved_files"] == 0,
        "all_cases_produced_zero_files": all(r["saved_files"] == 0 for r in generation["cases"].values()),
        "additional_diagnostic_glossary_called_for_course_questions": search_diagnostic,
        "diagnostic_note": "Search diagnostic applies the existing instruction literally. Case 04 used the summary tool but not glossary search; report separately from the predeclared five grading criteria."
    }
    save(HERE / "code_checks.json", code_checks)
    def usage(records):
        return {k: sum(r["usage"].get(k, 0) or 0 for r in records.values()) for k in ["requests", "input_tokens", "output_tokens"]}
    analysis = {"status": "complete", "label_source": "assistant-reviewed provisional; not independent human annotations",
                "generated_cases": 10, "graded_cases": 10, "summary": scored["summary"],
                "reference_overall_pass": sum(r["reference_overall"] == "pass" for r in rows),
                "judge_overall_pass": sum(r["judge_overall"] == "pass" for r in rows),
                "generation_usage": usage(generation["cases"]), "grading_usage": usage(scored["calls"]),
                "code_checks": code_checks,
                "caution": "Agreement against provisional AI-assisted references is not agreement with the user. Ten cases and one run do not establish general reliability."}
    save(HERE / "analysis.json", analysis)
    save(HERE / "validation.json", {"status": "passed", "at": datetime.now(ZoneInfo("Asia/Taipei")).isoformat(timespec="seconds"),
         "fixed_inputs_verified": True, "summaries_recomputed": True, "annotations_fixed_before_grading": True,
         "sha256": {p: sha(ROOT / p) for p in ["data/eval/my_cases.jsonl", "data/eval/my_rubric.md", "lectures/04/my_labels.jsonl", "lectures/04/my_judge_result.json", "lectures/04/implementation/generation_trace.json", "lectures/04/implementation/label_review.json", "lectures/04/implementation/code_checks.json", "lectures/04/implementation/case_results.csv", "lectures/04/implementation/analysis.json"]}})
    print(json.dumps(analysis, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

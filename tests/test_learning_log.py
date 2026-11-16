"""第3回 実装課題: 実ファイルと実際の承認・再開処理を、APIなしで検証する。"""

import json
from datetime import datetime

import pytest
from pydantic_ai import DeferredToolRequests
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, ToolReturnPart, UserPromptPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.models.test import TestModel

from app import agent as agent_module
from app import tools

CONTENT = "ツールの保存前に利用者の承認を挟む。"
QUESTION = f"第3回の学習記録『{CONTENT}』を保存して"


@pytest.fixture(autouse=True)
def log_dir(monkeypatch, tmp_path):
    """個人の学習ログには触れず、一時フォルダに保存する。"""
    path = tmp_path / "learning_log"
    monkeypatch.setattr(tools, "LEARNING_LOG_DIR", path)
    return path


def _saving_model(calls=None):
    """最初に保存を要求し、再開後は返された結果を表示する固定の偽モデル。"""
    if calls is None:
        calls = [ToolCallPart("save_learning_log", {"lecture": 3, "content": CONTENT}, "save-1")]

    def respond(messages, info):
        assert "save_learning_log" in {tool.name for tool in info.function_tools}
        returns = [p for m in messages for p in m.parts if isinstance(p, ToolReturnPart)]
        if not returns:
            return ModelResponse(parts=calls)
        return ModelResponse(parts=[TextPart(json.dumps([p.content for p in returns], ensure_ascii=False))])

    return FunctionModel(respond)


def _tool_returns(result):
    return [p for m in result.all_messages() for p in m.parts if isinstance(p, ToolReturnPart)]


def test_save_preserves_japanese_content_and_records_time(log_dir):
    result = json.loads(tools.save_learning_log(3, CONTENT))

    assert result["status"] == "saved"
    files = list(log_dir.glob("*.json"))
    assert len(files) == 1
    record = json.loads(files[0].read_text(encoding="utf-8"))
    assert record["lecture"] == 3
    assert record["content"] == CONTENT
    assert datetime.fromisoformat(record["created_at"]).utcoffset().total_seconds() == 0
    assert result["path"] == f"learning_log/{files[0].name}"


def test_saving_again_creates_a_new_file_without_overwriting(log_dir):
    first = json.loads(tools.save_learning_log(3, "最初の記録"))
    second = json.loads(tools.save_learning_log(3, "次の記録"))

    assert first["path"] != second["path"]
    records = [json.loads(p.read_text(encoding="utf-8")) for p in log_dir.glob("*.json")]
    assert {r["content"] for r in records} == {"最初の記録", "次の記録"}


@pytest.mark.parametrize("lecture,content", [(0, CONTENT), (-1, CONTENT), (3, ""), (3, " \n ")])
def test_invalid_log_is_not_saved(lecture, content, log_dir):
    result = json.loads(tools.save_learning_log(lecture, content))

    assert result["status"] == "error"
    assert not log_dir.exists()


def test_write_failure_is_reported_as_error(log_dir):
    log_dir.write_text("ここはディレクトリではない", encoding="utf-8")

    result = json.loads(tools.save_learning_log(3, CONTENT))

    assert result["status"] == "error"
    assert "保存できませんでした" in result["message"]
    assert log_dir.read_text(encoding="utf-8") == "ここはディレクトリではない"


def test_tool_waits_for_approval_without_creating_a_directory(log_dir):
    result = agent_module.agent.run_sync(QUESTION, model=_saving_model())

    assert isinstance(result.output, DeferredToolRequests)
    assert len(result.output.approvals) == 1
    call = result.output.approvals[0]
    assert call.tool_name == "save_learning_log"
    assert call.args_as_dict() == {"lecture": 3, "content": CONTENT}
    assert call.tool_call_id == "save-1"
    assert not _tool_returns(result)
    assert not log_dir.exists()


@pytest.mark.parametrize("answer", ["y", " YES "])
def test_approval_shows_arguments_before_saving_and_saves_once(answer, monkeypatch, capsys, log_dir):
    def approve(prompt):
        assert "[y/N]" in prompt
        shown = capsys.readouterr().out
        assert "[approval required] save_learning_log" in shown
        assert '"lecture": 3' in shown
        assert CONTENT in shown
        assert not log_dir.exists()
        return answer

    monkeypatch.setattr("builtins.input", approve)
    result = agent_module.run_with_approval(agent_module.agent, QUESTION, _saving_model())

    assert isinstance(result.output, str)
    assert len(list(log_dir.glob("*.json"))) == 1
    returns = _tool_returns(result)
    assert len(returns) == 1
    assert json.loads(returns[0].content)["status"] == "saved"
    assert result.usage.requests == 2  # 承認前の要求 + 再開後の回答
    assert result.usage.tool_calls == 1
    prompts = [p for m in result.all_messages() for p in m.parts if isinstance(p, UserPromptPart)]
    assert [p.content for p in prompts] == [QUESTION]  # 元の質問を送り直して二重実行しない


@pytest.mark.parametrize("answer", ["n", "", "maybe"])
def test_denial_or_unrecognized_answer_does_not_save(answer, monkeypatch, log_dir):
    monkeypatch.setattr("builtins.input", lambda prompt: answer)

    result = agent_module.run_with_approval(agent_module.agent, QUESTION, _saving_model())

    assert isinstance(result.output, str)
    assert not log_dir.exists()
    returns = _tool_returns(result)
    assert len(returns) == 1
    assert returns[0].outcome == "denied"
    assert "拒否" in returns[0].content
    assert result.usage.requests == 2


@pytest.mark.parametrize("interruption", [EOFError, KeyboardInterrupt])
def test_interrupted_input_denies_the_save(interruption, monkeypatch, capsys, log_dir):
    def interrupt(prompt):
        raise interruption

    monkeypatch.setattr("builtins.input", interrupt)
    result = agent_module.run_with_approval(agent_module.agent, QUESTION, _saving_model())

    assert not log_dir.exists()
    assert _tool_returns(result)[0].outcome == "denied"
    assert "入力が中断" in capsys.readouterr().out


def test_multiple_calls_receive_individual_approval(monkeypatch, log_dir):
    calls = [
        ToolCallPart("save_learning_log", {"lecture": 3, "content": "承認する記録"}, "save-a"),
        ToolCallPart("save_learning_log", {"lecture": 3, "content": "拒否する記録"}, "save-b"),
    ]
    answers = iter(["y", "n"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))

    result = agent_module.run_with_approval(agent_module.agent, QUESTION, _saving_model(calls))

    records = [json.loads(p.read_text(encoding="utf-8")) for p in log_dir.glob("*.json")]
    assert [r["content"] for r in records] == ["承認する記録"]
    returns = {p.tool_call_id: p for p in _tool_returns(result)}
    assert json.loads(returns["save-a"].content)["status"] == "saved"
    assert returns["save-b"].outcome == "denied"


def test_read_only_question_does_not_ask_for_approval(monkeypatch, log_dir):
    def unexpected_prompt(prompt):
        pytest.fail("検索だけの質問で承認を求めた")

    monkeypatch.setattr("builtins.input", unexpected_prompt)
    result = agent_module.run_with_approval(
        agent_module.agent, "LoRAとは？", TestModel(call_tools=["search_glossary"])
    )

    assert isinstance(result.output, str)
    assert not log_dir.exists()
    assert _tool_returns(result)[0].tool_name == "search_glossary"


@pytest.mark.parametrize("answer,expected_files,outcome", [("y", 1, "approved"), ("n", 0, "denied")])
def test_cli_runs_confirmation_and_trace(answer, expected_files, outcome, monkeypatch, capsys, log_dir):
    monkeypatch.setattr("sys.argv", ["app.agent", "--trace", QUESTION])
    monkeypatch.setattr(agent_module, "build_model", _saving_model)
    monkeypatch.setattr("builtins.input", lambda prompt: answer)

    agent_module.main()

    output = capsys.readouterr().out
    assert "[approval required] save_learning_log" in output
    assert f"[approval] save_learning_log: {outcome}" in output
    assert "[tool call]   save_learning_log" in output
    assert "[tool return] save_learning_log" in output
    assert "requests=2" in output
    assert len(list(log_dir.glob("*.json"))) == expected_files


def test_cli_lists_save_tool_without_api_key(monkeypatch, capsys, log_dir):
    def unexpected_api_call():
        pytest.fail("ツール一覧の表示で実モデルを作ろうとした")

    monkeypatch.setattr("sys.argv", ["app.agent", "--list-tools"])
    monkeypatch.setattr(agent_module, "build_model", unexpected_api_call)
    agent_module.main()

    output = capsys.readouterr().out
    assert "[save_learning_log]" in output
    assert "実行前に利用者の承認が必要" in output
    assert '"lecture"' in output and '"content"' in output
    assert not log_dir.exists()

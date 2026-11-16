"""SPR-32 TK6j: kho lệnh THƯỜNG (đọc, tìm, kiểm thử, git hằng ngày, định dạng) với công tắc agile BẬT: rào không được chặn nhầm lệnh nào.
Mục đích: đo tỉ lệ chặn nhầm sau TK6h/TK6i (luật `cd`, ký tự đại diện, `claude -p`, đường trạng thái). Rào là lưới phụ chống tai nạn, không phải ranh giới
bảo mật; mỗi ca chặn nhầm tìm thấy được ghi trong KNOWN_FALSE_POSITIVES kèm lý do (không giấu, không xoá khỏi kho).
Chạy: python -m pytest -q tests/test_agile_guard_benign.py"""

from __future__ import annotations

import pytest

from test_agile_guard import claude, make_repo, run, write_switch

pytestmark = pytest.mark.usefixtures("agile_state_dir")

# Lệnh có nhắc "agile", "state", "claude", "hosts/claude" chỉ để ĐỌC hay tìm; lệnh kiểm thử, npm, git và định dạng thường ngày; `cd` trong repo.
CORPUS = [
    # tìm và đọc có nhắc agile / state / claude
    'grep -rn "agile" docs/', 'grep -r "/agile" hosts/claude', 'git log --oneline -- scripts/agile_state.py', 'git log -p --grep="agile" -- hosts/claude',
    'rg -n "agile" method/', 'rg -n "session_id" scripts/agile_state.py', 'rg -i "state" scripts/ | head -20', 'cat hosts/claude/README.md',
    'cat method/agile.md | head -40', 'ls hosts/claude', 'ls -la scripts', 'head -30 scripts/agile_state.py', 'tail -n 20 CHANGELOG.md', 'wc -l AGENTS.md method/agile.md',
    'sed -n 1,40p skills/agile/SKILL.md', 'python scripts/agile_state.py status', 'git diff -- hosts/claude', 'git show HEAD:AGENTS.md | head -20',
    'find . -name "*.py" -path "./scripts/*"', 'find skills -maxdepth 2 -name SKILL.md', 'grep -c "claude" README.md', 'cat .gitignore', 'file README.md',
    'git grep -n "state" -- "*.py"', 'rg --files | wc -l', 'diff AGENTS.md method/agile.md', 'echo "agile state is stored outside the project"',
    'git log --since=2.weeks --format="%h %s" -- skills/agile', 'cat commands/agile-goal.md',
    # git hằng ngày
    'git status', 'git status --short', 'git diff', 'git diff --stat', 'git diff --cached', 'git log --oneline -10', 'git branch --show-current', 'git add -A',
    'git add README.md docs/guide.md', 'git commit -m "docs: explain the agile switch"', 'git commit -m "fix: state file is not touched by claude -p"', 'git stash list',
    'git remote -v', 'git rev-parse HEAD', 'git blame -L 1,20 AGENTS.md', 'git checkout -b feature/agile-docs', 'git fetch origin',
    # kiểm thử, build, định dạng
    'pytest', 'pytest -q tests/test_check.py', 'python -m pytest -q -x', 'python -X utf8 -m pytest -q tests/test_commands.py', 'python scripts/check.py --self',
    'python scripts/check.py samples templates', 'npm test', 'npm run build', 'npm ci', 'npm install --save-dev prettier', 'npx prettier --write src/app.ts',
    'npx prettier --check "src/**/*.ts"', 'npx eslint --fix src/app.js', 'npx eslint src', 'ruff check scripts', 'sed -i s/foo/bar/ src/app.py', "sed -i 's/old/new/g' README.md",
    'mkdir -p build/out', 'cp README.md build/out/README.md', 'mv build/out/README.md build/out/README.txt', 'rm build/out/README.txt', 'touch notes.txt',
    'echo done > build/log.txt', 'python scripts/floor_check.py --base main --mode report',
    # cd trong repo
    'cd src && npm test', 'cd docs && ls', 'cd scripts && python check.py --self', 'cd src; npx prettier --write "**/*.ts"', 'cd tests && pytest -q', 'cd hosts/claude && ls',
    'cd src && git status', 'cd docs; grep -rn agile .', 'cd src; git add .', 'cd src && rm -f *.log', 'cd src && sed -i s/a/b/ *.md', 'cd src && cp -r * ../dist/',
    'cd docs && prettier --write "*.json"', 'cd config && sed -i s/a/b/ settings.json',
    # ca chặn nhầm đã biết (lớp ký tự đại diện / `state/` tương đối sau một `cd`; xem KNOWN_FALSE_POSITIVES)
    'cd src && mv * ../backup/', 'cd src && tar -czf ../out.tgz *', 'cd build && rm -rf *', 'cd src && git restore --staged "**/*"', 'cd src && echo hi > state/out.txt',
]

# Ca chặn nhầm đã đo: lệnh -> lý do. Mỗi ca ở đây vẫn được kiểm là BỊ CHẶN (đổi rào thì test báo để cập nhật danh sách).
_CD_WILDCARD = "đối số `*`/`**` sau một `cd` trong cùng lệnh có thể là file `.json` trong thư mục trạng thái (TK6h RF1, lớp còn lại sau TK6i SF1; `method/agile.md` 5.1)"
KNOWN_FALSE_POSITIVES: dict[str, str] = {
    'cd src && mv * ../backup/': _CD_WILDCARD,
    'cd src && tar -czf ../out.tgz *': _CD_WILDCARD,
    'cd build && rm -rf *': _CD_WILDCARD,
    'cd src && git restore --staged "**/*"': _CD_WILDCARD,
    'cd src && echo hi > state/out.txt': "đường tương đối `state/...` sau một `cd` bị coi là thư mục trạng thái; dự án có thư mục tên đúng `state` bị ảnh hưởng (TK6h RF1)",
}


@pytest.fixture(params=["repo-always", "session-on"])
def switch(request, tmp_path, monkeypatch):
    """(repo, session_id, mode): công tắc BẬT ở mức repo (cờ `always`) hay ở mức phiên (`session-t1.json`), thư mục trạng thái tạm riêng."""
    state = tmp_path / "home" / ".claude" / "plugins" / "data" / "agent-agile-team" / "state"
    state.mkdir(parents=True)
    monkeypatch.setenv("AGENT_AGILE_STATE_DIR", str(state))
    repo = make_repo(tmp_path / "work", marker=None)
    if request.param == "session-on":
        write_switch(repo, {}, session_id="t1")
        return repo, "t1", request.param
    write_switch(repo, {})
    return repo, None, request.param


def verdict(switch, cmd):
    repo, sid, _ = switch
    payload = claude(cmd, repo)
    if sid:
        payload["session_id"] = sid
    return run("claude", payload)


def test_corpus_has_at_least_sixty_unique_commands():
    assert len(CORPUS) >= 60 and len(set(CORPUS)) == len(CORPUS)


def test_known_false_positives_are_listed_in_the_corpus():
    assert set(KNOWN_FALSE_POSITIVES) <= set(CORPUS)


def test_the_guard_is_really_on_in_this_setup(switch):
    """Đối chứng: cùng thiết lập thì `rm -rf` ngoài `.tmp/` bị chặn (không thì kho lệnh thường qua vì rào ngủ, không có nghĩa gì)."""
    rc, _, err = verdict(switch, "rm -rf /some/dir")
    assert rc == 2, err


@pytest.mark.parametrize("cmd", [c for c in CORPUS if c not in KNOWN_FALSE_POSITIVES])
def test_benign_command_is_allowed_with_agile_on(switch, cmd):
    assert verdict(switch, cmd) == (0, "", ""), (switch[2], cmd)


def test_known_false_positives_are_still_blocked(switch):
    """Mỗi ca đã ghi chặn nhầm vẫn bị chặn (rào đổi thì test này báo để cập nhật danh sách); danh sách rỗng thì không kiểm gì."""
    for cmd, reason in KNOWN_FALSE_POSITIVES.items():
        rc, _, err = verdict(switch, cmd)
        assert rc == 2, (cmd, reason, rc, err)

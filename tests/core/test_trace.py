"""Журнал модуля и данные окна «О модуле» без QGIS."""
import os

from routeliner import about, trace


def test_trace_writes_steps_and_traceback(tmp_path):
    p = trace.setup(str(tmp_path))
    assert p == os.path.join(str(tmp_path), "routeliner.log")
    trace.step("запуск")
    try:
        1 / 0
    except ZeroDivisionError as e:
        trace.fail("сбой", e)
    lines = trace.tail()
    assert "ШАГ" in lines[0] and lines[0].endswith("запуск")
    assert "ОШИБКА" in lines[1] and lines[1].endswith("сбой")
    assert any("ZeroDivisionError" in ln for ln in lines[2:])


def test_trace_rotates_big_file(tmp_path):
    big = tmp_path / "routeliner.log"
    big.write_bytes(b"x" * (trace.MAX_BYTES + 1))
    trace.setup(str(tmp_path))
    assert (tmp_path / "routeliner.log.old").exists()
    assert big.stat().st_size == 0


def test_trace_silent_without_folder():
    assert trace.setup("") == ""
    trace.step("никуда")                 # не падает
    assert trace.tail() == []


def test_about_reads_version_and_history():
    md = about.read_metadata()
    hist = about.changelog_lines()
    assert hist and hist[0].startswith(md["version"] + " ")
    assert about.manual_path().endswith(".pdf")

# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez and IngeCAD contributors.
"""A polyline's width is a filled band, not just its axis: changing it must
rebuild that fill at once.

PEDIT Width and the Properties "Global width" field both edit a wide
polyline in place. The surgical overlay repaints a polyline by its axis
segments only, so without a full regen the new width stayed invisible until
a later deferred regen (toggling closed, a zoom) revealed it -- and a large
stray width then appeared all at once as a huge fill the user could not even
pick (a wide polyline is picked by its axis). Revert either fix and one of
these fails.
"""
import ezdxf
import pytest

from core import modify
from views import properties_panel as pp


def test_pedit_width_demands_a_full_regen():
    # Unlike a dimension edit (overlay-drawable), a width change alters the
    # polyline's FILL, which the overlay cannot paint: it needs the regen.
    assert modify.PolylineEditCommand.needs_regen is True
    assert modify.polyline_edit(object(), "width", 5).needs_regen is True


@pytest.fixture
def win(qapp):
    from views.main_window import MainWindow

    window = MainWindow()
    window.new_document("mm")
    yield window
    window.close()


def test_pedit_width_repaints_the_fill(win, monkeypatch):
    msp = win.document.modelspace()
    pl = msp.add_lwpolyline([(0, 0), (10, 0), (10, 10)])
    win.tools._invalidate_geometry()
    regens = []
    monkeypatch.setattr(win, "regen_in_memory",
                        lambda *a, **k: regens.append(1))

    win.tools._execute(modify.polyline_edit(pl, "width", 5))

    assert regens, "PEDIT Width must force the fill to be rebuilt on the spot"


class _RecordingPanel:
    """Enough of PropertiesPanel to build and fire the polyline rows,
    recording whether the width edit asked for a regen."""

    def __init__(self, entity):
        self._ents = [entity]
        self.calls = []

    def _active(self):
        return self._ents

    def _set_prop(self, prop, value, regen=False):
        self.calls.append((prop, value, regen))

    def _in_place(self, mutate):
        mutate()


def test_properties_global_width_asks_for_a_regen():
    doc = ezdxf.new("R2018", setup=True)
    pl = doc.modelspace().add_lwpolyline([(0, 0), (10, 0), (10, 10)])
    panel = _RecordingPanel(pl)

    rows = pp._lwpolyline_rows(panel, pl)[1]
    width = next(r for r in rows if r.label == "Global width")
    width.apply(5)

    # The fill changes with the width, so this edit must request a regen,
    # unlike color or layer which the overlay repaints.
    assert panel.calls == [("const_width", 5, True)]

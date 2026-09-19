def test_marker_warnung_bricht_den_lauf_nicht(pytester):
    pytester.makepyfile("""
        import pytest

        @pytest.mark.warnung
        def test_nur_warnung():
            assert False

        def test_echt_gruen():
            assert True
    """)
    r = pytester.runpytest('-q')
    assert r.ret == 0, r.outlines[-5:]
    assert any('W' in l or 'WARNUNG' in l for l in r.outlines)


def test_fehlschlag_ohne_marker_bleibt_rot(pytester):
    pytester.makepyfile("def test_x():\n    assert False\n")
    assert pytester.runpytest('-q').ret != 0


def test_leere_messung_macht_den_test_rot(pytester):
    """FEHLER 3: eigene Zusicherungen grün, aber nichts gemessen -> trotzdem rot."""
    pytester.makepyfile("""
        from build123d import Box

        from pruefstand import Body, Frame, Region, gap

        def test_nichts_gemessen():
            a = Body('A', 'A', solid=Box(10, 10, 10))
            b = Body('B', 'B', solid=Box(10, 10, 10))
            weit_weg = Region.box(Frame.identity(), (500, 500, 500), (510, 510, 510))
            r = gap(a, b, within=weit_weg)
            assert r.min_mm > 0.1          # sieht grün aus, ist aber inf
    """)
    r = pytester.runpytest('-q')
    assert r.ret != 0
    r.stdout.fnmatch_lines(['*nichts gemessen: Region enthält keine Geometrie*'])

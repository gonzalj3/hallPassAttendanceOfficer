from hpao.models import School


def test_school_construction() -> None:
    s = School(name="Pflugerville HS", district="PfISD")
    assert s.name == "Pflugerville HS"
    assert s.district == "PfISD"


def test_school_district_optional() -> None:
    s = School(name="Lone Star Academy")
    assert s.name == "Lone Star Academy"
    assert s.district is None


def test_school_repr_includes_name() -> None:
    s = School(name="Pflugerville HS")
    assert "Pflugerville HS" in repr(s)

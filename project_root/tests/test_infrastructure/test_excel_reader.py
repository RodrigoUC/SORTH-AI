"""Tests for the documented Aulas/Cursos workbook contract."""
import pandas as pd
import pytest

from src.infrastructure.excel_reader import ExcelReader


@pytest.fixture
def make_workbook(tmp_path):
    def write(courses, classrooms=None, sheet_order=("Aulas", "Cursos")):
        if classrooms is None:
            classrooms = pd.DataFrame({
                "# DE AULA": ["601", "LBIO"], "DESCRIPCIÓN": ["Aula", "Laboratorio"],
                "CAMPUS": ["HO", "HO"], "CAPACIDAD": [60, 25], "CAPACIDAD 80%": [48, 20],
            })
        sheets = {"Aulas": classrooms, "Cursos": courses}
        path = tmp_path / "input.xlsx"
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            for sheet in sheet_order:
                sheets[sheet].to_excel(writer, sheet_name=sheet, index=False)
        return ExcelReader(str(path))
    return write


def test_classrooms_metadata_capacity_and_blank_rows(make_workbook):
    rooms = pd.DataFrame({
        "# DE AULA": [" 601 ", "LBIO", "602", None, "  "],
        "DESCRIPCIÓN": [" Aula ", "Laboratorio", None, "Unused", None],
        "CAMPUS": [" HO ", "CH", None, None, None],
        "CAPACIDAD": [60, 25, None, 10, 10], "CAPACIDAD 80%": [48, 20, 0, 8, 8],
    })
    classrooms = make_workbook(pd.DataFrame({"Curso": []}), rooms).load_classrooms()
    assert set(classrooms) == {"601", "LBIO", "602"}
    assert classrooms["601"].room_type == "REGULAR"
    assert classrooms["601"].capacity == 60  # Not the 80% column.
    assert classrooms["601"].description == "Aula"
    assert classrooms["601"].campus == "HO"
    assert classrooms["LBIO"].room_type == "LAB"
    assert classrooms["LBIO"].capacity == 25
    assert classrooms["602"].capacity == 0
    assert classrooms["602"].description == ""
    assert classrooms["602"].campus == ""
    assert all(room.occupancy == {} for room in classrooms.values())


@pytest.mark.parametrize("sheet_order", [("Aulas", "Cursos"), ("Cursos", "Aulas")])
def test_each_row_is_one_group_and_preserves_suggestions(make_workbook, sheet_order):
    reader = make_workbook(pd.DataFrame({
        "Curso": [" BIO101 ", "BIO101", "BIO101", None, "  "],
        "Nombre de Curso": [" Biología ", "Biología", "Biología", None, None],
        # The column does not override the documented one-row-per-group rule.
        "Cantidad de Grupos": [99, 99, 99, None, None],
        "Horas": ["0800-1055", "0800-1055", "1400-1555", None, None],
        "Aula": ["601", "601", "LBIO", None, None],
        "Días": ["L", "L", "I,M", None, None],
    }), sheet_order=sheet_order)
    course, = reader.load_courses()
    assert course.code == "BIO101"
    assert course.name == "Biología"
    assert course.number_of_groups == 3
    assert course.duration_min == 175
    assert course.required_room_type == "REGULAR"
    assert course.suggested_classroom == "601"
    assert course.preferred_day == "Lunes"
    assert course.preferred_start_min == 480
    assert course.group_suggestions == [
        {"aula": "601", "preferred_day": "Lunes", "preferred_start_min": 480},
        {"aula": "601", "preferred_day": "Lunes", "preferred_start_min": 480},
        {"aula": "LBIO", "preferred_day": "Martes", "preferred_start_min": 840},
    ]
    groups = course.generate_groups()
    assert [group.group_id for group in groups] == ["BIO101-G1", "BIO101-G2", "BIO101-G3"]
    assert groups[2].suggested_classroom == "LBIO"
    assert groups[2].preferred_day == "Martes"
    assert groups[2].preferred_start_min == 840


def test_unknown_rooms_are_ignored_and_room_type_falls_back_to_code(make_workbook):
    reader = make_workbook(pd.DataFrame({
        "Curso": ["BIO101", "BIO102L", "BIO103P", "BIO104L", "BIO105"],
        "Horas": ["-", None, "", "0900-1000", "0800-0900"],
        "Aula": ["MISSING", "MISSING", "-", "601", "LBIO"],
        "Días": [None, "-", "", "J", "V"],
    }))
    courses = {course.code: course for course in reader.load_courses()}
    for code, expected_type in [("BIO101", "REGULAR"), ("BIO102L", "LAB"), ("BIO103P", "LAB")]:
        course = courses[code]
        assert course.suggested_classroom is None
        assert course.group_suggestions[0]["aula"] is None
        assert course.required_room_type == expected_type
        assert course.duration_min == 60
        assert course.preferred_day is None
        assert course.preferred_start_min is None
    assert courses["BIO104L"].required_room_type == "REGULAR"
    assert courses["BIO105"].required_room_type == "LAB"
    filtered = {course.code: course for course in reader.load_courses(known_classrooms={"601"})}
    assert filtered["BIO105"].suggested_classroom is None
    assert filtered["BIO105"].required_room_type == "REGULAR"


def test_missing_optional_columns_use_defaults(make_workbook):
    course, = make_workbook(pd.DataFrame({"Curso": ["BIO101"]})).load_courses()
    assert course.name is None
    assert course.number_of_groups == 1
    assert course.duration_min == 60
    assert course.suggested_classroom is None
    assert course.preferred_day is None
    assert course.preferred_start_min is None
    assert course.group_suggestions == [
        {"aula": None, "preferred_day": None, "preferred_start_min": None}
    ]


def test_course_columns_ignore_case_accents_and_whitespace(make_workbook):
    course, = make_workbook(pd.DataFrame({
        " CURSO ": ["BIO101"], "NOMBRE DE CURSO": ["Biología"],
        " HORAS ": ["0800-0955"], "aula": ["LBIO"], " dias ": ["s"],
    })).load_courses()
    assert course.name == "Biología"
    assert course.duration_min == 115
    assert course.preferred_day == "Sábado"
    assert course.preferred_start_min == 480
    assert course.suggested_classroom == "LBIO"


@pytest.mark.parametrize("code_column", ["Curso", " CURSO "])
def test_exact_course_column_wins_when_columns_are_reordered(make_workbook, code_column):
    reader = make_workbook(pd.DataFrame({
        "Nombre de Curso": ["Biología", "Biología", "Sin código"],
        code_column: ["BIO101", "BIO102", None],
        "Aula": ["601", "601", "601"],
    }))

    courses = reader.load_courses()

    assert [course.code for course in courses] == ["BIO101", "BIO102"]
    assert [course.name for course in courses] == ["Biología", "Biología"]
    assert [course.number_of_groups for course in courses] == [1, 1]
    assert reader.load_course_classroom_map() == {"601": ["BIO101", "BIO102"]}


def test_classroom_course_map_filters_unknown_rooms_and_deduplicates(make_workbook):
    reader = make_workbook(pd.DataFrame({
        "Curso": ["BIO101", "BIO101", "BIO102", "BIO103", "BIO104", None, "BIO105"],
        "Aula": ["601", "601", "601", "LBIO", "MISSING", "601", "-"],
    }))
    assert reader.load_course_classroom_map() == {"601": ["BIO101", "BIO102"], "LBIO": ["BIO103"]}
    assert reader.load_course_classroom_map(known_classrooms={"LBIO"}) == {"LBIO": ["BIO103"]}
    assert reader.load_course_classroom_map(known_classrooms=set()) == {}


@pytest.mark.parametrize("value,expected", [
    ("0800-1055", (480, 655)), (" 0700 - 0930 ", (420, 570)),
    (None, (None, None)), (float("nan"), (None, None)),
    ("-", (None, None)), ("", (None, None)), ("invalid", (None, None)),
])
def test_parse_horas(value, expected):
    assert ExcelReader("unused.xlsx")._parse_horas(value) == expected


@pytest.mark.parametrize("value,expected", [
    ("L,I,M,J,V,S", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]),
    (" l, m ", ["Lunes", "Miércoles"]), ("X,L", ["Lunes"]),
    (None, []), (float("nan"), []), ("-", []), ("", []),
])
def test_parse_dias(value, expected):
    assert ExcelReader("unused.xlsx")._parse_dias(value) == expected


def test_missing_required_sheet_reports_sheet_name(tmp_path):
    path = tmp_path / "wrong_sheets.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame({"# DE AULA": ["601"]}).to_excel(writer, sheet_name="aulas", index=False)
    with pytest.raises(ValueError, match="Aulas"):
        ExcelReader(str(path)).load_classrooms()

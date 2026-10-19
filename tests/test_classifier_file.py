from osint.input_parser.classifier import ArtifactType, classify_line


def test_file_prefix_is_classified_as_file():
    art = classify_line("file:leak_doc.pdf")
    assert art.type == ArtifactType.FILE
    assert art.value == "leak_doc.pdf"


def test_file_prefix_is_case_insensitive():
    art = classify_line("FILE: scan.png")
    assert art.type == ArtifactType.FILE
    assert art.value == "scan.png"


def test_bare_filename_without_prefix_is_not_file():
    art = classify_line("leak_doc.pdf")
    assert art.type != ArtifactType.FILE


def test_file_value_is_not_mutated():
    art = classify_line("file:subdir/report.docx")
    assert art.value == "subdir/report.docx"

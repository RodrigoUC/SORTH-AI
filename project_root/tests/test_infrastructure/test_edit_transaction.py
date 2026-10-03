import pytest
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.course import Course


def test_materialization_callback_failure_rolls_back_whole_write(tmp_path):
    repo = SessionRepository(str(tmp_path/'session.db'))
    original = dict(excel_path=None, seed=42, classrooms={}, courses=[Course('BIO',1,60,'REGULAR')],
                    restrictions={}, assignments=None)
    repo.save_session(**original)
    called = []
    def reject():
        called.append(True)
        # Other readers continue to see the accepted state until commit.
        assert repo.load_session()['courses'][0].code == 'BIO'
        raise RuntimeError('render failed')
    candidate = {**original, 'courses': []}
    with pytest.raises(RuntimeError):
        repo.save_session(**candidate, before_commit=reject)
    assert called == [True]
    assert repo.load_session()['courses'][0].code == 'BIO'
    repo.save_session(**candidate, before_commit=lambda: None)
    assert repo.load_session()['courses'] == []

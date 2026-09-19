from api import server

def test_local_chat_missing_topic_does_not_crash():
    reply=server.quick_chat_reply([{'role':'user','content':'mango calories'}])
    assert isinstance(reply,str) and len(reply)>10

def test_health_exposes_real_readiness(tmp_path, monkeypatch):
    from backend import classification_service
    monkeypatch.setattr(classification_service, 'ROOT', tmp_path)
    monkeypatch.setattr(classification_service, 'EXPERIMENT_DIR', tmp_path / 'experiment')
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    status=server.runtime_status()
    assert status['model_present'] is False
    assert status['inspection_ready'] is False
    assert status['gemini_configured'] is False
    assert status['classification_ready'] is False


def test_experiment_summary_unavailable_is_honest(tmp_path, monkeypatch):
    monkeypatch.setattr(server, 'EXPERIMENT_DIR', tmp_path)
    assert server.experiment_summary() == {
        'available': False,
        'message': 'Experiment artifacts have not been generated yet.',
    }


def test_classification_requires_real_artifact(tmp_path, monkeypatch):
    monkeypatch.setattr(server, 'EXPERIMENT_DIR', tmp_path)
    try:
        server.classify_fruit_type(server.Image.new('RGB', (32, 32), 'red'))
    except RuntimeError as exc:
        assert 'not available' in str(exc).lower()
    else:
        raise AssertionError('Classification must not run without a trained model')

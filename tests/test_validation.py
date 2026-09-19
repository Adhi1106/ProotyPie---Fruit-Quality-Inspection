from api import server


def test_unknown_fruit_does_not_get_freshness_advice():
    result=server.local_recommendation('apple', None)
    assert result['status'] == 'Unknown'
    assert 'estimate' in result['shelf_life'].lower() or 'not assessed' in result['shelf_life'].lower()


def test_image_decode_rejects_excessive_pixel_dimensions(monkeypatch):
    import io
    import pytest
    monkeypatch.setattr(server, 'MAX_IMAGE_PIXELS', 100)
    b=io.BytesIO()
    server.Image.new('RGB',(11,11),'red').save(b,format='PNG')
    with pytest.raises(ValueError,match='dimensions'):
        server.load_image(b.getvalue())

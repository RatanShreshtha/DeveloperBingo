from fastapi.testclient import TestClient

from devbingo_backend.app import create_app

DATABASE_URL = "postgresql+psycopg://x@127.0.0.1:1/x"


def test_the_default_pool_is_served_as_nine_columns():
    with TestClient(create_app(DATABASE_URL)) as client:
        response = client.get("/pools/default")

    assert response.status_code == 200
    columns = response.json()["columns"]
    assert [len(column) for column in columns] == [9, 10, 10, 10, 10, 10, 10, 10, 11]


def test_every_default_topic_has_a_name_and_an_explanation():
    with TestClient(create_app(DATABASE_URL)) as client:
        columns = client.get("/pools/default").json()["columns"]

    topics = [topic for column in columns for topic in column]
    assert len(topics) == 90
    assert all(topic["name"].strip() for topic in topics)
    assert all(topic["explanation"].strip() for topic in topics)


def test_the_default_pool_cannot_be_edited_over_http():
    with TestClient(create_app(DATABASE_URL)) as client:
        put = client.put("/pools/default", json={"columns": []})
        post = client.post("/pools/default", json={"columns": []})
        delete = client.delete("/pools/default")

    assert put.status_code == 405
    assert post.status_code == 405
    assert delete.status_code == 405

import json
import os
from pathlib import Path
import tempfile
import unittest
from uuid import uuid4


class CVFileImportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.previous_database = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f'sqlite:///{cls.directory.name}/inventory.db'
        import backend
        cls.backend = backend
        cls.app = backend.app
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            cls.backend.db.session.remove()
            cls.backend.db.engine.dispose()
        cls.directory.cleanup()
        if cls.previous_database is None:
            os.environ.pop('DATABASE_URL', None)
        else:
            os.environ['DATABASE_URL'] = cls.previous_database

    def setUp(self):
        with self.app.app_context():
            self.backend.db.drop_all()
            self.backend.db.create_all()
        self.shelf_id = self.client.post('/shelf', json={'name': 'Fridge'}).json['shelf_id']
        self.path = Path(self.directory.name) / 'result.json'
        self.path.unlink(missing_ok=True)

    def write(self, items, **overrides):
        data = {'result_id': str(uuid4()), 'shelf_id': self.shelf_id, 'items': items}
        data.update(overrides)
        self.path.write_text(json.dumps(data), encoding='utf-8')
        return data

    def ingest(self):
        from cv_file_import import import_result_file
        with self.app.app_context():
            return import_result_file(self.path, self.backend.reconcile_shelf)

    def test_file_to_inventory_and_price_edit_persists_across_new_results(self):
        self.write([{'name': 'Milk', 'confidence': 0.91}])
        self.assertIsNotNone(self.ingest())
        food = self.client.get('/items').json['items'][0]
        self.assertEqual(food['name'], 'Milk')
        self.assertEqual(food['category'], 'Dairy')
        self.assertIsNone(food['price'])
        self.assertEqual(food['confidence'], 0.91)
        self.assertEqual(self.client.post(f"/item/{food['id']}", json={
            'name': 'Milk', 'category': 'Dairy', 'price': 4.25,
        }).status_code, 200)
        # Another photo sees the same food plus a new one.
        self.write([{'name': 'Milk'}, {'name': 'Apple'}])
        self.ingest()
        inventory = {item['name']: item for item in self.client.get('/items').json['items']}
        self.assertEqual(set(inventory), {'Milk', 'Apple'})
        self.assertEqual(inventory['Milk']['id'], food['id'])
        self.assertEqual(inventory['Milk']['stored_at'], food['stored_at'])
        self.assertEqual(inventory['Milk']['price'], 4.25)
        self.assertEqual(self.client.get('/accounting/events').json, {'events': []})

    def test_same_result_is_not_replayed_after_database_session_restart(self):
        self.write([{'name': 'Milk'}])
        self.ingest()
        food = self.client.get('/items').json['items'][0]
        self.client.post(f"/item/{food['id']}/remove", json={'outcome': 'consumed'})
        with self.app.app_context():
            self.backend.db.session.remove()
        self.assertIsNone(self.ingest())
        self.assertEqual(self.client.get('/items').json['items'], [])
        with self.app.app_context():
            self.assertEqual(self.backend.Capture.query.count(), 1)

    def test_result_is_a_full_shelf_snapshot(self):
        self.write([{'name': 'Milk'}, {'name': 'Apple'}])
        self.ingest()
        self.write([{'name': 'Milk'}])
        self.ingest()
        self.assertEqual([item['name'] for item in self.client.get('/items').json['items']], ['Milk'])
        self.write([])
        self.ingest()
        self.assertEqual(self.client.get('/items').json['items'], [])

    def test_bad_results_do_not_partially_change_inventory(self):
        self.write([{'name': 'Milk'}])
        self.ingest()
        for overrides in [
            {'items': [{'name': 'Apple'}, {'name': ''}]},
            {'items': [{'name': 'Apple', 'confidence': 2}]},
            {'items': [{'name': 'Apple', 'confidence': float('nan')}]},
            {'shelf_id': 9999}, {'result_id': ''}, {'items': 'Milk'},
        ]:
            with self.subTest(overrides=overrides):
                self.write(**{'items': [], **overrides})
                with self.assertRaises(ValueError):
                    self.ingest()
                self.assertEqual([item['name'] for item in self.client.get('/items').json['items']], ['Milk'])

    def test_missing_or_incomplete_file_can_be_retried(self):
        self.assertIsNone(self.ingest())
        self.path.write_text('{"items":', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.ingest()
        self.write([{'name': 'Milk'}])
        self.assertIsNotNone(self.ingest())

    def test_file_polling_loop_imports_without_a_camera_or_cv_http_service(self):
        from unittest.mock import patch
        self.write([{'name': 'Milk'}])
        class StopPolling(Exception):
            pass
        with patch.dict(os.environ, {'CV_RESULTS_FILE': str(self.path)}):
            with patch.object(self.backend, 'mapped_cameras', side_effect=AssertionError('HTTP camera mode should be disabled')):
                with patch.object(self.backend.time, 'sleep', side_effect=StopPolling):
                    with self.assertRaises(StopPolling):
                        self.backend.poll_cameras_forever()
        self.assertEqual(self.client.get('/items').json['items'][0]['name'], 'Milk')


if __name__ == '__main__':
    unittest.main()

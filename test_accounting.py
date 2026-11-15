import os
import tempfile
import unittest


class AccountingTest(unittest.TestCase):
    def setUp(self):
        self.database = tempfile.TemporaryDirectory()
        os.environ['DATABASE_URL'] = f"sqlite:///{self.database.name}/test.db"
        from backend import app
        self.client = app.test_client()
        shelf = self.client.post('/shelf', json={'name': 'Fridge'}).json
        self.item_id = self.client.post('/item', json={
            'name': 'Milk', 'category': 'Dairy', 'price': 3.5,
            'shelf_id': shelf['shelf_id'],
        }).json['item_id']

    def tearDown(self):
        self.database.cleanup()
        os.environ.pop('DATABASE_URL', None)

    def test_outcome_persists_and_undo_voids_it(self):
        path = f'/item/{self.item_id}'
        self.assertEqual(self.client.post(path + '/remove', json={
            'outcome': 'consumed', 'use_first': True,
        }).status_code, 200)
        self.client.post(path + '/remove', json={'outcome': 'consumed'})
        self.assertEqual(self.client.get('/items').json['items'], [])
        events = self.client.get('/accounting/events').json['events']
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['price'], 3.5)
        self.assertTrue(events[0]['use_first'])
        self.assertIn('+00:00', events[0]['occurred_at'])
        self.client.post(path + '/restore', json={})
        self.assertEqual(self.client.get('/accounting/events').json['events'], [])
        self.assertEqual(len(self.client.get('/items').json['items']), 1)


if __name__ == '__main__':
    unittest.main()

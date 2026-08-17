"""
End-to-End Test Suite for Virtual Soundboard Numpad Pro
======================================================
Validates Flask endpoints, Audio Engine integrations,
Device settings, Hotkey rebinds, FX modifications, and Panic Stop.
"""

import os
import unittest
from app import app, config_manager, audio_engine, hotkey_manager


class TestSoundboardE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        cls.client = app.test_client()

    def test_01_index_page(self):
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Virtual Soundboard', res.data)
        self.assertIn(b'STOP ALL', res.data)
        self.assertIn(b'grid-ctrl', res.data)
        self.assertIn(b'grid-alt', res.data)

    def test_02_api_status(self):
        res = self.client.get('/api/status')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['status'], 'ok')
        self.assertIn('master_volume', data)
        self.assertIn('panic_key', data)
        self.assertGreater(data['sound_count'], 0)

    def test_03_api_devices(self):
        res = self.client.get('/api/devices')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('devices', data)
        self.assertIsInstance(data['devices'], list)

        post_res = self.client.post('/api/devices', json={
            'primary_device': None,
            'secondary_device': 'CABLE Input (VB-Audio Virtual Cable)',
            'secondary_enabled': True
        })
        self.assertEqual(post_res.status_code, 200)

        # Test routing toggle
        toggle_res = self.client.post('/api/routing_toggle', json={
            'headset_enabled': True,
            'cable_enabled': False
        })
        self.assertEqual(toggle_res.status_code, 200)
        self.assertEqual(toggle_res.get_json()['headset_enabled'], True)
        self.assertEqual(toggle_res.get_json()['cable_enabled'], False)

    def test_04_api_sounds(self):
        res = self.client.get('/api/sounds')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('sounds', data)
        self.assertGreater(len(data['sounds']), 0)

    def test_05_edit_sound_and_fx(self):
        sounds = config_manager.config.get('sounds', [])
        self.assertGreater(len(sounds), 0)
        first_id = sounds[0]['id']

        edit_res = self.client.post(f'/api/sounds/{first_id}/edit', json={
            'volume': 0.85,
            'speed': 1.15,
            'pitch': 3.0
        })
        self.assertEqual(edit_res.status_code, 200)
        updated = edit_res.get_json()['sound']
        self.assertEqual(updated['volume'], 0.85)
        self.assertEqual(updated['speed'], 1.15)
        self.assertEqual(updated['pitch'], 3.0)

    def test_06_hotkey_rebind(self):
        sounds = config_manager.config.get('sounds', [])
        first_id = sounds[0]['id']

        rebind_res = self.client.post(f'/api/sounds/{first_id}/rebind', json={
            'hotkey': 'ctrl+7'
        })
        self.assertEqual(rebind_res.status_code, 200)
        self.assertEqual(rebind_res.get_json()['status'], 'success')

    def test_07_play_and_panic_stop(self):
        sounds = config_manager.config.get('sounds', [])
        first_id = sounds[0]['id']

        play_res = self.client.post(f'/api/play/{first_id}', json={
            'volume': 0.1,
            'speed': 1.2,
            'pitch': 2.0
        })
        self.assertEqual(play_res.status_code, 200)

        stop_single = self.client.post(f'/api/sounds/{first_id}/stop')
        self.assertEqual(stop_single.status_code, 200)

        stop_all = self.client.post('/api/stop')
        self.assertEqual(stop_all.status_code, 200)

    def test_08_master_volume_and_panic_key(self):
        vol_res = self.client.post('/api/master_volume', json={'volume': 0.9})
        self.assertEqual(vol_res.status_code, 200)
        self.assertEqual(vol_res.get_json()['master_volume'], 0.9)

        panic_res = self.client.post('/api/panic_key', json={'panic_key': 'esc'})
        self.assertEqual(panic_res.status_code, 200)
        self.assertEqual(panic_res.get_json()['panic_key'], 'esc')

    def test_09_global_fx(self):
        fx_res = self.client.post('/api/global_fx', json={
            'pitch': 4.0,
            'speed': 1.25,
            'echo': 0.5,
            'reverb': 0.6
        })
        self.assertEqual(fx_res.status_code, 200)
        data = fx_res.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['pitch'], 4.0)
        self.assertEqual(data['speed'], 1.25)
        self.assertEqual(data['echo'], 0.5)
        self.assertEqual(data['reverb'], 0.6)

        status_res = self.client.get('/api/status')
        s_data = status_res.get_json()
        self.assertEqual(s_data['global_pitch'], 4.0)
        self.assertEqual(s_data['global_echo'], 0.5)

    def test_10_upload_and_replace_hotkey(self):
        import io
        fake_audio = io.BytesIO(b"fake audio data content")
        data = {
            'file': (fake_audio, 'test_replacement.mp3'),
            'name': 'Test Replacement Sound',
            'hotkey': 'ctrl+7'
        }
        res = self.client.post('/api/sounds/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 200)
        sound = res.get_json()['sound']
        self.assertEqual(sound['hotkey'], 'ctrl+7')
        self.assertEqual(sound['name'], 'Test Replacement Sound')

        # Clean up created file
        created_file = os.path.join(audio_engine.audio_dir, sound['filename'])
        if os.path.exists(created_file):
            os.remove(created_file)


if __name__ == '__main__':
    unittest.main()

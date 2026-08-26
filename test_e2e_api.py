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
        from auth_service import auth_service
        auth_service.disable_auth = True

    @classmethod
    def tearDownClass(cls):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        test_file = os.path.join(base_dir, 'static', 'audio', 'test_replacement.mp3')
        if os.path.exists(test_file):
            try:
                os.remove(test_file)
            except Exception:
                pass
        config_manager.sync_audio_files(config_manager.config)
        config_manager.config['master_volume'] = 0.9
        config_manager.config['global_pitch'] = 0.0
        config_manager.config['global_speed'] = 1.0
        config_manager.config['global_echo'] = 0.0
        config_manager.config['global_reverb'] = 0.0
        for s in config_manager.config.get('sounds', []):
            s['volume'] = 1.0
            s['pitch'] = 0.0
            s['speed'] = 1.0
        config_manager.save_config()

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

        # Restore default zero FX
        self.client.post('/api/global_fx', json={
            'pitch': 0.0,
            'speed': 1.0,
            'echo': 0.0,
            'reverb': 0.0
        })
        self.client.post('/api/master_volume', json={'volume': 0.9})

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

    def test_11_discord_api(self):
        # Status endpoint
        st_res = self.client.get('/api/discord/status')
        self.assertEqual(st_res.status_code, 200)
        st_data = st_res.get_json()
        self.assertIn('configured', st_data)
        self.assertIn('connected', st_data)
        self.assertIn('voice_connected', st_data)

        # Config endpoint
        cfg_res = self.client.post('/api/discord/config', json={
            'token': '',
            'guild_id': '1234567890',
            'channel_id': '9876543210'
        })
        self.assertEqual(cfg_res.status_code, 200)
        self.assertIn('discord', cfg_res.get_json())

    def test_12_auth_config_public_endpoint(self):
        res = self.client.get('/api/auth/config')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('apiKey', data)
        self.assertIn('projectId', data)
        self.assertIn('authEnabled', data)

    def test_13_auth_unauthorized_when_auth_enabled(self):
        from auth_service import auth_service
        orig_disable = auth_service.disable_auth
        try:
            auth_service.disable_auth = False
            # Request without Bearer token
            res = self.client.get('/api/sounds')
            self.assertEqual(res.status_code, 401)
            self.assertEqual(res.get_json()['error'], 'Unauthorized')
        finally:
            auth_service.disable_auth = orig_disable

    def test_14_auth_forbidden_when_not_in_allowed_users(self):
        from auth_service import auth_service
        from unittest.mock import patch

        orig_disable = auth_service.disable_auth
        orig_users = auth_service.allowed_users
        try:
            auth_service.disable_auth = False
            auth_service.allowed_users = {'authorized@example.com', 'admin@example.com'}

            with patch.object(auth_service, 'verify_token', return_value={'email': 'unauthorized@example.com', 'uid': '123'}):
                res = self.client.get('/api/sounds', headers={'Authorization': 'Bearer mock-token'})
                self.assertEqual(res.status_code, 403)
                self.assertIn('Access Denied', res.get_json()['error'])
        finally:
            auth_service.disable_auth = orig_disable
            auth_service.allowed_users = orig_users

    def test_15_auth_authorized_user_flow(self):
        from auth_service import auth_service
        from unittest.mock import patch

        orig_disable = auth_service.disable_auth
        orig_users = auth_service.allowed_users
        try:
            auth_service.disable_auth = False
            auth_service.allowed_users = {'authorized-user@example.com', 'admin@example.com'}

            mock_user = {
                'email': 'authorized-user@example.com',
                'name': 'Test Engineer',
                'uid': 'user-456'
            }

            with patch.object(auth_service, 'verify_token', return_value=mock_user):
                # Check me endpoint
                me_res = self.client.get('/api/auth/me', headers={'Authorization': 'Bearer valid-token'})
                self.assertEqual(me_res.status_code, 200)
                self.assertEqual(me_res.get_json()['user']['email'], 'authorized-user@example.com')

                # Check protected data access
                sounds_res = self.client.get('/api/sounds', headers={'Authorization': 'Bearer valid-token'})
                self.assertEqual(sounds_res.status_code, 200)
                self.assertIn('sounds', sounds_res.get_json())
        finally:
            auth_service.disable_auth = orig_disable
            auth_service.allowed_users = orig_users

    def test_16_companion_auth_and_events(self):
        from auth_service import auth_service
        orig_disable = auth_service.disable_auth
        try:
            auth_service.disable_auth = False
            # Test access via X-Companion-Key
            res = self.client.get('/api/sounds', headers={'X-Companion-Key': 'soundboard-companion-key-2026'})
            self.assertEqual(res.status_code, 200)
            self.assertIn('sounds', res.get_json())

            # Test panic with companion key
            panic_res = self.client.post('/api/panic', headers={'X-Companion-Key': 'soundboard-companion-key-2026'})
            self.assertEqual(panic_res.status_code, 200)
        finally:
            auth_service.disable_auth = orig_disable


if __name__ == '__main__':
    unittest.main()



#!/usr/bin/env python3
"""
Test script to verify the hotkey client works with the containerized soundboard
"""

import subprocess
import time
import requests
import sys
import json

def check_docker_running():
    """Check if Docker is running"""
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def check_container_running():
    """Check if the soundboard container is running"""
    try:
        result = subprocess.run(['docker-compose', 'ps'], capture_output=True, text=True)
        return 'Up' in result.stdout
    except:
        return False

def check_server_responding():
    """Check if the soundboard server is responding"""
    try:
        response = requests.get('http://localhost:5000/', timeout=3)
        return response.status_code == 200
    except:
        return False

def test_api_endpoint():
    """Test if the /api/sounds endpoint works"""
    try:
        response = requests.get('http://localhost:5000/api/sounds', timeout=3)
        if response.status_code == 200:
            sounds = response.json()
            print(f"✅ API endpoint working - found {len(sounds)} sounds")
            
            # Show first few sounds for verification
            if sounds:
                print("   Sample sounds:")
                for i, sound in enumerate(sounds[:3]):
                    print(f"     {sound['hotkey']} -> {sound['name']}")
                if len(sounds) > 3:
                    print(f"     ... and {len(sounds) - 3} more")
            return True
        else:
            print(f"❌ API endpoint returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API endpoint failed: {e}")
        return False

def test_play_endpoint():
    """Test if the /play endpoint works"""
    try:
        # Get a sound to test with
        response = requests.get('http://localhost:5000/api/sounds', timeout=3)
        if response.status_code == 200:
            sounds = response.json()
            if sounds:
                test_filename = sounds[0]['filename']
                play_response = requests.get(f'http://localhost:5000/play/{test_filename}', timeout=3)
                if play_response.status_code == 200:
                    print(f"✅ Play endpoint working - tested with {test_filename}")
                    return True
                else:
                    print(f"❌ Play endpoint returned status {play_response.status_code}")
                    return False
            else:
                print("❌ No sounds available to test")
                return False
        else:
            print("❌ Could not get sounds list for testing")
            return False
    except Exception as e:
        print(f"❌ Play endpoint test failed: {e}")
        return False

def check_keyboard_permissions():
    """Check if we can import keyboard library"""
    try:
        import keyboard
        print("✅ Keyboard library available")
        return True
    except ImportError:
        print("❌ Keyboard library not installed")
        print("💡 Run: pip install -r requirements_hotkey_client.txt")
        return False
    except Exception as e:
        print(f"❌ Keyboard library error: {e}")
        print("💡 Try running as administrator")
        return False

def main():
    print("🧪 Soundboard Hybrid Setup Diagnostics")
    print("=" * 50)
    
    # Test 0: Check if Docker is running
    print("0. Checking if Docker is running...")
    if check_docker_running():
        print("✅ Docker is available")
    else:
        print("❌ Docker is not running or not installed")
        print("💡 Start Docker Desktop")
        return False
    
    # Test 1: Check if container is running
    print("1. Checking if container is running...")
    if check_container_running():
        print("✅ Container is running")
    else:
        print("❌ Container is not running")
        print("💡 Run: docker-compose up -d")
        return False
    
    # Test 2: Check if server is responding
    print("2. Checking if server is responding...")
    if check_server_responding():
        print("✅ Server is responding")
    else:
        print("❌ Server is not responding")
        print("💡 Check container logs: docker-compose logs")
        return False
    
    # Test 3: Test API endpoint
    print("3. Testing API endpoint...")
    if not test_api_endpoint():
        return False
    
    # Test 4: Test play endpoint
    print("4. Testing play endpoint...")
    if not test_play_endpoint():
        return False
    
    # Test 5: Check keyboard permissions
    print("5. Checking keyboard library...")
    if not check_keyboard_permissions():
        return False
    
    print("\n🎉 All tests passed!")
    print("✅ Ready to start hotkey client")
    print("\n📝 Next steps:")
    print("   1. Run: python hotkey_client.py")
    print("   2. Test with F12 key (manual test)")
    print("   3. Test with Ctrl+7, Alt+7, etc.")
    print("   4. Check that sounds play in browser")
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n❌ Setup has issues - please fix the problems above")
        sys.exit(1)
    else:
        print("\n✅ Everything looks good!")
        sys.exit(0)

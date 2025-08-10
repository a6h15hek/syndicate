#!/usr/bin/env python3
"""System tests for Enhanced Speech Recognition System"""

import os
import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class SystemTest(unittest.TestCase):
    def test_imports(self):
        """Test that all required modules can be imported"""
        try:
            import vosk
            import sounddevice as sd
            import webrtcvad
            import numpy as np
            from dotenv import load_dotenv
        except ImportError as e:
            self.fail(f"Failed to import required module: {e}")
    
    def test_model_exists(self):
        """Test that the Vosk model exists and is valid"""
        from dotenv import load_dotenv
        load_dotenv()
        
        model_path = os.getenv("VOSK_MODEL_PATH")
        self.assertIsNotNone(model_path, "VOSK_MODEL_PATH not set")
        self.assertTrue(os.path.exists(model_path), f"Model path does not exist: {model_path}")
        
        # Check for essential model files
        essential_files = ["am/final.mdl", "graph/HCLG.fst", "../../words.txt"]
        for file in essential_files:
            file_path = os.path.join(model_path, file)
            self.assertTrue(os.path.exists(file_path), f"Missing model file: {file}")
    
    def test_audio_devices(self):
        """Test that audio input devices are available"""
        import sounddevice as sd
        
        devices = sd.query_devices()
        input_devices = [d for d in devices if d['max_input_channels'] > 0]
        self.assertTrue(len(input_devices) > 0, "No input audio devices found")
    
    def test_vad_initialization(self):
        """Test Voice Activity Detection initialization"""
        import webrtcvad
        
        vad = webrtcvad.Vad()
        for mode in range(4):
            vad.set_mode(mode)  # Should not raise exception

if __name__ == '__main__':
    unittest.main()

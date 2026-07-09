import sys
import os

print("=== AIRA Backend Verification Check ===")

# Test basic imports
try:
    import dotenv
    print("[PASS] python-dotenv imported successfully")
except ImportError:
    print("[FAIL] python-dotenv is missing")

try:
    import websockets
    print("[PASS] websockets imported successfully")
except ImportError:
    print("[FAIL] websockets is missing")

try:
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.runner import PipelineRunner
    from pipecat.pipeline.task import PipelineTask
    print("[PASS] Pipecat Core elements imported successfully")
except ImportError as e:
    print(f"[FAIL] Pipecat Core elements import failed: {e}")

try:
    from pipecat.services.google.llm import GoogleLLMService
    print("[PASS] GoogleLLMService imported successfully")
except ImportError as e:
    print(f"[FAIL] GoogleLLMService import failed: {e}")

# Check STT and TTS services

# Check context and aggregators
try:
    from pipecat.processors.aggregators.llm_context import LLMContext
    from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
    print("[PASS] Context and Context Pair imported successfully")
    
    # Dry run instantiation to check ONNX runtime DLL dependency
    try:
        context = LLMContext()
        context_pair = LLMContextAggregatorPair(context)
        print("[PASS] Context Pair instantiated successfully")
    except Exception as e:
        print(f"[FAIL] Context Pair instantiation failed: {e}")
        print("       (Note: This is usually due to onnxruntime failing to load its DLL on Windows with Python 3.14)")
except ImportError as e:
    print(f"[FAIL] Context and Context Pair import failed: {e}")

# Check local audio availability
try:
    from pipecat.transports.local.audio import LocalAudioTransport
    print("[PASS] LocalAudioTransport imported successfully (PyAudio present)")
except ImportError as e:
    print(f"[WARN] LocalAudioTransport import failed: {e}")
    print("       (Note: PyAudio is not installed, which is expected on Windows hosts without MSVC build tools)")

print("=======================================")

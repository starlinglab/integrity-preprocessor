import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../lib")))
import common

DEBUG = os.environ.get("HTTP_DEBUG") == "1"

def test_sha256sum():
    assert common.sha256sum("tests/assets/sha256_test.txt") == "936a185caaa266bb9cbe981e9e05cb78cd732b0b3280eb944412bb6f8f8f07af"

#def add_to_pipeline(source_file, content_meta, recorder_meta, stage_path, output_path):
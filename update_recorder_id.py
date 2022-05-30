import os
import sys

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/lib")

import integrity_recorder_id

integrity_recorder_id.build_recorder_id_json()

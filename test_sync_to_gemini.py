import os
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

from sync_to_gemini import read_local, replace_doc, sync

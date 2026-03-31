#!/usr/bin/env python3
"""Mountain DisplayPad macOS Controller - Main Entry Point"""

import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from displaypad.gui import DisplayPadApp


def main():
    app = DisplayPadApp()
    app.run()


if __name__ == "__main__":
    main()

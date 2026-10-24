"""Run cadgen; optionally use an installed Chrome for headless rendering.

CADGEN_CHROME_PATH selects a browser executable, with a fresh temporary profile.
This works around the macOS headless-shell ICU startup failure recorded in run/.
It does not modify cadgen, the browser installation, or any user profile.
"""
import os
from cadgen.cli import main


if os.environ.get('CADGEN_CHROME_PATH'):
    from playwright.async_api import BrowserType

    original_launch = BrowserType.launch

    async def launch(self, *args, **kwargs):
        if self.name == 'chromium':
            kwargs['executable_path'] = os.environ['CADGEN_CHROME_PATH']
        return await original_launch(self, *args, **kwargs)

    BrowserType.launch = launch


if __name__ == '__main__':
    raise SystemExit(main())

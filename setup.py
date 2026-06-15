"""
@author buchi
@since 2026-06-15
"""
from setuptools import setup, find_packages

setup(
    name="wechat-remote",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "httpx",
        "prompt_toolkit",
        "rich",
        "websockets",
    ],
    entry_points={
        "console_scripts": [
            "wchat=cli.app:main",
        ],
    },
    python_requires=">=3.10",
)

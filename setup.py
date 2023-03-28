from setuptools import setup
from async_termux import VERSION

with open("README.md", "rt", encoding="utf-8") as f:
    LONG_DESC = f.read()

setup(
    name='async_termux',
    version=VERSION,
    author="Dreagonmon",
    description="async termux wrapper",
    long_description=LONG_DESC,
    long_description_content_type="text/markdown",
    zip_safe=True,
    python_requires=">=3.9",
    install_requires=[],
)
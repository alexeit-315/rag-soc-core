from setuptools import setup, find_packages

setup(
    name="hdx-converter",
    version="1.4.0",
    author="HDX Converter Team",
    author_email="alexeit315@gmail.com",
    description="Tool for converting HDX documentation to multiple formats with metadata",
    long_description="""
# HDX Converter

A modular tool for converting HDX documentation to multiple formats (TXT, MD, JSON) with comprehensive metadata extraction.

## Features

- Extracts content from HDX (HTML) files
- Preserves internal links and navigation
- Generates structured metadata in JSON format (schema 1.2)
- Converts to multiple formats: TXT, Markdown, HTML backup
- Validates metadata completeness
- Handles images and tables
- Provides detailed statistics and reporting
- Modular architecture for easy extension
- Supports hierarchical navigation parsing
- Extracts section structure with proper formatting
- Includes progress bars for long conversions
- Validates required and strictly desirable fields
- REST API with FastAPI
- Async conversion with Kafka notifications
- Prometheus metrics for monitoring
    """,
    long_description_content_type="text/markdown",
    url="https://github.com/alexeit-315/rag-soc-core",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Documentation",
        "Topic :: Text Processing :: Markup :: HTML",
        "Topic :: Text Processing :: Markup :: Markdown",
        "Topic :: Utilities",
    ],
    python_requires=">=3.11",
    install_requires=[
        "beautifulsoup4>=4.12.0",
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
        "lxml>=4.9.0",
        "tqdm>=4.66.0",
        "markdown>=3.4.0",
        "html2text>=2020.1.16",
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "python-multipart>=0.0.6",
        "prometheus-client>=0.19.0",
        "kafka-python>=2.0.2",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "types-python-slugify>=8.0.0",
        ],
        "test": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
        "kafka": [
            "kafka-python>=2.0.2",
        ],
        "metrics": [
            "prometheus-client>=0.19.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "hdx-converter=hdx_converter.cli:main",
            "hdx-converter-api=hdx_converter.cli:run_api",
        ],
    },
    include_package_data=True,
    keywords="hdx documentation converter html markdown metadata api",
    project_urls={
        "Bug Reports": "https://github.com/alexeit-315/rag-soc-core/issues",
        "Source": "https://github.com/alexeit-315/rag-soc-core",
        "Documentation": "https://github.com/alexeit-315/rag-soc-core/wiki",
    },
)
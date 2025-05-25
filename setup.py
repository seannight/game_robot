from setuptools import setup, find_packages

setup(
    name="teddy-cup",
    version="5.0.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "langchain",
        "langchain-community",
        "jieba",
        "pymupdf",
        "python-multipart",
        "pydantic",
        "python-dotenv",
        "aiofiles"
    ],
    description="竞赛智能客服系统",
    author="Teddy-Cup Team",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
) 
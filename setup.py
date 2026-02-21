from setuptools import setup, find_packages

setup(
    name='pdb-trajectory-cli',
    version='1.0.0',
    description='PDB Trajectory Analysis CLI — local version of the web GUI pipeline',
    packages=find_packages(),
    python_requires='>=3.10',
    install_requires=[
        'MDAnalysis>=2.6',
        'rich>=13.0',
        'plotly>=5.0',
        'kaleido==0.2.1',
        'python-dotenv',
    ],
    entry_points={
        'console_scripts': [
            'pdb-cli=cli.main:main',
        ],
    },
)

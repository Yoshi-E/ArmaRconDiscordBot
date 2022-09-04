from setuptools import find_packages, setup

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name='ArmaRconDiscordBot',
    version='0.0.1',
    packages=find_packages(exclude=['tests']),  # Include all the python modules except `tests`.
    description='ArmaRconDiscordBot to manage Arma 3 servers with discord',
    long_description='An open source tool to manage servers with Rcon via Discord',
    install_requires=required,
    classifiers=[
        'Programming Language :: Python',
    ],
    entry_points={
        'pytest11': []
    },
)